import pytest
from pathlib import Path
from tcfd_extractor.clustering.ingestion import VocabularyIngestion


def test_ingest():
    """测试关键词摄入"""
    ingestion = VocabularyIngestion()
    result = ingestion.ingest(Path("output/tcfd_keywords_test"))
    assert "政策维度" in result
    assert "市场维度" in result
    assert "技术维度" in result
