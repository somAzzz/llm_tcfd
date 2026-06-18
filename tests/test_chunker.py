# tests/test_chunker.py
from tcfd_extractor.chunker import SmartChunker


def test_chunker_init():
    """测试分块器初始化"""
    chunker = SmartChunker(min_chunk_size=200, max_chunk_size=2000)
    assert chunker.min_chunk_size == 200
    assert chunker.max_chunk_size == 2000


def test_chunk_by_paragraph():
    """测试按段落分块"""
    chunker = SmartChunker(min_chunk_size=50, max_chunk_size=500)
    text = "第一段内容。\n\n第二段内容。\n\n第三段内容超过目标大小限制，" * 50
    chunks = chunker.chunk_by_paragraph(text, target_size=300)
    assert len(chunks) > 0


def test_split_large_paragraph():
    """测试拆分大段落"""
    chunker = SmartChunker()
    text = "这是一个很长的段落。" * 100
    chunks = chunker._split_large_paragraph(text)
    assert len(chunks) > 1
