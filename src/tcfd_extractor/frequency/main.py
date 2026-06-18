"""TCFD词频统计CLI

Examples:
    # 基本用法（固定窗口30字）
    python -m tcfd_extractor.frequency.main \\
        --data-dir /path/to/年报数据 \\
        --output-dir output/frequency

    # 启用公司过滤（A后10字内含"公司"则不统计）
    python -m tcfd_extractor.frequency.main \\
        --data-dir /path/to/年报数据 \\
        --output-dir output/frequency \\
        --exclude-company

    # 启用句子窗口（窗口边界限制为前后句号）
    python -m tcfd_extractor.frequency.main \\
        --data-dir /path/to/年报数据 \\
        --output-dir output/frequency \\
        --sentence-window

    # 组合使用：同时启用公司过滤和句子窗口
    python -m tcfd_extractor.frequency.main \\
        --data-dir /path/to/年报数据 \\
        --output-dir output/frequency \\
        --exclude-company \\
        --sentence-window

    # 保存共现上下文到MD文件
    python -m tcfd_extractor.frequency.main \\
        --data-dir /path/to/年报数据 \\
        --output-dir output/frequency \\
        --save-context
"""

import argparse
import json
import re
from multiprocessing import Pool, cpu_count
from pathlib import Path

import pandas as pd

from tcfd_extractor.frequency.cooccurrence import count_cooccurrence
from tcfd_extractor.frequency.counter import get_word_count
from tcfd_extractor.frequency.parser import parse_filename


def load_bag_a(bag_a_file: str) -> dict:
    """从词袋A_合并版.json加载 {维度: {math_label: [keywords]}}"""
    with open(bag_a_file, encoding="utf-8") as f:
        return json.load(f)


def count_keywords_v2(
    text: str, math_label_keywords: dict, normalize: bool = False
) -> dict:
    """统计所有math_label下keywords的出现次数

    Args:
        text: 待统计文本
        math_label_keywords: {math_label: [keywords列表]}
        normalize: 是否归一化（每万字）

    Returns:
        {math_label: 次数, math_label_每万字: 归一化值, ...}
    """
    word_count = len(text)
    result = {}

    for math_label, keywords in math_label_keywords.items():
        total_count = 0
        for kw in keywords:
            count = len(re.findall(re.escape(kw), text))
            total_count += count
        result[math_label] = total_count
        if normalize and word_count > 0:
            result[f"{math_label}_每万字"] = round(
                total_count / (word_count / 10000), 4
            )

    return result


def load_bag_b(bag_b_file: str) -> list:
    """从words_bag_b.md加载负面词汇"""
    with open(bag_b_file, encoding="utf-8") as f:
        content = f.read()
    # 用顿号分隔
    if "、" in content:
        words = content.split("、")
        return [w.strip() for w in words if w.strip()]
    return []


def process_report(args):
    """处理单个年报文件"""
    filepath, bag_a_data, keywords_b, window, exclude_company, sentence_window, folder_year = args

    parsed = parse_filename(filepath.name)

    with open(filepath, encoding="utf-8", errors="ignore") as f:
        text = f.read()

    word_count = get_word_count(text)
    counts_a = count_keywords_v2(text, bag_a_data, normalize=True)
    cooc = count_cooccurrence(
        text,
        bag_a_data,
        keywords_b,
        window=window,
        normalize=True,
        exclude_company=exclude_company,
        sentence_window=sentence_window,
    )

    result = {
        "filename": filepath.stem,
        "year": folder_year if folder_year is not None else (parsed["year"] if parsed else ""),
        "company_id": parsed["company_id"] if parsed else "",
        "company_name": parsed["company_name"] if parsed else "",
        "report_words_count": word_count,
    }

    for math_label in bag_a_data.keys():
        result[f"{math_label}_每万字"] = counts_a.get(f"{math_label}_每万字", 0)

    sum_a = sum(v for k, v in counts_a.items() if not k.endswith("_每万字"))
    result["sum_class_A"] = sum_a
    result["sum_class_A_每万字"] = (
        round(sum_a / (word_count / 10000), 4) if word_count > 0 else 0
    )

    result["sum_class_AB"] = cooc["sum_class_AB"]
    result["sum_class_AB_每万字"] = cooc.get("sum_class_AB_每万字", 0)
    # context仅在save_context时使用，不放入CSV
    result["_contexts"] = cooc.get("contexts", [])

    return result


def save_cooccurrence_context(
    output_dir: Path, filename: str, company_name: str, year: int, contexts: list
):
    """保存共现上下文到MD文件

    MD格式:
    # {公司名称} - {年份}年度报告

    ## 共现上下文汇总

    ### {math_label}

    **{keyword_a}** + **{keyword_b}** ({count}次共现)
    1. "...{context}..." (位置: {position})
    ...
    """
    md_dir = output_dir / "cooccurrence_context" / str(year)
    md_dir.mkdir(parents=True, exist_ok=True)

    lines = [f"# {company_name} - {year}年度报告\n"]
    lines.append("## 共现上下文汇总\n")

    # 按math_label分组
    by_math_label = {}
    for ctx in contexts:
        ml = ctx.math_label_a
        if ml not in by_math_label:
            by_math_label[ml] = []
        by_math_label[ml].append(ctx)

    # 生成MD内容
    for ml, ctxs in by_math_label.items():
        lines.append(f"### {ml}\n")

        # 按关键词对分组
        by_pair = {}
        for ctx in ctxs:
            key = (ctx.keyword_a, ctx.keyword_b)
            if key not in by_pair:
                by_pair[key] = []
            by_pair[key].append(ctx)

        for (kw_a, kw_b), pair_ctxs in by_pair.items():
            lines.append(f"**{kw_a}** + **{kw_b}** ({len(pair_ctxs)}次共现)")
            for i, ctx in enumerate(pair_ctxs, 1):
                pos = ctx.position
                ctx_text = ctx.window_text.replace("\n", " ")
                # Escape special markdown characters
                for char in ["*", "_", "[", "]", "(", ")", "#", "+", "-", ".", "!"]:
                    ctx_text = ctx_text.replace(char, "\\" + char)
                lines.append(f'{i}. "...{ctx_text}..." (位置: {pos})')
            lines.append("")

        lines.append("---\n")

    # 保存文件
    md_file = md_dir / f"{filename}.md"
    with open(md_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def main():
    parser = argparse.ArgumentParser(description="TCFD词频统计")
    parser.add_argument(
        "--data-dir",
        type=str,
        default="/home/bo/projects/data/A股年报",
        help="年报数据目录",
    )
    parser.add_argument(
        "--output-dir", type=str, default="output/frequency", help="输出目录"
    )
    parser.add_argument(
        "--bag-a-file",
        type=str,
        default="/home/bo/projects/python/frequency_analyzer/doc/word-bags/tcfd-validated/tcfd_validated.json",
        help="词袋A文件路径",
    )
    parser.add_argument(
        "--bag-b-file",
        type=str,
        default="doc/word-bags/auxiliary/words_bag_b.md",
        help="词袋B文件路径",
    )
    parser.add_argument("--workers", type=int, default=None, help="并行进程数")
    parser.add_argument(
        "--window", type=int, default=30, help="共现窗口大小，默认30字（前后各30字）"
    )
    parser.add_argument(
        "--exclude-company",
        action="store_true",
        help="启用公司过滤（A后10字内含'公司'则不统计）",
    )
    parser.add_argument(
        "--sentence-window",
        action="store_true",
        help="启用句子窗口（窗口边界限制为前后句号）",
    )
    parser.add_argument(
        "--save-context", action="store_true", help="保存共现上下文到MD文件"
    )
    args = parser.parse_args()

    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    bag_a_file = args.bag_a_file
    bag_b_file = args.bag_b_file
    output_dir.mkdir(parents=True, exist_ok=True)

    # 加载词袋
    bag_a = load_bag_a(bag_a_file)
    bag_b = load_bag_b(bag_b_file)
    print(f"词袋A: {len(bag_a)} 维度")
    print(f"词袋B: {len(bag_b)} 词")

    # 获取所有维度
    dims = list(bag_a.keys())

    # 收集所有txt文件（支持年份子目录或直接放在data_dir下）
    # 格式: {filepath: folder_year}
    files_with_year = {}
    for year_dir in sorted(data_dir.iterdir()):
        if year_dir.is_dir() and not year_dir.name.startswith("."):
            for f in year_dir.glob("*.txt"):
                files_with_year[f] = int(year_dir.name)
    # 如果没有找到文件，尝试直接在data_dir下查找
    if not files_with_year:
        for f in data_dir.glob("*.txt"):
            files_with_year[f] = None  # 无年份信息

    files = list(files_with_year.keys())

    print(f"共 {len(files)} 个年报文件")

    for dim in dims:
        print(f"\n处理 {dim}...")
        bag_a_data = bag_a[dim]
        print(f"  词袋A: {len(bag_a_data)} math_label")

        # 多进程处理
        worker_count = args.workers or cpu_count()
        tasks = [
            (
                f,
                bag_a_data,
                bag_b,
                args.window,
                args.exclude_company,
                args.sentence_window,
                files_with_year[f],
            )
            for f in files
        ]

        with Pool(worker_count) as pool:
            results = pool.map(process_report, tasks)

        # 过滤空结果
        results = [r for r in results if r is not None]

        # 保存共现上下文到MD
        if args.save_context:
            for result in results:
                contexts = result.pop("_contexts", [])
                if contexts:
                    save_cooccurrence_context(
                        output_dir=output_dir,
                        filename=result["filename"],
                        company_name=result["company_name"],
                        year=result["year"],
                        contexts=contexts,
                    )

        # 输出CSV - 移除_contexts列
        for result in results:
            result.pop("_contexts", None)
        df = pd.DataFrame(results)
        df = df.sort_values(["year", "company_id"])

        output_file = output_dir / f"词频统计_{dim}.csv"
        df.to_csv(output_file, index=False, encoding="utf-8-sig")
        print(f"  输出: {output_file}")

    print("\n完成!")


if __name__ == "__main__":
    main()
