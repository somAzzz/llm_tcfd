from typing import Dict, List, Tuple
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
import numpy as np


class KeywordClustering:
    """使用K-Means对每个维度的关键词进行聚类"""

    def __init__(self, k_range: Tuple[int, int] = (3, 30), model_name: str = "BAAI/bge-m3"):
        self.k_range = k_range
        self.model_name = model_name
        self.model = SentenceTransformer(model_name, device='cuda')

    def cluster(self, vocabulary: Dict[str, List[str]], save_embeddings: bool = True) -> Dict[str, List[dict]]:
        """对每个维度分别进行K-Means聚类

        Args:
            vocabulary: 关键词字典
            save_embeddings: 是否保存向量（用于可视化）
        """
        results = {}

        for dim, keywords in vocabulary.items():
            if not keywords or len(keywords) < 3:
                results[dim] = [{"cluster_id": 0, "keywords": keywords, "size": len(keywords)}]
                continue

            # 编码
            embeddings = self.model.encode(keywords)

            # 找最优K
            best_k, best_score = self._find_optimal_k(embeddings)

            # 聚类
            kmeans = KMeans(n_clusters=best_k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(embeddings)

            # 整理结果
            clusters = []
            for i in range(best_k):
                cluster_keywords = [kw for kw, label in zip(keywords, labels) if label == i]
                if cluster_keywords:
                    # 找质心最近词
                    centroid = kmeans.cluster_centers_[i]
                    distances = np.linalg.norm(embeddings[labels == i] - centroid, axis=1)
                    math_label = cluster_keywords[np.argmin(distances)]

                    cluster_data = {
                        "cluster_id": i,
                        "keywords": cluster_keywords,
                        "size": len(cluster_keywords),
                        "math_label": math_label
                    }

                    # 保存向量用于可视化
                    if save_embeddings:
                        # 保存该聚类中每个词的向量
                        keyword_indices = [idx for idx, label in enumerate(labels) if label == i]
                        cluster_data["embeddings"] = [embeddings[idx].tolist() for idx in keyword_indices]

                    clusters.append(cluster_data)

            results[dim] = clusters

        return results

    def _find_optimal_k(self, embeddings: np.ndarray) -> Tuple[int, float]:
        """使用轮廓系数找最优K"""
        best_k = self.k_range[0]
        best_score = -1

        for k in range(self.k_range[0], min(self.k_range[1], len(embeddings) - 1)):
            kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = kmeans.fit_predict(embeddings)

            if len(set(labels)) > 1:
                score = silhouette_score(embeddings, labels)
                if score > best_score:
                    best_score = score
                    best_k = k

        return best_k, best_score
