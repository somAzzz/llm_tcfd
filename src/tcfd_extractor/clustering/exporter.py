import json
from pathlib import Path
from typing import Dict, List
import matplotlib
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
import numpy as np

# 设置中文字体
matplotlib.rcParams['font.sans-serif'] = ['WenQuanYi Zen Hei', 'SimHei', 'DejaVu Sans']
matplotlib.rcParams['axes.unicode_minus'] = False


class ResultExporter:
    """导出聚类结果和可视化"""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    def export(self, clusters: Dict[str, List[dict]], vocabulary: Dict[str, List[str]]):
        """导出所有结果"""
        # 创建目录
        (self.output_dir / "phase5_category_mapping").mkdir(parents=True, exist_ok=True)
        (self.output_dir / "visualization").mkdir(parents=True, exist_ok=True)

        # 保存各维度聚类结果
        for dim, cluster_list in clusters.items():
            # 移除 embeddings 以减小文件体积
            clusters_to_save = []
            for c in cluster_list:
                c_copy = c.copy()
                c_copy.pop("embeddings", None)
                clusters_to_save.append(c_copy)

            output_path = self.output_dir / "phase5_category_mapping" / f"{dim}_clusters.json"
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(clusters_to_save, f, ensure_ascii=False, indent=2)

        # 生成可视化
        self._visualize(clusters, vocabulary)

    def _visualize(self, clusters: Dict[str, List[dict]], vocabulary: Dict[str, List[str]]):
        """生成可视化（散点图）"""
        for dim, cluster_list in clusters.items():
            # 收集所有向量和标签
            all_embeddings = []
            all_labels = []
            all_cluster_ids = []

            for cluster in cluster_list:
                if "embeddings" not in cluster:
                    continue

                embeddings = cluster["embeddings"]
                cluster_id = cluster["cluster_id"]
                math_label = cluster.get("math_label", f"Cluster {cluster_id}")

                for emb in embeddings:
                    all_embeddings.append(emb)
                    all_labels.append(math_label)
                    all_cluster_ids.append(cluster_id)

            if not all_embeddings:
                continue

            # t-SNE 降维到 2D
            embeddings_array = np.array(all_embeddings)
            if len(embeddings_array) < 2:
                continue

            try:
                tsne = TSNE(n_components=2, random_state=42, perplexity=min(5, len(embeddings_array)-1))
                embeddings_2d = tsne.fit_transform(embeddings_array)
            except Exception:
                continue

            # 画散点图
            plt.figure(figsize=(12, 8))
            scatter = plt.scatter(embeddings_2d[:, 0], embeddings_2d[:, 1],
                                 c=all_cluster_ids, cmap='tab10', s=50, alpha=0.6)

            plt.title(f"{dim} 聚类散点图 (t-SNE)")
            plt.colorbar(scatter, label='Cluster ID')
            plt.tight_layout()

            output_path = self.output_dir / "visualization" / f"{dim}聚类散点图.png"
            plt.savefig(output_path, dpi=100)
            plt.close()
