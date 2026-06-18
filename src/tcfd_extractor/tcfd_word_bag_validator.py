# src/tcfd_extractor/tcfd_word_bag_validator.py
import argparse
import json
import time
from pathlib import Path

from openai import OpenAI
from pydantic import BaseModel, Field


class TCFDValidationResult(BaseModel):
    """TCFD验证结果 - 返回符合标准的关键词列表"""
    valid_keywords: list[str] = Field(
        description="符合TCFD标准的关键词列表"
    )


SYSTEM_PROMPT = """你是一位资深的 ESG 分析师和 TCFD（气候相关财务信息披露）专家，精通气候变化对企业造成的财务影响、转型风险及气候机遇。

你的任务是判断给定的关键词是否符合 TCFD 框架标准。

# TCFD 校验标准 (严格执行)
一个词必须与"气候变化、温室气体减排、低碳转型、或适应气候变化"有直接关联，才能被保留。

**保留标准：**
- 与碳减排政策、气候法规相关（碳税、碳交易、排放限制等）
- 与低碳转型带来的市场变化相关（绿色偏好、绿电溢价、可持续供应链等）
- 与低碳/节能/清洁能源技术相关（变频电机、新能源汽车、超级电容等）
- ESG相关（ESG评级、ESG投资、可持续发展等与气候/环境相关）

**排除标准：**
- 与气候无关的普通税收、常规劳动法、普通工商政策
- 常规宏观经济波动、与环保无关的消费升级
- 常规 IT 技术、与节能减排无关的普通机械设备、普通互联网技术
"""


def parse_args(args=None):
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="TCFD词袋验证器 - 根据TCFD框架过滤关键词"
    )
    parser.add_argument(
        "--input", required=True, help="输入JSON词袋文件路径"
    )
    parser.add_argument(
        "--output", required=True, help="输出JSON结果文件路径（保留的关键词）"
    )
    parser.add_argument(
        "--output-rejected",
        help="输出JSON文件路径（剔除的关键词）"
    )
    parser.add_argument(
        "--batch-size", type=int, default=20,
        help="每批处理的关键词数量 (default: 20)"
    )
    parser.add_argument(
        "--api-url", default="http://0.0.0.0:30000/v1",
        help="LLM API端点"
    )
    parser.add_argument(
        "--model", default="Qwen/Qwen3.5-35B-A3B",
        help="模型名称"
    )
    parser.add_argument(
        "--temperature", type=float, default=0.1,
        help="生成温度 (default: 0.1)"
    )
    return parser.parse_args(args)


def load_word_bag(path: str) -> dict:
    """加载嵌套JSON词袋文件。"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_batch(
    keywords: list[str],
    api_url: str,
    model: str,
    temperature: float = 0.1,
    max_retries: int = 3
) -> TCFDValidationResult:
    """验证一批关键词，返回符合TCFD标准的关键词。"""
    client = OpenAI(base_url=api_url, api_key="sk-local")

    keywords_text = "\n".join(f"- {kw}" for kw in keywords)

    user_prompt = f"""请判断以下关键词哪些符合 TCFD 标准。返回符合标准的关键词列表。

关键词列表：
{keywords_text}

请直接输出 JSON，不要包含任何解释或额外文本。"""

    last_exception = None
    for attempt in range(max_retries):
        try:
            response = client.beta.chat.completions.parse(
                model=model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                response_format=TCFDValidationResult,
                temperature=temperature,
                timeout=60,
            )
            return response.choices[0].message.parsed
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                time.sleep(2 * (attempt + 1))

    raise last_exception


def process_word_bag(
    word_bag: dict,
    validate_func,
    batch_size: int = 20
) -> tuple[dict, dict]:
    """处理词袋，对每个分类的关键词进行验证，保留原结构。

    Args:
        word_bag: 嵌套结构的词袋
        validate_func: 验证函数，接受关键词列表返回TCFDValidationResult
        batch_size: 每批处理的关键词数量

    Returns:
        (valid_result, rejected_result): 两个嵌套结构的词袋，分别包含保留和剔除的关键词
    """
    valid_result = {}
    rejected_result = {}
    total_keywords = 0
    valid_count = 0

    for category, subcategories in word_bag.items():
        if isinstance(subcategories, dict):
            valid_result[category] = {}
            rejected_result[category] = {}
            for subcategory, keywords in subcategories.items():
                if isinstance(keywords, list):
                    total_keywords += len(keywords)
                    valid, rejected = _process_category(keywords, validate_func, batch_size)
                    valid_result[category][subcategory] = valid
                    rejected_result[category][subcategory] = rejected
                    valid_count += len(valid)
                    print(f"  {category}/{subcategory}: {len(keywords)} -> {len(valid)} (剔除 {len(rejected)})")
        elif isinstance(subcategories, list):
            total_keywords += len(subcategories)
            valid, rejected = _process_category(subcategories, validate_func, batch_size)
            valid_result[category] = valid
            rejected_result[category] = rejected
            valid_count += len(valid)
            print(f"  {category}: {len(subcategories)} -> {len(valid)} (剔除 {len(rejected)})")

    print(f"\n总计: {total_keywords} 个关键词，保留 {valid_count} 个 (剔除 {total_keywords - valid_count} 个)")
    return valid_result, rejected_result


def _process_category(
    keywords: list[str],
    validate_func,
    batch_size: int
) -> tuple[list[str], list[str]]:
    """处理单个分类的关键词列表。

    Returns:
        (valid_keywords, rejected_keywords): 保留和剔除的关键词列表
    """
    if not keywords:
        return [], []

    all_valid = set()
    all_rejected = set()

    for i in range(0, len(keywords), batch_size):
        batch = keywords[i:i + batch_size]
        batch_num = i // batch_size + 1

        try:
            result = validate_func(batch)
            valid_set = set(result.valid_keywords)
            rejected_set = set(batch) - valid_set
            all_valid.update(valid_set)
            all_rejected.update(rejected_set)
        except Exception as e:
            print(f"    警告: 批次 {batch_num} 处理失败: {e}")
            # Fail-open: keep all keywords in failed batch
            all_valid.update(batch)

    return sorted(list(all_valid)), sorted(list(all_rejected))


def save_results(data: dict, output_path: str):
    """保存结果到JSON文件，保持原结构。"""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"结果已保存到: {output_path}")


def main():
    """主函数"""
    args = parse_args()

    print(f"加载词袋: {args.input}")
    word_bag = load_word_bag(args.input)

    def validate_func(batch):
        return validate_batch(batch, args.api_url, args.model, args.temperature)

    print(f"\n开始验证...")
    valid_result, rejected_result = process_word_bag(word_bag, validate_func, args.batch_size)

    save_results(valid_result, args.output)
    if args.output_rejected:
        save_results(rejected_result, args.output_rejected)
        print(f"剔除的关键词已保存到: {args.output_rejected}")
    print("\n验证完成!")


if __name__ == "__main__":
    main()