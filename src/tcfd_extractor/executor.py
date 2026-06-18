import threading
import time
from typing import List, Any, Callable, Dict

from threading import Semaphore, Lock


class ControlledExecutor:
    """带并发控制的任务执行器"""

    def __init__(self, max_workers: int = 8):
        self.semaphore = Semaphore(max_workers)
        self.max_workers = max_workers
        self.active_count = 0
        self.lock = Lock()
        self.task_count = 0
        self.completed_count = 0

        # 使用独立的结果容器，避免数据混乱
        self.file_results: Dict[str, List[Any]] = {}

    def submit(self, func: Callable, file_key: str, *args, **kwargs):
        """提交任务，自动管理并发 - 先获取信号量再获取锁"""
        self.semaphore.acquire()

        with self.lock:
            self.active_count += 1
            self.task_count += 1
            if file_key not in self.file_results:
                self.file_results[file_key] = []

        def wrapper():
            try:
                result = func(*args, **kwargs)
                with self.lock:
                    self.file_results[file_key].append(result)
            except Exception as e:
                with self.lock:
                    if "errors" not in self.file_results:
                        self.file_results["errors"] = []
                    self.file_results["errors"].append({"task": str(args[:1]), "error": str(e)})
            finally:
                with self.lock:
                    self.active_count -= 1
                    self.completed_count += 1
                self.semaphore.release()

        thread = threading.Thread(target=wrapper, daemon=True)
        thread.start()
        return thread

    def wait_for_file_completion(self, file_key: str, expected_count: int, check_interval: float = 0.5):
        """等待指定文件的所有任务完成"""
        max_loops = 120  # 最多等待60秒
        loops = 0
        while True:
            with self.lock:
                current_count = len(self.file_results.get(file_key, []))
                error_count = len(self.file_results.get("errors", []))

            if current_count >= expected_count:
                break
            if error_count > 0 and current_count + error_count >= expected_count:
                break
            time.sleep(check_interval)
            loops += 1
            if loops > max_loops:
                break

    def get_file_results(self, file_key: str) -> List[Any]:
        """获取指定文件的结果"""
        with self.lock:
            return self.file_results.get(file_key, []).copy()

    def clear_file_results(self, file_key: str):
        """清除指定文件的结果"""
        with self.lock:
            if file_key in self.file_results:
                del self.file_results[file_key]

    def wait_until_complete(self, check_interval: float = 1.0):
        """等待所有任务完成"""
        while self.active_count > 0:
            time.sleep(check_interval)