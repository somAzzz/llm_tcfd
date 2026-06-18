import pytest
from tcfd_extractor.frequency.cooccurrence import (
    MatchContext,
    count_cooccurrence,
    extract_window,
    sentence_extract_window,  # NEW
    exclude_company_filter,
    sentence_window_filter,  # NEW
    get_filters,
)


def test_cooccurrence_basic():
    """测试基本共现"""
    text = "碳达峰风险不确定，碳中和风险波动"  # "碳达峰"后50字内有"风险"
    # 新接口: math_label_keywords 是 dict {math_label: [keywords]}
    math_label_keywords = {
        "气候": ["碳达峰", "碳中和"],
        "排放": []
    }
    keywords_b = ["风险", "不确定", "波动"]
    result = count_cooccurrence(text, math_label_keywords, keywords_b, window=50)
    assert result["sum_class_AB"] >= 1


def test_match_context_text_after_a():
    """测试 text_after_a_in_window 属性"""
    # 场景："某碳排放公司风险" - "公司"在"碳排放"后4字处
    # "碳排放" 位置=2, end=5 (2-5表示start=2, end=5在0-indexed)
    # window_start=0, window_end=9
    # text_after_a = window_text[5-0:][:10] = window_text[5:] = "司风险"
    # 但如果我们用 keyword_a_end=4，则 window_text[4:] = "公司风险"
    ctx = MatchContext(
        math_label_a="气候",
        keyword_a="碳排放",
        keyword_b="风险",
        window_text="某碳排放公司风险",
        position=2,
        keyword_a_end=4,  # 修正：碳排放结束位置是4 (0-indexed: 碳=1,排=2,放=3,end=4)
        window_start=0,
        window_end=9
    )
    assert ctx.text_after_a_in_window == "公司风险"


def test_match_context_text_after_a_short_window():
    """测试当A在窗口末尾时"""
    ctx = MatchContext(
        math_label_a="气候",
        keyword_a="碳",
        keyword_b="风险",
        window_text="碳",
        position=0,
        keyword_a_end=1,
        window_start=0,
        window_end=1
    )
    assert ctx.text_after_a_in_window == ""


def test_match_context_text_after_a_exceeds_10():
    """测试 A后超过10字"""
    ctx = MatchContext(
        math_label_a="气候",
        keyword_a="碳",
        keyword_b="风险",
        window_text="碳排放风险很大",
        position=0,
        keyword_a_end=1,
        window_start=0,
        window_end=8
    )
    # window_text[1:][:10] = "排放风险很大"
    assert ctx.text_after_a_in_window == "排放风险很大"
    assert len(ctx.text_after_a_in_window) <= 10


def test_extract_window_sentence():
    """测试句子窗口提取"""
    text = "这是第一句话！这是第二句话？碳排放风险很大。这是第三句话。"
    start = text.find("碳排放")
    end = start + len("碳排放")

    window_start, window_end = extract_window(text, start, end, 30, use_sentence=True)

    # 前一个终止符是"？"(在"第二句话"后)，后一个终止符是"。"(在"第三句话"后)
    # 正确窗口: "碳排放风险很大" (implementation excludes terminator)
    assert text[window_start:window_end] == "碳排放风险很大"


def test_extract_window_sentence_no_terminator():
    """测试句子窗口：文本无终止符时"""
    text = "碳排放风险很大没有句号"
    start = 0
    end = len("碳排放")

    window_start, window_end = extract_window(text, start, end, 30, use_sentence=True)
    assert window_start == 0
    assert window_end == len(text)


def test_extract_window_sentence_no_next_terminator():
    """测试句子窗口：后面没有终止符"""
    text = "前面有句号。碳排放风险很大"
    start = text.find("碳排放")
    end = start + len("碳排放")

    window_start, window_end = extract_window(text, start, end, 30, use_sentence=True)
    assert window_end == len(text)


def test_extract_window_fixed():
    """测试固定窗口提取"""
    text = "ABC" + "碳排放风险" + "DEF"
    window_start, window_end = extract_window(text, 3, 6, 2, use_sentence=False)
    assert window_start == 1  # 3-2=1
    assert window_end == 8    # 6+2=8


def test_exclude_company_filter_should_exclude():
    """A后10字内有'公司'应被过滤"""
    ctx = MatchContext(
        math_label_a="气候",
        keyword_a="碳排放",
        keyword_b="风险",
        window_text="某碳排放公司风险",
        position=2,
        keyword_a_end=4,  # 修正：碳排放结束位置是4
        window_start=0,
        window_end=9
    )
    assert exclude_company_filter(ctx) == False


def test_exclude_company_filter_should_keep():
    """A后10字内无'公司'应保留"""
    ctx = MatchContext(
        math_label_a="气候",
        keyword_a="碳排放",
        keyword_b="风险",
        window_text="碳排放风险很大",
        position=0,
        keyword_a_end=3,
        window_start=0,
        window_end=8
    )
    assert exclude_company_filter(ctx) == True


def test_get_filters_combinations():
    """测试 get_filters 组合"""
    # 无筛选器
    filters = get_filters(exclude_company=False, sentence_window=False)
    assert len(filters) == 0

    # 仅 exclude_company
    filters = get_filters(exclude_company=True, sentence_window=False)
    assert len(filters) == 1
    assert filters[0] == exclude_company_filter

    # 两者都启用
    filters = get_filters(exclude_company=True, sentence_window=True)
    assert len(filters) == 2


def test_apply_filters_combined():
    """组合筛选器"""
    filters = get_filters(exclude_company=True, sentence_window=True)
    ctx = MatchContext(
        math_label_a="气候", keyword_a="碳排放", keyword_b="风险",
        window_text="某碳排放公司风险",
        position=2, keyword_a_end=4, window_start=0, window_end=9
    )
    assert all(f(ctx) for f in filters) == False


def test_count_cooccurrence_empty_keywords_b():
    """keywords_b 为空时，不应产生任何共现"""
    text = "碳排放风险很大"
    result = count_cooccurrence(text, {"气候": ["碳排放"]}, [], window=10)
    assert result["sum_class_AB"] == 0
    assert result["contexts"] == []


def test_match_context_new_fields():
    """Test MatchContext with new fields for sentence window filter"""
    ctx = MatchContext(
        math_label_a="气候",
        keyword_a="碳排放",
        keyword_b="风险",
        window_text="碳排放风险很大",
        position=0,
        keyword_a_end=3,
        window_start=0,
        window_end=8,
        text="碳排放风险很大这是另一句。",
        sentence_window_start=0,
        sentence_window_end=8,
        keyword_b_position=3
    )
    assert ctx.text == "碳排放风险很大这是另一句。"
    assert ctx.sentence_window_start == 0
    assert ctx.sentence_window_end == 8
    assert ctx.keyword_b_position == 3


def test_sentence_extract_window_basic():
    """测试句子窗口提取 - 基本场景"""
    text = "这是第一句话！这是第二句话？碳排放风险很大。这是第三句话。"
    start_a = text.find("碳排放")
    end_a = start_a + len("碳排放")

    window_start, window_end = sentence_extract_window(text, start_a, end_a)

    assert text[window_start:window_end] == "碳排放风险很大"


def test_sentence_extract_window_no_terminator():
    """句子窗口：文本无终止符时"""
    text = "碳排放风险很大没有句号"
    start_a = 0
    end_a = len("碳排放")

    window_start, window_end = sentence_extract_window(text, start_a, end_a)
    assert window_start == 0
    assert window_end == len(text)


def test_sentence_extract_window_invalid_positions():
    """句子窗口：无效位置应抛出 ValueError"""
    text = "碳排放风险"
    with pytest.raises(ValueError):
        sentence_extract_window(text, 5, 3)  # start > end
    with pytest.raises(ValueError):
        sentence_extract_window(text, -1, 3)  # start < 0


def test_sentence_window_filter_b_inside():
    """B在句子窗口内应保留"""
    text = "这是第一句话！碳排放风险很大。这是第三句话。"
    ctx = MatchContext(
        math_label_a="气候",
        keyword_a="碳排放",
        keyword_b="风险",
        window_text="碳排放风险很大",
        position=9,
        keyword_a_end=12,
        window_start=9,
        window_end=16,
        text=text,
        sentence_window_start=9,
        sentence_window_end=16,
        keyword_b_position=12
    )
    assert sentence_window_filter(ctx) == True


def test_sentence_window_filter_b_outside():
    """B在句子窗口外应被过滤"""
    text = "第一句话。第二句话。碳排放很大。第三句话。风险"
    ctx = MatchContext(
        math_label_a="气候",
        keyword_a="碳排放",
        keyword_b="风险",
        window_text="碳排放很大。第三句话。风险",
        position=12,
        keyword_a_end=15,
        window_start=10,
        window_end=30,
        text=text,
        sentence_window_start=6,
        sentence_window_end=16,
        keyword_b_position=23
    )
    assert sentence_window_filter(ctx) == False


def test_sentence_window_filter_no_sentence_window():
    """sentence_window未启用时应返回True（跳过筛选）"""
    ctx = MatchContext(
        math_label_a="气候",
        keyword_a="碳排放",
        keyword_b="风险",
        window_text="碳排放风险",
        position=0,
        keyword_a_end=3,
        window_start=0,
        window_end=6,
        text="碳排放风险",
        sentence_window_start=None,  # 未启用
        sentence_window_end=None,
        keyword_b_position=None
    )
    assert sentence_window_filter(ctx) == True


def test_count_cooccurrence_window_intersection():
    """固定窗口和句子窗口交集 - 集成测试"""
    text = "这是第一句话！这是第二句话？碳排放风险很大。这是第三句话。"
    math_label_keywords = {"气候": ["碳排放"]}
    keywords_b = ["风险"]

    # 只启用sentence_window时，应只匹配同句子内的B
    result = count_cooccurrence(text, math_label_keywords, keywords_b, window=30, sentence_window=True)
    # "碳排放"和"风险"都在同一句子窗口[9,16]内，应有1个共现
    assert result["sum_class_AB"] == 1


def test_count_cooccurrence_window_intersection_empty():
    """当固定窗口和句子窗口无交集时，应跳过该A词"""
    text = "第一句话。碳排放。第二句话。风险很大。"
    math_label_keywords = {"气候": ["碳排放"]}
    keywords_b = ["风险"]

    # A在第一句的"碳排放"，B在第二句的"风险"
    # 固定窗口[1,11]包含第二句的"风险"
    # 但句子窗口是第一句[0,5]
    # 交集为空，应跳过，无共现
    result = count_cooccurrence(text, math_label_keywords, keywords_b, window=30, sentence_window=True)
    assert result["sum_class_AB"] == 0
