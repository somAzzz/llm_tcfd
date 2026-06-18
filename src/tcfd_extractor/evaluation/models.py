"""评估模块 Pydantic 数据模型

从 cooccurrence_evaluator.py 移出,无业务逻辑。
"""
from pydantic import BaseModel, Field


class CooccurrenceContext(BaseModel):
    """共现上下文片段"""
    keyword_a: str
    keyword_b: str
    context: str
    position: int
    count: int = 1  # 共现次数


class TCFDValidationResult(BaseModel):
    """LLM 返回的 TCFD 验证结果"""
    is_tcfd_related: bool
    dimension: str = "无"  # 政策/市场/技术/无
    reason: str = Field(default="", max_length=100)


class EvaluationResult(BaseModel):
    """评估结果"""
    keyword_a: str
    keyword_b: str
    context: str
    position: int
    is_tcfd_related: bool
    dimension: str = "无"  # 政策/市场/技术/无
    reason: str = Field(max_length=50)


class FileParseResult(BaseModel):
    """解析后的文件结果"""
    file: str
    company: str
    year: int
    contexts: list[CooccurrenceContext]