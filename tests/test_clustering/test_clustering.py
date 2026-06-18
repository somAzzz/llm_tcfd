import pytest
from tcfd_extractor.clustering.clustering import KeywordClustering


def test_clustering_init():
    """测试聚类器初始化"""
    clusterer = KeywordClustering(k_range=(5, 10))
    assert clusterer.k_range == (5, 10)
