"""评估模块自定义异常层次

异常层次:
    EvaluationError (基础)
    ├── LLMEvaluationError (LLM 调用基类)
    │   ├── LLMUnavailableError (API 不可达,超过重试)
    │   ├── LLMResponseParseError (响应无法解析)
    │   └── LLMTimeoutError (调用超时)
"""


class EvaluationError(Exception):
    """评估模块的基础异常"""


class LLMEvaluationError(EvaluationError):
    """LLM 调用相关错误基类"""


class LLMUnavailableError(LLMEvaluationError):
    """LLM API 不可达,超过重试次数后抛出"""


class LLMResponseParseError(LLMEvaluationError):
    """LLM 响应无法解析为 TCFDValidationResult"""


class LLMTimeoutError(LLMEvaluationError):
    """LLM 调用超时"""
