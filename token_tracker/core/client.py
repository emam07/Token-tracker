import warnings as _warnings

import anthropic

from token_tracker.core.models import Session
from token_tracker.core.tracker import log_usage
from token_tracker.storage.db import init_db, insert_session


def _extract_prompt_text(messages: list) -> str:
    """Extract text from user messages only (skips system messages and handles non-text blocks)."""
    parts = []
    for m in messages:
        if not isinstance(m, dict):
            continue
        if m.get("role") == "system":
            continue
        content = m.get("content", "")
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for block in content:
                if not isinstance(block, dict):
                    continue
                btype = block.get("type")
                if btype == "text":
                    parts.append(block.get("text", ""))
                elif btype == "image":
                    parts.append("[image]")
                elif btype == "tool_use":
                    parts.append(f"[tool_use:{block.get('name', '')}]")
                elif btype == "tool_result":
                    tc = block.get("content", "")
                    if isinstance(tc, str):
                        parts.append(tc)
                    elif isinstance(tc, list):
                        for tb in tc:
                            if isinstance(tb, dict) and tb.get("type") == "text":
                                parts.append(tb.get("text", ""))
    return " ".join(parts)


def _replace_last_user_message(messages: list, new_text: str) -> list:
    new_messages = list(messages)
    for i in range(len(new_messages) - 1, -1, -1):
        m = new_messages[i]
        if isinstance(m, dict) and m.get("role") == "user":
            replacement = dict(m)
            replacement["content"] = new_text
            new_messages[i] = replacement
            return new_messages
    _warnings.warn(
        "Token Tracker: no user message found to replace with optimized prompt — "
        "sending original messages unchanged.",
        stacklevel=3,
    )
    return new_messages


def _ask_action(has_rewrite: bool) -> str:
    options = "[s]end / [o]ptimize+send / [c]ancel" if has_rewrite else "[s]end / [c]ancel"
    valid_send   = {"s", "send", ""}
    valid_opt    = {"o", "optimize"}
    valid_cancel = {"c", "cancel"}

    while True:
        try:
            answer = input(f"Action? {options} (default: send) ").strip().lower()
        except EOFError:
            return "send"   # non-interactive environment (CI, pipe) — default to send
        if answer in valid_send:
            return "send"
        if answer in valid_opt and has_rewrite:
            return "optimize"
        if answer in valid_cancel:
            return "cancel"
        print("Invalid choice — type s, o, or c.")


class _TrackedStream:
    """Wraps an Anthropic stream to capture token usage once iteration completes."""

    def __init__(self, raw_stream, on_done):
        self._raw = raw_stream
        self._on_done = on_done
        self._input_tokens = 0
        self._output_tokens = 0
        self._cache_read = 0
        self._cache_write = 0

    def _capture(self, event):
        t = getattr(event, "type", None)
        if t == "message_start":
            u = getattr(getattr(event, "message", None), "usage", None)
            if u:
                self._input_tokens = getattr(u, "input_tokens",               0) or 0
                self._cache_read   = getattr(u, "cache_read_input_tokens",     0) or 0
                self._cache_write  = getattr(u, "cache_creation_input_tokens", 0) or 0
        elif t == "message_delta":
            u = getattr(event, "usage", None)
            if u:
                self._output_tokens = getattr(u, "output_tokens", 0) or 0

    def __iter__(self):
        try:
            for event in self._raw:
                self._capture(event)
                yield event
        finally:
            self._on_done(
                self._input_tokens,
                self._output_tokens,
                self._cache_read,
                self._cache_write,
            )

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def __getattr__(self, name):
        return getattr(self._raw, name)


class _TrackedMessages:
    def __init__(self, owner: "TrackedClient"):
        self._owner = owner
        self._inner = owner._anthropic.messages

    def create(self, **kwargs):
        model = kwargs.get("model", "unknown")
        if model == "unknown":
            _warnings.warn(
                "Token Tracker: no model specified in messages.create() — "
                "cost will be estimated using Sonnet pricing.",
                stacklevel=2,
            )

        prompt = _extract_prompt_text(kwargs.get("messages", []))

        # Streaming: wrap stream to capture usage at end, skip interactive analysis
        if kwargs.get("stream"):
            owner = self._owner

            def _on_stream_done(in_tok, out_tok, cache_r, cache_w):
                class _U:
                    input_tokens               = in_tok
                    output_tokens              = out_tok
                    cache_read_input_tokens    = cache_r
                    cache_creation_input_tokens = cache_w

                log_usage(
                    session_id=owner.session.id,
                    model=model,
                    prompt=prompt,
                    usage=_U(),
                    efficiency_score=None,
                    flagged=False,
                )

            return _TrackedStream(self._inner.create(**kwargs), _on_stream_done)

        final_prompt = prompt
        analysis = None

        if self._owner.analyze:
            from token_tracker.analyzer.preflight import analyze
            from token_tracker.dashboard.report import show_analysis

            analysis = analyze(prompt, model)
            should_show = analysis.efficiency_score < self._owner.warn_threshold

            if should_show:
                show_analysis(analysis, original_prompt=prompt)

                if self._owner.interactive and analysis.warnings:
                    has_rewrite = bool(analysis.suggested_rewrite)
                    action = _ask_action(has_rewrite)

                    if action == "cancel":
                        raise RuntimeError("Prompt cancelled by user.")
                    if action == "optimize":
                        final_prompt = analysis.suggested_rewrite
                        kwargs["messages"] = _replace_last_user_message(
                            kwargs.get("messages", []), final_prompt
                        )

        response = self._inner.create(**kwargs)

        log_usage(
            session_id=self._owner.session.id,
            model=model,
            prompt=final_prompt,
            usage=response.usage,
            efficiency_score=analysis.efficiency_score if analysis else None,
            flagged=bool(analysis and analysis.warnings),
        )
        return response

    def stream(self, **kwargs):
        return self._inner.stream(**kwargs)


class TrackedClient:
    """Drop-in replacement for anthropic.Anthropic that logs token usage to SQLite."""

    def __init__(
        self,
        api_key: str = None,
        session_name: str = "default",
        analyze: bool = True,
        interactive: bool = True,
        warn_threshold: int = 60,
        _client=None,
        **kwargs,
    ):
        init_db()
        if _client is not None:
            self._anthropic = _client
        elif api_key:
            self._anthropic = anthropic.Anthropic(api_key=api_key, **kwargs)
        else:
            self._anthropic = anthropic.Anthropic(**kwargs)
        self.analyze = analyze
        self.interactive = interactive
        self.warn_threshold = warn_threshold
        self.session = Session(name=session_name)
        insert_session(self.session)
        self.messages = _TrackedMessages(self)
