"""全局配置测试"""
from pathlib import Path

from tcfd_extractor.config import (
    LLMSettings,
    PathSettings,
    BatchSettings,
    llm_settings,
    path_settings,
    batch_settings,
)


class TestLLMSettings:
    def test_default_base_url(self):
        s = LLMSettings()
        assert s.base_url == "http://127.0.0.1:30000/v1"

    def test_default_model_name(self):
        s = LLMSettings()
        assert s.model_name == "Qwen/Qwen3.5-35B-A3B"

    def test_default_api_key(self):
        s = LLMSettings()
        assert s.api_key == "sk-local"

    def test_default_timeout(self):
        s = LLMSettings()
        assert s.timeout == 60

    def test_default_temperature(self):
        s = LLMSettings()
        assert s.temperature == 0.1

    def test_env_var_override(self, monkeypatch):
        monkeypatch.setenv("TCFD_LLM_BASE_URL", "http://example.com:8080/v1")
        s = LLMSettings()
        assert s.base_url == "http://example.com:8080/v1"

    def test_env_var_model_override(self, monkeypatch):
        monkeypatch.setenv("TCFD_LLM_MODEL_NAME", "custom-model")
        s = LLMSettings()
        assert s.model_name == "custom-model"


class TestPathSettings:
    def test_default_input_root(self):
        s = PathSettings()
        assert s.input_root == Path("output/frequency/cooccurrence_context")

    def test_default_output_root(self):
        s = PathSettings()
        assert s.output_root == Path("output/evaluate_cooccurrence")

    def test_path_type_is_path(self):
        s = PathSettings()
        assert isinstance(s.input_root, Path)
        assert isinstance(s.output_root, Path)

    def test_env_var_override(self, monkeypatch):
        monkeypatch.setenv("TCFD_PATH_INPUT_ROOT", "/tmp/custom")
        s = PathSettings()
        assert s.input_root == Path("/tmp/custom")


class TestBatchSettings:
    def test_default_workers(self):
        s = BatchSettings()
        assert s.workers == 8

    def test_default_max_retries(self):
        s = BatchSettings()
        assert s.max_retries == 3

    def test_default_retry_delay(self):
        s = BatchSettings()
        assert s.retry_delay == 1.0

    def test_default_reason_max_length(self):
        s = BatchSettings()
        assert s.reason_max_length == 50


class TestGlobalSingletons:
    def test_llm_settings_is_llmsettings(self):
        assert isinstance(llm_settings, LLMSettings)

    def test_path_settings_is_pathsettings(self):
        assert isinstance(path_settings, PathSettings)

    def test_batch_settings_is_batchsettings(self):
        assert isinstance(batch_settings, BatchSettings)