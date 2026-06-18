"""TCFD关键词提取系统主入口"""

import time
from pathlib import Path

from tcfd_extractor.sampler import AnnualReportSampler
from tcfd_extractor.chunker import SmartChunker
from tcfd_extractor.extractor import (
    load_word_bag,
    read_text_with_fallback,
    check_sglang_health,
    TCFDKeywordExtractor
)
from tcfd_extractor.executor import ControlledExecutor
from tcfd_extractor.evaluator import ChunkEvaluator
from tcfd_extractor.aggregator import ResultAggregator


def extract_single_chunk(chunk: str, word_bag: dict, extractor: TCFDKeywordExtractor) -> dict:
    """提取单个chunk的关键词"""
    try:
        return extractor.extract(chunk, word_bag)
    except Exception as e:
        print(f"提取失败: {e}")
        return {"政策维度": [], "市场维度": [], "技术维度": []}


def main():
    """主函数"""
    # 1. 配置参数
    DATA_DIR = "/home/bo/projects/data/A股年报"
    OUTPUT_DIR = Path("./output/tcfd_keywords")
    WORD_BAG_PATH = "/home/bo/projects/python/frequency_analyzer/doc/word-bags/raw/words_bag.md"
    SAMPLE_SIZE = 1000
    MAX_WORKERS = 8
    SGLANG_BASE_URL = "http://127.0.0.1:30000/v1"

    # 确保输出目录存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 2. 验证SGLang服务
    print("检查SGLang服务状态...")
    if not check_sglang_health(SGLANG_BASE_URL):
        raise RuntimeError("SGLang服务不可用，请检查Docker容器是否运行")
    print("SGLang服务正常")

    # 3. 加载词袋
    word_bag = load_word_bag(WORD_BAG_PATH)
    print(f"词袋加载完成: 政策维度{len(word_bag['政策维度'])}词, "
          f"市场维度{len(word_bag['市场维度'])}词, "
          f"技术维度{len(word_bag['技术维度'])}词")

    # 4. 采样
    print(f"从 {DATA_DIR} 采样 {SAMPLE_SIZE} 份年报...")
    sampler = AnnualReportSampler(DATA_DIR, SAMPLE_SIZE)
    reports = sampler.random_sample(years=(2000, 2024))
    print(f"采样完成，共 {len(reports)} 份年报")

    # 5. Chunk长度寻优（小样本）
    print("开始Chunk长度寻优...")
    evaluator = ChunkEvaluator(word_bag)
    eval_result = evaluator.find_optimal_chunk_size(reports[:50])
    optimal_chunk_size = eval_result["optimal_size"]
    print(f"最优chunk大小: {optimal_chunk_size}")
    print(f"各长度F1分数: {eval_result['all_results']}")

    # 6. 全量提取
    print(f"开始全量提取，共 {len(reports)} 份年报...")
    chunker = SmartChunker(min_chunk_size=200, max_chunk_size=2000)
    extractor = TCFDKeywordExtractor(base_url=SGLANG_BASE_URL)
    executor = ControlledExecutor(max_workers=MAX_WORKERS)
    aggregator = ResultAggregator(word_bag)

    all_results = []

    for i, report in enumerate(reports):
        print(f"处理第 {i+1}/{len(reports)} 份: {report.name}")

        # 使用fallback读取文本
        try:
            text = read_text_with_fallback(report)
        except Exception as e:
            print(f"读取文件失败: {report.name}, {e}")
            continue

        # 分块
        chunks = chunker.chunk_by_paragraph(text, optimal_chunk_size)

        # 并行提取
        file_key = report.stem
        for chunk in chunks:
            executor.submit(
                extract_single_chunk,
                file_key,
                chunk,
                word_bag,
                extractor
            )

        # 等待完成
        executor.wait_for_file_completion(file_key, len(chunks))

        # 获取结果
        chunk_results = executor.get_file_results(file_key)
        executor.clear_file_results(file_key)

        # 聚合并保存
        final_result = aggregator.aggregate(chunk_results)
        final_result["report_name"] = report.name
        all_results.append(final_result)

        # 输出JSON
        aggregator.export_json(OUTPUT_DIR, report.stem, final_result)

    # 7. 输出CSV汇总
    aggregator.export_csv(OUTPUT_DIR, all_results)
    print(f"完成！结果已保存到 {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
