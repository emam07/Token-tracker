"""Transparent instrumentation — patches anthropic.Anthropic without touching user code."""
import anthropic as _mod

_patched = False


def patch(
    session_name: str = "auto",
    analyze: bool = True,
    interactive: bool = False,
    warn_threshold: int = 60,
    verbose: bool = False,
) -> None:
    """Replace anthropic.Anthropic with a tracked version. Safe to call multiple times."""
    global _patched
    if _patched:
        return

    _orig = _mod.Anthropic
    from token_tracker.core.client import TrackedClient

    _s, _a, _i, _w, _v = session_name, analyze, interactive, warn_threshold, verbose

    def _auto(api_key=None, **kwargs):
        inner = _orig(api_key=api_key, **kwargs) if api_key else _orig(**kwargs)
        return TrackedClient(_client=inner, session_name=_s, analyze=_a, interactive=_i, warn_threshold=_w, verbose=_v)

    _auto.__wrapped__ = _orig
    _mod.Anthropic = _auto
    _patched = True


def unpatch() -> None:
    """Restore the original anthropic.Anthropic. Useful in tests."""
    global _patched
    if not _patched:
        return
    wrapped = getattr(_mod.Anthropic, "__wrapped__", None)
    if wrapped is not None:
        _mod.Anthropic = wrapped
    _patched = False
