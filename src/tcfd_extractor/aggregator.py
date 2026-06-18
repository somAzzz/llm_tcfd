import json
from pathlib import Path
from typing import List, Dict, Any

import pandas as pd


class ResultAggregator:
    """聚合并输出结果"""

    def __init__(self, word_bag: Dict[str, List[str]]):
        self.word_bag = word_bag

    def aggregate(self, chunk_results: List[Dict[str, List[str]]]) -> Dict[str, List[str]]:
        """合并多个chunk的提取结果"""
        policy_keywords = []
        market_keywords = []
        tech_keywords = []

        for result in chunk_results:
            policy_keywords.extend(result.get("政策维度", []))
            market_keywords.extend(result.get("市场维度", []))
            tech_keywords.extend(result.get("技术维度", []))

        # 去重
        return {
            "政策维度": list(set(policy_keywords)),
            "市场维度": list(set(market_keywords)),
            "技术维度": list(set(tech_keywords))
        }

    def export_json(self, output_dir: Path, report_name: str, result: Dict[str, Any]):
        """输出JSON文件"""
        output_path = output_dir / f"{report_name}.json"
        output_path.write_text(
            json.dumps(result, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )

    def export_csv(self, output_dir: Path, all_results: List[Dict[str, Any]]):
        """输出CSV汇总文件"""
        rows = []
        for r in all_results:
            rows.append({
                "年报": r.get("report_name", ""),
                "政策维度": ",".join(r.get("政策维度", [])),
                "市场维度": ",".join(r.get("市场维度", [])),
                "技术维度": ",".join(r.get("技术维度", []))
            })

        df = pd.DataFrame(rows)
        df.to_csv(
            output_dir / "tcfd_keywords_summary.csv",
            index=False,
            encoding='utf-8-sig'
        )
