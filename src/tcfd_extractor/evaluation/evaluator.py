"""单条 LLM 评估器

从 cooccurrence_evaluator.py 移出,只负责单条 CooccurrenceContext 的 LLM 评估。
删除了脆弱的 _parse_json_response 正则,改为最小化异常捕获路径,
在抛出 LLMResponseParseError 之前用 logger.error() 记录原始响应。
"""
import logging
import json

from openai import BadRequestError, OpenAI
from pydantic import ValidationError

from ..config import LLMSettings, llm_settings
from .exceptions import LLMResponseParseError
from .models import (
    CooccurrenceContext,
    EvaluationResult,
    TCFDValidationResult,
)
from .prompts import EVAL_SYSTEM_PROMPT, EVAL_USER_PROMPT


logger = logging.getLogger(__name__)


class CooccurrenceEvaluator:
    """共现上下文单条 LLM 评估器"""

    def __init__(self, settings: LLMSettings | None = None) -> None:
        self.settings = settings if settings is not None else llm_settings
        self.client = OpenAI(
            base_url=self.settings.base_url,
            api_key=self.settings.api_key,
        )

    def evaluate(self, context: CooccurrenceContext) -> EvaluationResult:
        """评估单个上下文片段

        Args:
            context: 共现上下文片段

        Returns:
            EvaluationResult: 评估结果

        Raises:
            LLMResponseParseError: LLM 响应无法解析
        """
        try:
            response = self.client.beta.chat.completions.parse(
                model=self.settings.model_name,
                messages=[
                    {"role": "system", "content": EVAL_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": EVAL_USER_PROMPT.format(
                            keyword_a=context.keyword_a,
                            keyword_b=context.keyword_b,
                            context=context.context,
                        ),
                    },
                ],
                response_format=TCFDValidationResult,
                temperature=self.settings.temperature,
                timeout=self.settings.timeout,
            )
            parsed = response.choices[0].message.parsed
            # 在 try 块内提取 raw_content,供后续 parsed=None 分支使用
            raw_content = response.choices[0].message.content or ""
        except (BadRequestError, ValidationError, json.JSONDecodeError) as e:
            # 记录原始响应以便调试
            try:
                raw_content = response.choices[0].message.content or ""
            except (NameError, AttributeError, IndexError):
                raw_content = ""
            logger.error(
                "LLM 响应解析失败: type=%s error=%s raw_response=%r",
                type(e).__name__, e, raw_content
            )
            raise LLMResponseParseError(f"LLM 响应无法解析: {e}") from e

        if parsed is None:
            logger.error("LLM 返回 parsed=None, content=%r", raw_content)
            raise LLMResponseParseError("LLM 返回的 parsed 为 None")

        return EvaluationResult(
            keyword_a=context.keyword_a,
            keyword_b=context.keyword_b,
            context=context.context,
            position=context.position,
            is_tcfd_related=parsed.is_tcfd_related,
            dimension=parsed.dimension,
            reason=parsed.reason[:50] if parsed.reason else "",
        )