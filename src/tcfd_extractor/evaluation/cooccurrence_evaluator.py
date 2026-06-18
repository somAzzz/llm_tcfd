# src/tcfd_extractor/evaluation/cooccurrence_evaluator.py
"""共现上下文评估模块 - 评估共现上下文是否符合TCFD标准"""

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from threading import Lock
from typing import Iterator

from openai import OpenAI
from pydantic import BaseModel, Field


class CooccurrenceContext(BaseModel):
    """共现上下文片段"""

    keyword_a: str
    keyword_b: str
    context: str
    position: int
    count: int = 1  # 共现次数


class TCFDValidationResult(BaseModel):
    """LLM返回的TCFD验证结果"""

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


# ============ Markdown解析器 ============


def parse_cooccurrence_md(filepath: Path) -> FileParseResult:
    """解析共现上下文MD文件

    Args:
        filepath: MD文件路径

    Returns:
        FileParseResult: 解析后的文件结果

    Raises:
        ValueError: 无法解析文件头时抛出
    """
    content = filepath.read_text(encoding="utf-8")

    # 解析公司名和年份: # 公司名 - 年份[年度]报告
    # 匹配: # 公司名 - 2020年度报告 或 # 公司名 - 2020报告
    header_match = re.match(r"# (.+) - (\d{4})年?度?报告", content)
    if header_match:
        company = header_match.group(1)
        year = int(header_match.group(2))
    else:
        # 解析失败时，使用文件名作为 fallback
        # 年份从目录路径获取（如 cooccurrence_context/2024/）
        # 公司名使用文件名（去掉.md）
        parts = filepath.parts
        year = 0
        for p in parts:
            m = re.match(r'^(\d{4})$', p)
            if m and 1900 <= int(m.group(1)) <= 2100:
                year = int(m.group(1))
                break
        stem = filepath.stem  # 去掉 .md
        company = stem if stem else str(filepath)
        if not company:
            raise ValueError(f"无法解析文件头: {filepath}")

    # 提取所有共现对和上下文
    contexts: list[CooccurrenceContext] = []

    # 模式: **关键词A** + **关键词B** (N次共现)
    pair_pattern = r"\*\*(.+?)\*\* \+ \*\*(.+?)\*\* \((\d+)次共现\)"
    # 模式: N. "...上下文..." (位置: 数字)
    context_pattern = r'\d+\. "\.\.\.(.+?)\.\.\." \(位置: (\d+)\)'

    pair_matches = list(re.finditer(pair_pattern, content))
    for i, pair_match in enumerate(pair_matches):
        keyword_a = pair_match.group(1)
        keyword_b = pair_match.group(2)
        count = int(pair_match.group(3))

        # 找下一个pair_match之前的所有上下文
        start = pair_match.end()
        next_match = pair_matches[i + 1] if i + 1 < len(pair_matches) else None
        end = next_match.start() if next_match else len(content)

        pair_section = content[start:end]
        for ctx_match in re.finditer(context_pattern, pair_section):
            contexts.append(
                CooccurrenceContext(
                    keyword_a=keyword_a,
                    keyword_b=keyword_b,
                    context=ctx_match.group(1),
                    position=int(ctx_match.group(2)),
                    count=count,
                )
            )

    return FileParseResult(
        file=filepath.name, company=company, year=year, contexts=contexts
    )


# ============ LLM评估器 ============

EVAL_SYSTEM_PROMPT = """你是一位资深的 TCFD（气候相关财务披露）评估专家。请判断提供的文本上下文是否构成实质性的 TCFD 气候风险或机遇披露，并明确其所属的具体维度。

【判断与分类标准】
1. 政策维度 (Policy)：涉及碳排限制、碳税、碳交易、环保合规成本增加、趋严的气候法规或政府绿电/减排补贴。
2. 市场维度 (Market)：涉及低碳产品需求变化、消费者绿色偏好、气候/减碳导致的原材料价格波动或可持续供应链要求。
3. 技术维度 (Technology)：涉及低碳/节能技术转型、可再生能源替代、新能源产品研发或高耗能落后产能淘汰。

【排除标准（以下情况必须判定为 false）】
- 否定表述：上下文中含有“未发现”、“不涉及”、“不适用”、“尚未”等否定语义。

**极其重要：你必须且只能输出合法的纯 JSON 格式数据。绝对不要输出任何 Markdown 格式符号（如 ```json）、不要输出思考过程、不要输出任何额外的解释文本。**

【输出 JSON 结构】
{
  "is_tcfd_related": true, 
  "dimension": "政策", 
  "reason": "简要说明共现词在当前语境下如何具体体现该维度的风险/机遇，或说明被排除的原因。"
}
注：dimension 字段的值必须是 "政策"、"市场"、"技术" 中的一个；如果 is_tcfd_related 为 false，则 dimension 必须输出 "无"。"""


EVAL_USER_PROMPT = """共现目标词：[{keyword_a}] + [{keyword_b}]
待评估上下文：{context}

请严格按照要求的 JSON 格式输出评估结果："""


class CooccurrenceEvaluator:
    """共现上下文LLM评估器"""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:30000/v1",
        model_name: str = "Qwen/Qwen3.5-35B-A3B",
    ):
        self.client = OpenAI(base_url=base_url, api_key="sk-local")
        self.model_name = model_name

    def _parse_json_response(self, text: str) -> dict:
        """解析JSON响应，处理各种格式问题"""
        text = text.strip()

        # 情况1: 纯JSON直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 情况2: 包含Thinking Process，需要提取JSON
        # 查找最后一个 { 到最后一个 } 之间的内容
        import re

        # 尝试匹配 {...} 模式（可能有嵌套）
        json_matches = list(re.finditer(r"\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}", text))
        if json_matches:
            # 取最后一个匹配（通常JSON在最后）
            for match in reversed(json_matches):
                try:
                    result = json.loads(match.group())
                    if "is_tcfd_related" in result:
                        return result
                except json.JSONDecodeError:
                    continue

        # 情况3: 如果上面都失败，抛出异常
        raise ValueError(f"无法解析响应: {text[:200]}...")

    def evaluate(self, context: CooccurrenceContext) -> EvaluationResult:
        """评估单个上下文片段

        Args:
            context: 共现上下文片段

        Returns:
            EvaluationResult: 评估结果
        """
        try:
            response = self.client.beta.chat.completions.parse(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": EVAL_SYSTEM_PROMPT},
                    {
                        "role": "user",
                        "content": EVAL_USER_PROMPT.format(
                            keyword_a=context.keyword_a,
                            keyword_b=context.keyword_b,
                            context=context.context,
                        ),
                    },
                ],
                response_format=TCFDValidationResult,
                temperature=0.1,
                timeout=60,
            )
            parsed = response.choices[0].message.parsed
        except Exception as e:
            raise ValueError(f"LLM调用失败: {e}")

        return EvaluationResult(
            keyword_a=context.keyword_a,
            keyword_b=context.keyword_b,
            context=context.context,
            position=context.position,
            is_tcfd_related=parsed.is_tcfd_related,
            dimension=parsed.dimension,
            reason=parsed.reason[:50] if parsed.reason else "",
        )


# ============ 批量评估器 ============


class BatchEvaluator:
    """批量评估器（并行版本）"""

    def __init__(
        self,
        evaluator: CooccurrenceEvaluator,
        max_retries: int = 3,
        workers: int = 8,
    ):
        self.evaluator = evaluator
        self.max_retries = max_retries
        self.workers = workers

    def _parse_all_files(self, input_dir: Path) -> Iterator[tuple[str, CooccurrenceContext]]:
        """解析所有文件，返回 (filename, context) 元组"""
        for md_file in sorted(input_dir.glob("*.md")):
            try:
                parse_result = parse_cooccurrence_md(md_file)
            except Exception as e:
                print(f"解析失败 {md_file.name}: {e}")
                continue

            for ctx in parse_result.contexts:
                yield (md_file.name, ctx)

    def _evaluate_one(
        self,
        filename: str,
        ctx: CooccurrenceContext,
    ) -> tuple[dict, bool]:
        """评估单个上下文"""
        for attempt in range(self.max_retries):
            try:
                result = self.evaluator.evaluate(ctx)
                break
            except Exception as e:
                if attempt == self.max_retries - 1:
                    error_reason = str(e)[:47] + "..." if len(str(e)) > 50 else str(e)
                    result = EvaluationResult(
                        keyword_a=ctx.keyword_a,
                        keyword_b=ctx.keyword_b,
                        context=ctx.context,
                        position=ctx.position,
                        is_tcfd_related=False,
                        dimension="无",
                        reason=error_reason,
                    )
                    print(f"评估失败 {filename} {ctx.keyword_a}+{ctx.keyword_b}: {e}")
                else:
                    time.sleep(1)

        row = {
            "file": filename,
            "keyword_a": result.keyword_a,
            "keyword_b": result.keyword_b,
            "context": result.context,
            "is_tcfd_related": result.is_tcfd_related,
            "dimension": result.dimension,
            "reason": result.reason,
        }
        return row, result.is_tcfd_related

    def evaluate_all(
        self,
        input_dir: Path,
        output_file: Path,
    ) -> dict:
        """批量评估所有文件（并行）

        Args:
            input_dir: 输入目录路径
            output_file: 输出JSONL文件路径

        Returns:
            dict: 评估统计 {"total": int, "tcfd_count": int}
        """
        output_file.parent.mkdir(parents=True, exist_ok=True)

        # 先解析所有文件
        items = list(self._parse_all_files(input_dir))
        total = len(items)
        print(f"共 {total} 个上下文待评估，并发数: {self.workers}")

        tcfd_count = 0
        lock = Lock()

        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = {
                executor.submit(self._evaluate_one, filename, ctx): (filename, ctx)
                for filename, ctx in items
            }

            with open(output_file, "w", encoding="utf-8") as f:
                for future in as_completed(futures):
                    row, is_tcfd = future.result()
                    with lock:
                        f.write(json.dumps(row, ensure_ascii=False) + "\n")
                        f.flush()
                        if is_tcfd:
                            tcfd_count += 1

                    # 进度显示
                    done = len([f for f in futures if f.done()])
                    print(f"\r进度: {done}/{total}", end="", flush=True)

        print()  # 换行
        return {"total": total, "tcfd_count": tcfd_count}


# ============ 总结生成器 ============

SUMMARY_SYSTEM_PROMPT = """你是一位资深的 ESG 与 TCFD（气候相关财务信息披露）评估分析师。
你的专长是通过“政策（Policy）”、“市场（Market）”和“技术（Technology）”三个核心维度来深度剖析企业的气候风险与机遇。
请基于提供的评估数据，生成结构清晰、具有高度专业性且高度聚焦这三个维度的总结报告。"""

SUMMARY_USER_PROMPT = """请分析以下 TCFD 共现评估结果，并严格从“政策、市场、技术”三个维度进行深度解读，生成总结报告：

【评估统计】
- 总片段数：{total}
- TCFD相关数：{tcfd_count}
- 非TCFD相关数：{non_tcfd_count}
- 准确率：{accuracy}%
（注：如果您的代码中能统计各维度的数量，可以解除下面这一行的注释并传入变量）
# - 维度分布：政策类 {policy_count} | 市场类 {market_count} | 技术类 {tech_count}

请严格按照以下 Markdown 格式输出：

## 1. 准确率与整体统计
（基于提供的统计数据进行整体概括，评估当前文本共现匹配方案的整体信噪比和有效性。）

## 2. 核心问题分析（基于三大维度）
请结合共现匹配中发现的噪音词、覆盖度、上下文等问题，按以下维度进行深度剖析：
* **政策维度 (Policy & Legal)**：（分析碳税、环保合规成本、排放限制等相关政策法律词汇的误报或漏报情况）
* **市场维度 (Market & Reputation)**：（分析市场需求、绿色偏好、原材料价格波动等词汇的匹配准确性与歧义问题）
* **技术维度 (Technology)**：（分析低碳技术、可再生能源、新能源产品等词汇在非气候语境下的泛化或干扰问题）
* **通用/其他问题**：（如跨维度的高频通用 ESG 词汇“风险”、“影响”带来的整体干扰）

## 3. 针对性优化建议
请针对上述问题，提供具体的规则、词袋或逻辑优化建议：
* **政策维度优化**：（如需新增哪些专有政策词汇，或增加哪些排除词）
* **市场维度优化**：（如何将宽泛的“价格”、“需求”限定在气候财务影响的语境中）
* **技术维度优化**：（如何排除常规技术的干扰，精准定位低碳转型技术）
* **底层处理流程优化**：（如句法距离限制、否定词过滤、动态权重打分制等）

要求：使用中文输出，语言专业严谨，逻辑清晰。"""


def generate_summary(
    results_file: Path,
    summary_file: Path,
    base_url: str = "http://127.0.0.1:30000/v1",
    model_name: str = "Qwen/Qwen3.5-35B-A3B",
) -> dict:
    """生成评估总结

    Args:
        results_file: JSONL评估结果文件路径
        summary_file: 输出Markdown总结文件路径
        base_url: LLM API地址
        model_name: 模型名称

    Returns:
        dict: 统计信息 {"total": int, "tcfd_count": int, "accuracy": float}
    """
    # 读取统计
    total = 0
    tcfd_count = 0
    policy_count = 0
    market_count = 0
    tech_count = 0

    with open(results_file, encoding="utf-8") as f:
        for line in f:
            item = json.loads(line)
            total += 1
            if item["is_tcfd_related"]:
                tcfd_count += 1
                dimension = item.get("dimension", "无")
                if dimension == "政策":
                    policy_count += 1
                elif dimension == "市场":
                    market_count += 1
                elif dimension == "技术":
                    tech_count += 1

    non_tcfd_count = total - tcfd_count
    accuracy = (tcfd_count / total * 100) if total > 0 else 0

    # 调用LLM生成报告
    client = OpenAI(base_url=base_url, api_key="sk-local")
    response = client.chat.completions.create(
        model=model_name,
        messages=[
            {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": SUMMARY_USER_PROMPT.format(
                    total=total,
                    tcfd_count=tcfd_count,
                    non_tcfd_count=non_tcfd_count,
                    accuracy=round(accuracy, 2),
                    policy_count=policy_count,
                    market_count=market_count,
                    tech_count=tech_count,
                ),
            },
        ],
        temperature=0.1,
        timeout=60,
    )

    summary_content = response.choices[0].message.content

    # 保存
    summary_file.write_text(summary_content, encoding="utf-8")
    print(f"总结已保存到: {summary_file}")

    return {
        "total": total,
        "tcfd_count": tcfd_count,
        "accuracy": accuracy,
        "policy_count": policy_count,
        "market_count": market_count,
        "tech_count": tech_count,
    }
