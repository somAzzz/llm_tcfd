from pathlib import Path
from typing import List, Dict, Any

from .chunker import SmartChunker
from .extractor import TCFDKeywordExtractor, load_word_bag


class ChunkEvaluator:
    """评估不同chunk长度的效果"""

    def __init__(self, word_bag: Dict[str, List[str]]):
        self.word_bag = word_bag

    def calculate_f1(self, extracted: List[str]) -> Dict[str, Any]:
        """计算综合F1分数"""
        policy_words = set(self.word_bag.get("政策维度", []))
        market_words = set(self.word_bag.get("市场维度", []))
        tech_words = set(self.word_bag.get("技术维度", []))
        all_bag_words = policy_words | market_words | tech_words

        extracted_set = set(extracted)

        # 精确率
        true_positives = len(extracted_set & all_bag_words)
        precision = true_positives / len(extracted_set) if extracted_set else 0

        # 召回率（简化版：相对于词袋总数）
        recall = true_positives / len(all_bag_words) if all_bag_words else 0

        # F1
        f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

        return {
            "precision": precision,
            "recall": recall,
            "f1": f1,
            "extracted_count": len(extracted_set),
            "matched_count": true_positives
        }

    def find_optimal_chunk_size(self, sample_reports: List[Path],
                                 chunk_sizes: List[int] = [512, 768, 1024, 1536, 2048]) -> Dict[str, Any]:
        """寻找最优chunk大小"""
        results = {}
        chunker = SmartChunker()
        extractor = TCFDKeywordExtractor()

        for size in chunk_sizes:
            all_keywords = []
            for report in sample_reports[:10]:  # 用10份年报测试
                try:
                    from .extractor import read_text_with_fallback
                    text = read_text_with_fallback(report)
                except:
                    continue

                chunks = chunker.chunk_by_paragraph(text, target_size=size)

                for chunk in chunks:
                    try:
                        result = extractor.extract(chunk, self.word_bag)
                        all_keywords.extend(result.get("政策维度", []))
                        all_keywords.extend(result.get("市场维度", []))
                        all_keywords.extend(result.get("技术维度", []))
                    except:
                        continue

            results[size] = self.calculate_f1(all_keywords)

        # 选取F1最高的chunk大小
        optimal = max(results.items(), key=lambda x: x[1]['f1'])
        return {"optimal_size": optimal[0], "all_results": results}
