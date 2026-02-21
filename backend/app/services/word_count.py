"""Word count budget checking for scene generation."""

from typing import Literal


def check_word_budget(
    text: str,
    target_chars: int,
    tolerance: float = 0.15,
) -> dict:
    """Check if text length is within the target budget.

    Returns dict with:
        status: 'within' | 'over' | 'under'
        actual_chars: int
        target_chars: int
        delta: int (actual - target)
        deviation: float (abs ratio)
        suggestion: 'compress' | 'expand' | None
    """
    actual = len(text)
    delta = actual - target_chars
    if target_chars <= 0:
        deviation = float(actual) if actual > 0 else 0.0
    else:
        deviation = abs(delta) / target_chars

    if deviation <= tolerance:
        status: Literal["within", "over", "under"] = "within"
        suggestion = None
    elif delta > 0:
        status = "over"
        suggestion = "compress"
    else:
        status = "under"
        suggestion = "expand"

    return {
        "status": status,
        "actual_chars": actual,
        "target_chars": target_chars,
        "delta": delta,
        "deviation": round(deviation, 3),
        "suggestion": suggestion,
    }


def build_rewrite_prompt(
    text: str,
    target_chars: int,
    mode: str,
) -> str:
    """Build a prompt for expanding or compressing scene text."""
    actual = len(text)
    if mode == "expand":
        return (
            f"你是一位专业的中文小说作家。以下场景正文目前有 {actual} 字，"
            f"目标是约 {target_chars} 字。"
            "请在保持原有情节和人物不变的前提下，扩写以下内容，"
            "增加细节描写、对话或环境描写。\n\n"
            f"{text}\n\n"
            "请直接输出扩写后的完整场景正文，不要输出任何标记或说明。"
        )
    else:
        return (
            f"你是一位专业的中文小说编辑。以下场景正文目前有 {actual} 字，"
            f"目标是约 {target_chars} 字。"
            "请在保持核心情节和关键对话不变的前提下，精简以下内容，"
            "删除冗余描写和不必要的细节。\n\n"
            f"{text}\n\n"
            "请直接输出精简后的完整场景正文，不要输出任何标记或说明。"
        )
