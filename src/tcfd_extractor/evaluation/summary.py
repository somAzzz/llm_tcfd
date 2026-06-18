"""统计计算与总结生成

从 cooccurrence_evaluator.py 移出,解耦了统计计算和 LLM 调用。
- compute_statistics: 纯函数,从 JSONL 读数据并统计
- generate_summary: 接受预先计算好的 stats,调用 LLM 生成总结
"""
import json
import logging
from pathlib import Path

from openai import OpenAI

from ..config import LLMSettings, llm_settings
from .exceptions import LLMEvaluationError
from .prompts import SUMMARY_SYSTEM_PROMPT, SUMMARY_USER_PROMPT


logger = logging.getLogger(__name__)


def compute_statistics(results_file: Path) -> dict:
    """从 JSONL 结果文件计算统计信息

    Args:
        results_file: JSONL 评估结果文件路径

    Returns:
        dict: {
            "total": int,
            "tcfd_count": int,
            "non_tcfd_count": int,
            "accuracy": float,  # 0-100
            "policy_count": int,
            "market_count": int,
            "tech_count": int,
        }
    """
    total = 0
    tcfd_count = 0
    policy_count = 0
    market_count = 0
    tech_count = 0

    with open(results_file, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                item = json.loads(line)
            except json.JSONDecodeError:
                logger.warning("跳过损坏行: %s", line[:100])
                continue

            total += 1
            if item.get("is_tcfd_related"):
                tcfd_count += 1
                dimension = item.get("dimension", "无")
                if dimension == "政策":
                    policy_count += 1
                elif dimension == "市场":
                    market_count += 1
                elif dimension == "技术":
                    tech_count += 1

    non_tcfd_count = total - tcfd_count
    accuracy = (tcfd_count / total * 100) if total > 0 else 0.0

    return {
        "total": total,
        "tcfd_count": tcfd_count,
        "non_tcfd_count": non_tcfd_count,
        "accuracy": accuracy,
        "policy_count": policy_count,
        "market_count": market_count,
        "tech_count": tech_count,
    }


def generate_summary(
    stats: dict,
    summary_file: Path,
    settings: LLMSettings | None = None,
) -> None:
    """生成评估总结

    Args:
        stats: compute_statistics() 返回的统计字典
        summary_file: 输出 Markdown 总结文件路径
        settings: LLM 配置(默认全局 llm_settings)

    Raises:
        LLMEvaluationError: LLM 调用失败
    """
    cfg = settings if settings is not None else llm_settings

    try:
        client = OpenAI(base_url=cfg.base_url, api_key=cfg.api_key)
        response = client.chat.completions.create(
            model=cfg.model_name,
            messages=[
                {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": SUMMARY_USER_PROMPT.format(
                        total=stats["total"],
                        tcfd_count=stats["tcfd_count"],
                        non_tcfd_count=stats["non_tcfd_count"],
                        accuracy=round(stats["accuracy"], 2),
                        policy_count=stats.get("policy_count", 0),
                        market_count=stats.get("market_count", 0),
                        tech_count=stats.get("tech_count", 0),
                    ),
                },
            ],
            temperature=cfg.temperature,
            timeout=cfg.timeout,
        )
    except Exception as e:
        logger.exception("总结 LLM 调用失败: %s", e)
        raise LLMEvaluationError(f"总结 LLM 调用失败: {e}") from e

    summary_content = response.choices[0].message.content
    summary_file.write_text(summary_content, encoding="utf-8")
    logger.info("总结已保存到: %s", summary_file)