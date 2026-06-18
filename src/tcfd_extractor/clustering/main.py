"""TCFD关键词聚类CLI"""

import argparse
import json
from pathlib import Path

from tcfd_extractor.clustering.clustering import KeywordClustering
from tcfd_extractor.clustering.exporter import ResultExporter
from tcfd_extractor.clustering.ingestion import VocabularyIngestion
from tcfd_extractor.clustering.label_generator import LabelGenerator
from tcfd_extractor.clustering.validator import SemanticValidator


def main():
    parser = argparse.ArgumentParser(description="TCFD关键词聚类")
    parser.add_argument("--input", type=str, required=True, help="输入目录")
    parser.add_argument("--output", type=str, default=None, help="输出目录")
    parser.add_argument("--k-range", type=str, default="20,40", help="K范围")
    parser.add_argument("--use-phase2", action="store_true", help="启用语义验证")
    parser.add_argument(
        "--phase2-threshold", type=float, default=0.5, help="语义验证阈值"
    )
    parser.add_argument("--use-llm-labels", action="store_true", help="生成LLM标签")
    parser.add_argument("--model", type=str, default="BAAI/bge-m3", help="向量化模型")

    args = parser.parse_args()

    input_dir = Path(args.input)
    output_dir = Path(args.output) if args.output else input_dir

    print(f"输入目录: {input_dir}")
    print(f"输出目录: {output_dir}")
    print(f"向量化模型: {args.model}")

    # Phase 1: 数据摄入
    print("\n[Phase 1] 数据摄入...")
    ingestion = VocabularyIngestion()
    vocabulary = ingestion.ingest(input_dir)
    for dim, kws in vocabulary.items():
        print(f"  {dim}: {len(kws)} 词")

    # 保存Phase1结果
    (output_dir / "phase1_ingestion").mkdir(parents=True, exist_ok=True)
    ingestion.save(
        vocabulary, output_dir / "phase1_ingestion" / "merged_vocabulary.json"
    )

    # Phase 2: 语义验证 (可选)
    if args.use_phase2:
        print(f"\n[Phase 2] 语义验证 (阈值={args.phase2_threshold})...")
        validator = SemanticValidator(
            threshold=args.phase2_threshold, model_name=args.model
        )
        vocabulary, removed = validator.validate_with_removed(vocabulary)
        for dim, kws in vocabulary.items():
            print(f"  {dim}: {len(kws)} 词")

        # 保存Phase2结果 - 验证后的词
        (output_dir / "phase2_validation").mkdir(parents=True, exist_ok=True)
        with open(
            output_dir / "phase2_validation" / "validation_result.json",
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(vocabulary, f, ensure_ascii=False, indent=2)

        # 保存被过滤的词
        with open(
            output_dir / "phase2_validation" / "removed_keywords.json",
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(removed, f, ensure_ascii=False, indent=2)

    # Phase 3: 聚类
    print("\n[Phase 3] K-Means聚类...")
    k_range = tuple(map(int, args.k_range.split(",")))
    clusterer = KeywordClustering(k_range=k_range, model_name=args.model)
    clusters = clusterer.cluster(vocabulary)
    for dim, cluster_list in clusters.items():
        print(f"  {dim}: {len(cluster_list)} clusters")

    # 保存Phase3结果
    (output_dir / "phase3_clustering").mkdir(parents=True, exist_ok=True)
    with open(output_dir / "phase3_clustering" / "clustering_result.json", "w") as f:
        json.dump(clusters, f, ensure_ascii=False, indent=2)

    # Phase 4: 标签生成
    if args.use_llm_labels:
        print("\n[Phase 4] LLM标签生成...")
        from openai import OpenAI

        llm_client = OpenAI(base_url="http://127.0.0.1:30000/v1", api_key="sk-local")
        label_gen = LabelGenerator(use_llm=True, llm_client=llm_client)
        clusters = label_gen.generate_labels(clusters)

    # Phase 5: 输出
    print("\n[Phase 5] 导出结果...")
    exporter = ResultExporter(output_dir)
    exporter.export(clusters, vocabulary)

    print("\n完成!")
    print(f"结果保存在: {output_dir}")


if __name__ == "__main__":
    main()
