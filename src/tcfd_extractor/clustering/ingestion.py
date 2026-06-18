import csv
import json
from pathlib import Path
from typing import Dict, List


class VocabularyIngestion:
    """合并所有年报的关键词，按维度分类"""

    def ingest(self, input_dir: Path) -> Dict[str, List[str]]:
        """读取CSV文件，合并关键词"""
        vocabulary = {
            "政策维度": set(),
            "市场维度": set(),
            "技术维度": set()
        }

        # 查找CSV文件
        csv_file = None
        for f in input_dir.glob("*.csv"):
            csv_file = f
            break

        if csv_file is None:
            # 回退到原来的JSON方式
            return self._ingest_json(input_dir)

        # 读取CSV
        with open(csv_file, 'r', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                for dim in ["政策维度", "市场维度", "技术维度"]:
                    keywords_str = row.get(dim, "")
                    if keywords_str:
                        keywords = [k.strip() for k in keywords_str.split(',') if k.strip()]
                        vocabulary[dim].update(keywords)

        # 转换为列表
        return {k: list(v) for k, v in vocabulary.items()}

    def _ingest_json(self, input_dir: Path) -> Dict[str, List[str]]:
        """读取所有JSON文件，合并关键词（回退方案）"""
        vocabulary = {
            "政策维度": set(),
            "市场维度": set(),
            "技术维度": set()
        }

        for json_file in input_dir.glob("*.json"):
            if json_file.name == "tcfd_keywords_summary.csv":
                continue

            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

            for dim in ["政策维度", "市场维度", "技术维度"]:
                keywords = data.get(dim, [])
                vocabulary[dim].update(keywords)

        return {k: list(v) for k, v in vocabulary.items()}

    def save(self, vocabulary: Dict[str, List[str]], output_path: Path):
        """保存到JSON文件"""
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(vocabulary, f, ensure_ascii=False, indent=2)
