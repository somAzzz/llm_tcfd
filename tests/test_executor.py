import pytest
import time
from tcfd_extractor.executor import ControlledExecutor

def test_executor_init():
    """测试执行器初始化"""
    executor = ControlledExecutor(max_workers=4)
    assert executor.max_workers == 4
    assert executor.active_count == 0

def test_submit_task():
    """测试提交任务"""
    executor = ControlledExecutor(max_workers=2)
    results = []

    def add_item(item):
        results.append(item)
        return item

    executor.submit(add_item, "test_key", "hello")
    time.sleep(0.5)
    assert "hello" in results

def test_concurrent_limit():
    """测试并发限制"""
    executor = ControlledExecutor(max_workers=2)
    active = []

    def task(n):
        active.append(n)
        time.sleep(0.1)
        active.remove(n)

    # 同时提交3个任务，但最大并发为2
    for i in range(3):
        executor.submit(task, f"key_{i}", i)

    time.sleep(0.15)
    # 最多2个任务同时执行
    assert len(active) <= 2