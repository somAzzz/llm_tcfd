import re
from collections.abc import Callable
from pydantic import BaseModel


SENTENCE_TERMINATORS = '。！？；'


def sentence_extract_window(text: str, start_a: int, end_a: int) -> tuple[int, int]:
    """提取句子窗口边界（前一句号到后一句号）

    Args:
        text: 原文
        start_a: A词起始位置
        end_a: A词结束位置

    Returns:
        (window_start, window_end)

    Note:
        - 若文本无任何终止符，返回 (0, len(text))
        - 若前面无终止符，window_start=0
        - 若后面无终止符，window_end=len(text)
        - 边界包含性：B在 terminator 位置视为"在句子内"（使用 <= 比较）
    """
    if not (0 <= start_a <= end_a <= len(text)):
        raise ValueError(f"Invalid positions: start_a={start_a}, end_a={end_a}, text_len={len(text)}")

    # 前一个终止符
    prev_pos = -1
    for i in range(start_a - 1, -1, -1):
        if text[i] in SENTENCE_TERMINATORS:
            prev_pos = i
            break
    window_start = prev_pos + 1 if prev_pos != -1 else 0
    # 后一个终止符
    next_pos = -1
    for i in range(end_a, len(text)):
        if text[i] in SENTENCE_TERMINATORS:
            next_pos = i
            break
    window_end = next_pos if next_pos != -1 else len(text)
    return window_start, window_end


class MatchContext(BaseModel):
    """共现事件上下文"""
    math_label_a: str
    keyword_a: str
    keyword_b: str
    window_text: str
    position: int
    keyword_a_end: int
    window_start: int
    window_end: int
    text: str = ""
    sentence_window_start: int | None = None
    sentence_window_end: int | None = None
    keyword_b_position: int | None = None

    @property
    def text_after_a_in_window(self) -> str:
        """A词之后的原文文本（最多10字）,用于公司过滤"""
        return self.window_text[self.keyword_a_end - self.window_start:][:10]


def extract_window(text: str, start_a: int, end_a: int,
                   window: int, use_sentence: bool = False) -> tuple[int, int]:
    """提取窗口边界

    Args:
        text: 原文
        start_a: A词起始位置
        end_a: A词结束位置
        window: 固定窗口大小（仅在 use_sentence=False 时使用）
        use_sentence: 是否使用句子窗口

    Returns:
        (window_start, window_end)
    """
    if use_sentence:
        # 前一个终止符
        prev_pos = -1
        for i in range(start_a - 1, -1, -1):
            if text[i] in SENTENCE_TERMINATORS:
                prev_pos = i
                break
        window_start = prev_pos + 1 if prev_pos != -1 else 0
        # 后一个终止符
        next_pos = -1
        for i in range(end_a, len(text)):
            if text[i] in SENTENCE_TERMINATORS:
                next_pos = i
                break
        window_end = next_pos if next_pos != -1 else len(text)
    else:
        window_start = max(0, start_a - window)
        window_end = min(len(text), end_a + window)

    return window_start, window_end


def create_context(text: str, math_label: str, kw_a: str, start_a: int, end_a: int,
                   kw_b: str, window_start: int, window_end: int,
                   sentence_window_start: int | None = None,
                   sentence_window_end: int | None = None,
                   keyword_b_position: int | None = None) -> MatchContext:
    """创建 MatchContext 实例

    Args:
        text: 原文
        math_label: 数学标签
        kw_a: A类关键词
        start_a: A类关键词起始位置
        end_a: A类关键词结束位置
        kw_b: B类关键词
        window_start: 窗口起始位置
        window_end: 窗口结束位置
        sentence_window_start: 句子窗口起始位置（sentence_window启用时）
        sentence_window_end: 句子窗口结束位置（sentence_window启用时）
        keyword_b_position: B类关键词在原文中的绝对位置
    """
    return MatchContext(
        math_label_a=math_label,
        keyword_a=kw_a,
        keyword_b=kw_b,
        window_text=text[window_start:window_end],
        position=start_a,
        keyword_a_end=end_a,
        window_start=window_start,
        window_end=window_end,
        text=text,
        sentence_window_start=sentence_window_start,
        sentence_window_end=sentence_window_end,
        keyword_b_position=keyword_b_position
    )


def exclude_company_filter(ctx: MatchContext) -> bool:
    """A后面10字内出现'公司'则过滤"""
    return "公司" not in ctx.text_after_a_in_window


def sentence_window_filter(ctx: MatchContext) -> bool:
    """检查B是否在句子窗口边界内

    筛选逻辑：
    - 若 sentence_window_start 为 None（未启用 sentence_window），直接返回 True（跳过此筛选器）
    - 若 B 在句子窗口范围内，返回 True（保留）
    - 若 B 不在句子窗口范围内，返回 False（过滤）
    """
    if ctx.sentence_window_start is None:
        return True

    if ctx.keyword_b_position is None:
        return True

    return ctx.sentence_window_start <= ctx.keyword_b_position <= ctx.sentence_window_end


FilterFunc = Callable[[MatchContext], bool]


def get_filters(exclude_company: bool, sentence_window: bool) -> list[FilterFunc]:
    """根据配置返回筛选器列表"""
    filters: list[FilterFunc] = []
    if exclude_company:
        filters.append(exclude_company_filter)
    if sentence_window:
        filters.append(sentence_window_filter)
    return filters


def apply_filters(contexts: list[MatchContext], filters: list[FilterFunc]) -> list[MatchContext]:
    """应用筛选器链,返回保留下来的上下文"""
    for f in filters:
        contexts = [ctx for ctx in contexts if f(ctx)]
    return contexts


def count_cooccurrence(text: str, math_label_keywords: dict, keywords_b: list[str],
                       window: int = 30, normalize: bool = False,
                       exclude_company: bool = False, sentence_window: bool = False) -> dict:
    """统计A类词(多个math_label的keywords)和B类词的共现

    共现定义：A和B在window距离内同时出现（双向）

    Args:
        text: 待统计文本
        math_label_keywords: {math_label: [keywords]} A类词
        keywords_b: B类词列表
        window: 窗口大小,默认30字（前后各30字）
        normalize: 是否归一化
        exclude_company: 是否排除A后10字内出现"公司"的共现
        sentence_window: 是否使用句子窗口（按句号切分）

    Returns:
        {"sum_class_AB": 共现次数, "sum_class_AB_每万字": 归一化值, "contexts": [...]}
    """
    # 构建 keyword -> math_label 映射
    keyword_to_math_label = {}
    for math_label, keywords in math_label_keywords.items():
        for kw in keywords:
            keyword_to_math_label[kw] = math_label

    word_count = len(text)
    cooccurrence_count = 0
    contexts = []

    # 构建B类词正则
    pattern_b = '|'.join(re.escape(kw) for kw in keywords_b)

    # 如果没有B类词,则直接返回
    if not keywords_b:
        return {"sum_class_AB": 0, "contexts": []}

    # 遍历每个math_label和它的keywords
    for math_label, keywords in math_label_keywords.items():
        if not keywords:
            continue

        # 构建当前math_label的A类词正则
        pattern_a = '|'.join(re.escape(kw) for kw in keywords)

        # 收集所有A出现的位置
        matches_a = list(re.finditer(pattern_a, text))

        for match_a in matches_a:
            start_a = match_a.start()
            end_a = match_a.end()
            matched_kw_a = match_a.group()

            # 计算固定窗口边界
            fixed_start = max(0, start_a - window)
            fixed_end = min(len(text), end_a + window)

            # 计算句子窗口边界
            sent_start, sent_end = sentence_extract_window(text, start_a, end_a)

            # 计算交集
            if sentence_window:
                window_start = max(fixed_start, sent_start)
                window_end = min(fixed_end, sent_end)
                # 若交集为空（start > end），跳过此A词
                if window_start > window_end:
                    continue
            else:
                window_start, window_end = fixed_start, fixed_end

            # 在交集窗口内搜索B类词
            window_text = text[window_start:window_end]
            match_b = re.search(pattern_b, window_text)
            if match_b:
                cooccurrence_count += 1
                # B在原文中的绝对位置 = 窗口起点 + B在窗口中的相对位置
                b_position = window_start + match_b.start()
                ctx = create_context(
                    text=text,
                    math_label=math_label,
                    kw_a=matched_kw_a,
                    start_a=start_a,
                    end_a=end_a,
                    kw_b=match_b.group(),
                    window_start=window_start,
                    window_end=window_end,
                    sentence_window_start=sent_start if sentence_window else None,
                    sentence_window_end=sent_end if sentence_window else None,
                    keyword_b_position=b_position
                )
                contexts.append(ctx)

    # 应用筛选器
    filters = get_filters(exclude_company, sentence_window)
    contexts = apply_filters(contexts, filters)

    # 同步计数 - 过滤后的实际共现数
    cooccurrence_count = len(contexts)

    result = {
        "sum_class_AB": cooccurrence_count,
        "contexts": contexts
    }

    if normalize and word_count > 0:
        result["sum_class_AB_每万字"] = round(
            cooccurrence_count / (word_count / 10000), 4)

    return result
