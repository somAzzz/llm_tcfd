"""全局配置 - 集中管理 LLM / 路径 / 批处理参数

使用 pydantic-settings (v2 API) 支持环境变量覆盖:
  - TCFD_LLM_BASE_URL / TCFD_LLM_API_KEY / TCFD_LLM_MODEL_NAME / TCFD_LLM_TIMEOUT / TCFD_LLM_TEMPERATURE
  - TCFD_PATH_INPUT_ROOT / TCFD_PATH_OUTPUT_ROOT
  - TCFD_BATCH_WORKERS / TCFD_BATCH_MAX_RETRIES / TCFD_BATCH_RETRY_DELAY / TCFD_BATCH_REASON_MAX_LENGTH
"""
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LLMSettings(BaseSettings):
    """LLM 调用相关配置"""
    model_config = SettingsConfigDict(env_prefix="TCFD_LLM_")

    base_url: str = "http://127.0.0.1:30000/v1"
    api_key: str = "sk-local"
    model_name: str = "Qwen/Qwen3.5-35B-A3B"
    timeout: int = 60
    temperature: float = 0.1


class PathSettings(BaseSettings):
    """路径相关配置"""
    model_config = SettingsConfigDict(env_prefix="TCFD_PATH_")

    input_root: Path = Field(default_factory=lambda: Path("output/frequency/cooccurrence_context"))
    output_root: Path = Field(default_factory=lambda: Path("output/evaluate_cooccurrence"))


class BatchSettings(BaseSettings):
    """批处理相关配置"""
    model_config = SettingsConfigDict(env_prefix="TCFD_BATCH_")

    workers: int = 8
    max_retries: int = 3
    retry_delay: float = 1.0
    reason_max_length: int = 50


# 全局单例(惰性求值,模块导入时构造)
llm_settings = LLMSettings()
path_settings = PathSettings()
batch_settings = BatchSettings()