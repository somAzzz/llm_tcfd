from typing import Dict, List
import numpy as np


class SemanticValidator:
    """使用Sentence-BERT验证关键词与维度的相关性"""

    def __init__(self, threshold: float = 0.5, model_name: str = "BAAI/bge-m3"):
        self.threshold = threshold
        self.model_name = model_name
        # 延迟导入，避免启动时加载模型
        self._model = None
        # 基于 words_bag.md 定义锚点词
        self.anchors = {
            # 政策维度 - 27词
            "政策维度": [
                "碳达峰", "碳中和", "能耗双控", "两高项目", "拉闸限电", "有序用电",
                "错峰生产", "限产", "关停取缔", "环保督察", "环保约谈", "强制报废",
                "停产整治", "限期整改", "环境行政处罚", "排污许可", "排放限值",
                "排放标准", "环保罚款", "产能置换", "落后产能", "清洁生产审核", "碳足迹"
            ],
            # 市场维度 - 25词
            "市场维度": [
                "碳排放配额", "碳指标", "碳配额", "排污权", "排放权", "履约成本",
                "履约清缴", "配额缺口", "碳交易", "碳市场", "绿色信贷", "赤道原则",
                "ESG评级", "ESG风险", "碳关税", "绿色贸易壁垒", "绿色供应链",
                "环保税", "环境保护税", "资源税", "合规成本", "治污成本", "绿色贷款", "绿色债券"
            ],
            # 技术维度 - 16词
            "技术维度": [
                "提前报废", "去煤化", "煤改气", "煤改电", "新能源替代", "清洁能源替代",
                "电能替代", "提标改造", "超低排放", "脱硫脱硝", "脱碳", "高排放",
                "高污染", "高耗能", "低碳技术", "节能技术"
            ]
        }

    @property
    def model(self):
        """懒加载模型"""
        if self._model is None:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self.model_name, device='cuda')
        return self._model

    def validate(self, vocabulary: Dict[str, List[str]]) -> Dict[str, List[str]]:
        """过滤低相似度词汇，返回验证后的词袋"""
        validated = {}

        for dim, keywords in vocabulary.items():
            if not keywords:
                validated[dim] = []
                continue

            # 计算每个词与锚点词的相似度
            anchor_text = " ".join(self.anchors.get(dim, []))
            anchor_embedding = self.model.encode([anchor_text])[0]
            keyword_embeddings = self.model.encode(keywords)

            # 计算余弦相似度
            similarities = np.dot(keyword_embeddings, anchor_embedding) / (
                np.linalg.norm(keyword_embeddings, axis=1) * np.linalg.norm(anchor_embedding)
            )

            # 过滤
            valid_keywords = [kw for kw, sim in zip(keywords, similarities) if sim >= self.threshold]
            validated[dim] = valid_keywords

        return validated

    def validate_with_removed(self, vocabulary: Dict[str, List[str]]) -> tuple:
        """过滤低相似度词汇，返回 (验证后的词袋, 被过滤的词袋)"""
        validated = {}
        removed = {}

        for dim, keywords in vocabulary.items():
            if not keywords:
                validated[dim] = []
                removed[dim] = []
                continue

            # 计算每个词与锚点词的相似度
            anchor_text = " ".join(self.anchors.get(dim, []))
            anchor_embedding = self.model.encode([anchor_text])[0]
            keyword_embeddings = self.model.encode(keywords)

            # 计算余弦相似度
            similarities = np.dot(keyword_embeddings, anchor_embedding) / (
                np.linalg.norm(keyword_embeddings, axis=1) * np.linalg.norm(anchor_embedding)
            )

            # 分类
            valid_keywords = []
            removed_keywords = []
            for kw, sim in zip(keywords, similarities):
                if sim >= self.threshold:
                    valid_keywords.append(kw)
                else:
                    removed_keywords.append(kw)

            validated[dim] = valid_keywords
            removed[dim] = removed_keywords

        return validated, removed
