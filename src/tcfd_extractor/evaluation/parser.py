"""共现上下文 MD 文件解析器

从 cooccurrence_evaluator.py 移出,纯解析逻辑,无 LLM 依赖。
"""
import re
from pathlib import Path

from .models import CooccurrenceContext, FileParseResult


# 预编译正则
_HEADER_PATTERN = re.compile(r"^# (.+) - (\d{4})年?度?报告")
_YEAR_DIR_PATTERN = re.compile(r"^(\d{4})$")
_PAIR_PATTERN = re.compile(r"\*\*(.+?)\*\* \+ \*\*(.+?)\*\* \((\d+)次共现\)")
_CONTEXT_PATTERN = re.compile(r'\d+\. "\.\.\.(.+?)\.\.\." \(位置: (\d+)\)')


def _extract_company_year(content: str, filepath: Path) -> tuple[str, int]:
    """从文件内容或路径提取 (company, year)。

    优先从文件头解析,失败时 fallback 到目录路径中的年份和文件名。

    Args:
        content: 文件完整内容
        filepath: 文件路径(用于 fallback)

    Returns:
        (company, year) 元组

    Raises:
        ValueError: 文件头无效且路径无法 fallback
    """
    header_match = _HEADER_PATTERN.match(content)
    if header_match:
        return header_match.group(1), int(header_match.group(2))

    # Fallback: 从路径的目录部分查找 4 位年份
    year = 0
    for part in filepath.parts:
        m = _YEAR_DIR_PATTERN.match(part)
        if m and 1900 <= int(m.group(1)) <= 2100:
            year = int(m.group(1))
            break

    company = filepath.stem or str(filepath)
    if not company:
        raise ValueError(f"无法解析文件头: {filepath}")
    return company, year


def parse_cooccurrence_md(filepath: Path) -> FileParseResult:
    """解析共现上下文 MD 文件

    Args:
        filepath: MD 文件路径

    Returns:
        FileParseResult: 解析后的文件结果,含 contexts 列表

    Raises:
        ValueError: 无法解析文件头
    """
    content = filepath.read_text(encoding="utf-8")
    company, year = _extract_company_year(content, filepath)

    contexts: list[CooccurrenceContext] = []
    pair_matches = list(_PAIR_PATTERN.finditer(content))

    for i, pair_match in enumerate(pair_matches):
        keyword_a = pair_match.group(1)
        keyword_b = pair_match.group(2)
        count = int(pair_match.group(3))

        # 找下一个 pair_match 之前的所有上下文
        start = pair_match.end()
        next_match = pair_matches[i + 1] if i + 1 < len(pair_matches) else None
        end = next_match.start() if next_match else len(content)

        pair_section = content[start:end]
        for ctx_match in _CONTEXT_PATTERN.finditer(pair_section):
            contexts.append(
                CooccurrenceContext(
                    keyword_a=keyword_a,
                    keyword_b=keyword_b,
                    context=ctx_match.group(1),
                    position=int(ctx_match.group(2)),
                    count=count,
                )
            )

    return FileParseResult(
        file=filepath.name, company=company, year=year, contexts=contexts
    )