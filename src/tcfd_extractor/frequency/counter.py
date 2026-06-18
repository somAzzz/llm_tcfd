import re
from typing import List, Dict


def count_keywords(text: str, keywords: List[str], normalize: bool = False) -> Dict:
    """统计关键词出现次数

    Args:
        text: 待统计文本
        keywords: 关键词列表
        normalize: 是否归一化（每万字）

    Returns:
        {"关键词": 次数, "关键词_每万字": 归一化值, ...}
    """
    word_count = len(text)
    result = {}

    for kw in keywords:
        # 精确匹配
        count = len(re.findall(re.escape(kw), text))
        result[kw] = count

        if normalize and word_count > 0:
            result[f"{kw}_每万字"] = round(count / (word_count / 10000), 4)

    return result


def get_word_count(text: str) -> int:
    """获取文本字数"""
    return len(text)
