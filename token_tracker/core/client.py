import anthropic

from token_tracker.core.models import Session
from token_tracker.core.tracker import log_usage
from token_tracker.storage.db import init_db, insert_session


def _extract_prompt_text(messages: list) -> str:
    parts = []
    for m in messages:
        content = m.get("content", "") if isinstance(m, dict) else ""
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
    return " ".join(parts)


def _replace_last_user_message(messages: list, new_text: str) -> list:
    new_messages = list(messages)
    for i in range(len(new_messages) - 1, -1, -1):
        m = new_messages[i]
        if isinstance(m, dict) and m.get("role") == "user":
            replacement = dict(m)
            replacement["content"] = new_text
            new_messages[i] = replacement
            break
    return new_messages


def _ask_action(has_rewrite: bool) -> str:
    options = "[s]end / [o]ptimize+send / [c]ancel" if has_rewrite else "[s]end / [c]ancel"
    valid_send   = {"s", "send", ""}        # default = send
    valid_opt    = {"o", "optimize"}
    valid_cancel = {"c", "cancel"}

    while True:
        answer = input(f"Action? {options} (default: send) ").strip().lower()
        if answer in valid_send:
            return "send"
        if answer in valid_opt and has_rewrite:
            return "optimize"
        if answer in valid_cancel:
            return "cancel"
        print("Invalid choice — type s, o, or c.")


class _TrackedMessages:
    def __init__(self, owner: "TrackedClient"):
        self._owner = owner
        self._inner = owner._anthropic.messages

    def create(self, **kwargs):
        # Streaming responses don't expose a usage block — pass through untracked
        if kwargs.get("stream"):
            return self._inner.create(**kwargs)

        model = kwargs.get("model", "unknown")
        prompt = _extract_prompt_text(kwargs.get("messages", []))
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
