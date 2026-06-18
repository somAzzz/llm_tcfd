"""简单测试版本 - 用于快速验证系统功能"""

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
from tcfd_extractor.aggregator import ResultAggregator


def main():
    """简单测试主函数"""
    # 配置参数
    DATA_DIR = "/home/bo/projects/data/A股年报"
    OUTPUT_DIR = Path("./output/tcfd_keywords_test")
    WORD_BAG_PATH = "/home/bo/projects/python/frequency_analyzer/doc/word-bags/raw/words_bag.md"
    SAMPLE_SIZE = 5  # 只处理5份年报
    CHUNK_SIZE = 1000  # 固定chunk大小，跳过寻优
    SGLANG_BASE_URL = "http://127.0.0.1:30000/v1"

    # 确保输出目录存在
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # 1. 验证SGLang服务
    print("检查SGLang服务状态...")
    if not check_sglang_health(SGLANG_BASE_URL):
        print("错误: SGLang服务不可用!")
        return
    print("SGLang服务正常")

    # 2. 加载词袋
    print("\n加载词袋...")
    word_bag = load_word_bag(WORD_BAG_PATH)
    print(f"  政策维度: {len(word_bag['政策维度'])}词")
    print(f"  市场维度: {len(word_bag['市场维度'])}词")
    print(f"  技术维度: {len(word_bag['技术维度'])}词")

    # 3. 采样 (只取5份)
    print(f"\n采样 {SAMPLE_SIZE} 份年报...")
    sampler = AnnualReportSampler(DATA_DIR, SAMPLE_SIZE)
    reports = sampler.random_sample(years=(2023, 2024))
    print(f"采样完成: {len(reports)} 份")

    # 4. 初始化组件
    print("\n初始化组件...")
    chunker = SmartChunker(min_chunk_size=200, max_chunk_size=2000)
    extractor = TCFDKeywordExtractor(base_url=SGLANG_BASE_URL)
    aggregator = ResultAggregator(word_bag)

    # 5. 处理每份年报
    print(f"\n开始处理...")
    all_results = []

    for i, report in enumerate(reports):
        print(f"\n[{i+1}/{len(reports)}] 处理: {report.name}")

        try:
            # 读取文本
            text = read_text_with_fallback(report)
            print(f"  文本长度: {len(text)} 字符")

            # 分块
            chunks = chunker.chunk_by_paragraph(text, target_size=CHUNK_SIZE)
            print(f"  分块数: {len(chunks)}")

            # 提取关键词
            chunk_results = []
            for j, chunk in enumerate(chunks):
                print(f"  提取chunk {j+1}/{len(chunks)}...", end=" ")
                result = extractor.extract(chunk, word_bag)
                chunk_results.append(result)
                print(f"OK")

            # 聚合结果
            final_result = aggregator.aggregate(chunk_results)
            final_result["report_name"] = report.name

            # 统计
            total_kw = len(final_result.get("政策维度", [])) + \
                      len(final_result.get("市场维度", [])) + \
                      len(final_result.get("技术维度", []))
            print(f"  提取关键词: {total_kw}个")
            print(f"    政策维度: {final_result.get('政策维度', [])}")
            print(f"    市场维度: {final_result.get('市场维度', [])}")
            print(f"    技术维度: {final_result.get('技术维度', [])}")

            all_results.append(final_result)

            # 保存JSON
            aggregator.export_json(OUTPUT_DIR, report.stem, final_result)

        except Exception as e:
            print(f"  错误: {e}")
            continue

    # 6. 保存CSV汇总
    if all_results:
        aggregator.export_csv(OUTPUT_DIR, all_results)
        print(f"\n完成! 结果已保存到 {OUTPUT_DIR}")
        print(f"  JSON文件: {len(all_results)}个")
        print(f"  CSV汇总: tcfd_keywords_summary.csv")
    else:
        print("\n没有处理成功的结果")


if __name__ == "__main__":
    main()
