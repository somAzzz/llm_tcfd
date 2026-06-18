"""提示词常量测试

验证:
- 4 个常量都能导入
- EVAL_USER_PROMPT 包含格式化占位符 {keyword_a} {keyword_b} {context}
- SUMMARY_USER_PROMPT 包含 {total} {tcfd_count} 等占位符
- 关键中文关键词存在(EVAL_SYSTEM_PROMPT 含"政策"/"市场"/"技术")
"""
from tcfd_extractor.evaluation.prompts import (
    EVAL_SYSTEM_PROMPT,
    EVAL_USER_PROMPT,
    SUMMARY_SYSTEM_PROMPT,
    SUMMARY_USER_PROMPT,
)


class TestPromptImports:
    def test_eval_system_prompt_is_string(self):
        assert isinstance(EVAL_SYSTEM_PROMPT, str)
        assert len(EVAL_SYSTEM_PROMPT) > 100

    def test_eval_user_prompt_is_string(self):
        assert isinstance(EVAL_USER_PROMPT, str)

    def test_summary_system_prompt_is_string(self):
        assert isinstance(SUMMARY_SYSTEM_PROMPT, str)

    def test_summary_user_prompt_is_string(self):
        assert isinstance(SUMMARY_USER_PROMPT, str)


class TestEvalPromptContent:
    def test_eval_system_contains_three_dimensions(self):
        assert "政策" in EVAL_SYSTEM_PROMPT
        assert "市场" in EVAL_SYSTEM_PROMPT
        assert "技术" in EVAL_SYSTEM_PROMPT

    def test_eval_user_has_placeholders(self):
        assert "{keyword_a}" in EVAL_USER_PROMPT
        assert "{keyword_b}" in EVAL_USER_PROMPT
        assert "{context}" in EVAL_USER_PROMPT

    def test_eval_user_formattable(self):
        formatted = EVAL_USER_PROMPT.format(
            keyword_a="碳交易", keyword_b="低碳", context="公司参与碳交易"
        )
        assert "碳交易" in formatted
        assert "低碳" in formatted
        assert "公司参与碳交易" in formatted
        assert "{keyword_a}" not in formatted


class TestSummaryPromptContent:
    def test_summary_user_has_placeholders(self):
        assert "{total}" in SUMMARY_USER_PROMPT
        assert "{tcfd_count}" in SUMMARY_USER_PROMPT
        assert "{non_tcfd_count}" in SUMMARY_USER_PROMPT
        assert "{accuracy}" in SUMMARY_USER_PROMPT

    def test_summary_user_formattable(self):
        formatted = SUMMARY_USER_PROMPT.format(
            total=100, tcfd_count=80, non_tcfd_count=20, accuracy=80.0,
            policy_count=30, market_count=25, tech_count=25
        )
        assert "100" in formatted
        assert "80" in formatted
        assert "{total}" not in formatted
