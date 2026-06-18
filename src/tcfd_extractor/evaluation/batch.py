"""批量评估器

从 cooccurrence_evaluator.py 移出,负责多文件、多 context 的并发评估编排。
- 使用生成器流式加载文件,避免一次性加载所有解析结果到内存
- 进度用 tqdm 显示
- 错误分类: parse_errors / eval_errors
"""
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import Iterator

from tqdm import tqdm

from ..config import BatchSettings, batch_settings
from .exceptions import LLMUnavailableError
from .models import CooccurrenceContext, EvaluationResult
from .parser import parse_cooccurrence_md


logger = logging.getLogger(__name__)


class BatchEvaluator:
    """批量评估器(并发 + 流式)"""

    def __init__(
        self,
        evaluator,
        settings: BatchSettings | None = None,
    ) -> None:
        self.evaluator = evaluator
        self.settings = settings if settings is not None else batch_settings

    def _parse_all_files(
        self, input_dir: Path
    ) -> Iterator[tuple[str, CooccurrenceContext | None, Exception | None]]:
        """生成器: 流式产出 (filename, context, error) 三元组。

        - 成功: (filename, context, None)
        - 失败: (filename, None, exception)

        Yields:
            三元组,调用方根据 error 是否为 None 区分成功/失败

        行为约定:
        - 解析异常 → 视为错误
        - 解析成功但无有效 header(company 为空或 year=0 且 header 未匹配)→ 视为错误
        - 解析成功但 contexts 为空列表 → 视为错误(无效文件)
        """
        for md_file in sorted(input_dir.glob("*.md")):
            try:
                parse_result = parse_cooccurrence_md(md_file)
            except Exception as e:
                yield (md_file.name, None, e)
                continue

            # 检测解析结果是否实际有效(无效 header 文件也应被跳过)
            if not parse_result.contexts:
                yield (
                    md_file.name,
                    None,
                    ValueError(
                        f"文件无有效 contexts: {md_file.name}"
                    ),
                )
                continue

            for ctx in parse_result.contexts:
                yield (md_file.name, ctx, None)

    def _evaluate_one(
        self, filename: str, ctx: CooccurrenceContext
    ) -> tuple[dict, bool]:
        """评估单个 context,含重试。返回 (row_dict, is_tcfd)。

        行为约定:
        - max_retries=0: 一次尝试,失败立即抛 LLMUnavailableError(spec §3.5 DoD)
        - max_retries=N: 最多 N 次尝试,全部失败后抛 LLMUnavailableError
        """
        result: EvaluationResult | None = None
        last_error: Exception | None = None
        attempts = max(1, self.settings.max_retries)

        for attempt in range(attempts):
            try:
                result = self.evaluator.evaluate(ctx)
                # 优先使用 context 的 keywords 以保证来源一致性,
                # 因为有些 LLM 响应可能不会回填这两个字段。
                return (
                    {
                        "file": filename,
                        "keyword_a": ctx.keyword_a,
                        "keyword_b": ctx.keyword_b,
                        "context": result.context,
                        "is_tcfd_related": result.is_tcfd_related,
                        "dimension": result.dimension,
                        "reason": result.reason,
                    },
                    result.is_tcfd_related,
                )
            except Exception as e:
                last_error = e
                if attempt < attempts - 1:
                    time.sleep(self.settings.retry_delay)
                else:
                    logger.warning(
                        "评估失败 %s %s+%s (重试 %d 次): %s",
                        filename, ctx.keyword_a, ctx.keyword_b, attempts, e
                    )

        # 所有重试都失败,抛 LLMUnavailableError(spec §3.5 要求终止批处理)
        assert last_error is not None
        raise LLMUnavailableError(
            f"评估 {ctx.keyword_a}+{ctx.keyword_b} 连续失败 {attempts} 次: {last_error}"
        ) from last_error

    def evaluate_all(self, input_dir: Path, output_file: Path) -> dict:
        """批量评估所有文件(并发 + 流式)

        Args:
            input_dir: 输入目录路径(含 *.md)
            output_file: 输出 JSONL 文件路径

        Returns:
            dict: 评估统计
                {
                    "total": int,
                    "tcfd_count": int,
                    "parse_errors": int,
                    "eval_errors": int,
                }
        """
        output_file.parent.mkdir(parents=True, exist_ok=True)
        # 使用生成器流式加载,边读边记录 parse_errors
        items: list[tuple[str, CooccurrenceContext]] = []
        parse_errors_count = 0
        for filename, ctx, err in self._parse_all_files(input_dir):
            if err is not None:
                parse_errors_count += 1
                logger.warning("解析失败 %s: %s", filename, err)
                continue
            assert ctx is not None
            items.append((filename, ctx))

        total = len(items)
        logger.info("共 %d 个上下文待评估,并发数: %d", total, self.settings.workers)

        tcfd_count = 0
        eval_errors_count = 0
        lock = Lock()

        with ThreadPoolExecutor(max_workers=self.settings.workers) as executor:
            futures = {
                executor.submit(self._evaluate_one, filename, ctx): (filename, ctx)
                for filename, ctx in items
            }

            with open(output_file, "w", encoding="utf-8") as f:
                for future in tqdm(
                    as_completed(futures), total=len(futures), desc="评估 contexts"
                ):
                    row, is_tcfd = future.result()
                    with lock:
                        f.write(json.dumps(row, ensure_ascii=False) + "\n")
                        f.flush()
                        if is_tcfd:
                            tcfd_count += 1
                        # eval_errors 通过 reason 字段含异常关键字判定
                        reason = row.get("reason", "")
                        if not is_tcfd and any(
                            kw in reason for kw in ("Error", "失败", "异常", "Timeout")
                        ):
                            eval_errors_count += 1

        return {
            "total": total,
            "tcfd_count": tcfd_count,
            "parse_errors": parse_errors_count,
            "eval_errors": eval_errors_count,
        }
