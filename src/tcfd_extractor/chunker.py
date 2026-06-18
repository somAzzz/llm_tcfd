# src/tcfd_extractor/chunker.py
import re


class SmartChunker:
    """按语义边界智能切分文本"""

    def __init__(self, min_chunk_size: int = 200, max_chunk_size: int = 2000):
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size

    def chunk_by_paragraph(self, text: str, target_size: int = 1000) -> list[str]:
        """按段落切分，合并小段落，拆分大段落"""
        # 按换行符分割段落
        paragraphs = re.split(r"\n+", text)
        chunks = []
        current_chunk = []
        current_size = 0

        for para in paragraphs:
            para = para.strip()
            if not para:
                continue
            para_size = len(para)

            # 如果单个段落超过目标大小，按句子拆分
            if para_size > self.max_chunk_size:
                if current_chunk:
                    chunks.append("\n".join(current_chunk))
                    current_chunk = []
                    current_size = 0
                chunks.extend(self._split_large_paragraph(para))
                continue

            # 合并小段落
            if (
                current_size + para_size > target_size
                and current_size >= self.min_chunk_size
            ):
                chunks.append("\n".join(current_chunk))
                current_chunk = [para]
                current_size = para_size
            else:
                current_chunk.append(para)
                current_size += para_size

        # 处理最后一个chunk
        if current_chunk:
            chunks.append("\n".join(current_chunk))

        return [c for c in chunks if c.strip()]

    def _split_large_paragraph(self, text: str) -> list[str]:
        """按句子拆分大段落"""
        # 按句子结束符分割
        sentences = re.split(r"([。！？])", text)
        chunks = []
        current = []
        size = 0

        for i in range(0, len(sentences) - 1, 2):
            sent = sentences[i].strip()
            if not sent:
                continue

            # 保留句子结束符
            sent_with_punct = sent
            if i + 1 < len(sentences):
                sent_with_punct += sentences[i + 1]

            # 如果当前chunk加上这句话会超过最大限制，则创建新chunk
            if size + len(sent_with_punct) > self.max_chunk_size:
                if current:
                    chunks.append("".join(current))
                    current = []
                    size = 0
            # 如果当前chunk已经满足最小大小要求，也创建新chunk
            elif size >= self.min_chunk_size:
                chunks.append("".join(current))
                current = []
                size = 0

            current.append(sent_with_punct)
            size += len(sent_with_punct)

        # 处理最后一个chunk
        if current:
            chunks.append("".join(current))

        return [c for c in chunks if c.strip()]
