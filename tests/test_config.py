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


class TestGlobalSingletonThreadSafety:
    """配置全局单例线程安全 DoD 测试"""

    def test_concurrent_settings_access(self):
        """spec §6.4 DoD: 多线程并发访问全局单例不应引发数据竞争

        通过 concurrent.futures 创建 8 个线程,每个线程读 1000 次 settings。
        验证:
        1. 不抛异常
        2. 读到的 settings 是同一个对象
        """
        from concurrent.futures import ThreadPoolExecutor
        results = []

        def read_settings():
            for _ in range(1000):
                results.append(id(llm_settings))
            return llm_settings.base_url

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(read_settings) for _ in range(8)]
            for f in futures:
                f.result()  # 抛异常则 fail

        # 验证 8000 次读到的都是同一个对象
        assert len(set(results)) == 1, f"发现 {len(set(results))} 个不同对象,存在数据竞争"
        assert results[0] == id(llm_settings)

    def test_path_settings_immutable_under_concurrent_read(self):
        """PathSettings 在并发读下保持一致"""
        from concurrent.futures import ThreadPoolExecutor

        def read_path():
            return path_settings.input_root

        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(lambda _: read_path(), range(100)))

        # 全部读到同一个 Path 对象
        assert all(r == results[0] for r in results)

    def test_batch_settings_immutable_under_concurrent_read(self):
        """BatchSettings 在并发读下保持一致"""
        from concurrent.futures import ThreadPoolExecutor

        def read_workers():
            return batch_settings.workers

        with ThreadPoolExecutor(max_workers=4) as executor:
            results = list(executor.map(lambda _: read_workers(), range(100)))

        assert all(r == 8 for r in results)