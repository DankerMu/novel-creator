"""Shared text utilities."""


def truncate_to_sentence(text: str, budget: int) -> str:
    """Truncate text to budget chars, trimming at sentence boundary."""
    if len(text) <= budget:
        return text

    truncated = text[:budget]
    for sep in ["\n", "。", ".", "！", "!", "？", "?", "；", ";"]:
        idx = truncated.rfind(sep)
        if idx > budget // 2:
            return truncated[: idx + 1]
    return truncated
