from typing import Dict, List


class LabelGenerator:
    """生成聚类标签"""

    def __init__(self, use_llm: bool = False, llm_client=None):
        self.use_llm = use_llm
        self.llm_client = llm_client

    def generate_labels(self, clusters: Dict[str, List[dict]]) -> Dict[str, List[dict]]:
        """为每个聚类生成标签"""
        for dim, cluster_list in clusters.items():
            for cluster in cluster_list:
                # 已有的 math_label 作为 fallback
                if not cluster.get("llm_label"):
                    cluster["llm_label"] = cluster.get("math_label", "")

                # 如果需要LLM标签
                if self.use_llm and self.llm_client:
                    cluster["llm_label"] = self._generate_llm_label(cluster["keywords"])

        return clusters

    def _generate_llm_label(self, keywords: List[str]) -> str:
        """调用LLM生成标签"""
        # 简化实现
        prompt = f"为以下关键词生成一个简洁的中文标签(1-4字): {','.join(keywords[:10])}"
        try:
            response = self.llm_client.chat.completions.create(
                model="Qwen/Qwen3.5-35B-A3B",
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=10
            )
            return response.choices[0].message.content.strip()
        except:
            return keywords[0] if keywords else ""
