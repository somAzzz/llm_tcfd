"""年报正文提取模块 - 删除财务报告等附件部分"""

import re
import argparse
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, as_completed


@dataclass
class CleanResult:
    """清洗结果"""
    file: str
    original_chars: int
    kept_chars: int
    keep_ratio: float
    is_problem: bool
    status: str  # "ok" | "problem" | "not_found" | "error"
    error_msg: str = ""


class AnnualReportCleaner:
    """年报正文提取器"""

    # 财务章节匹配模式（优先匹配正文章节，排除目录引用）
    # 注意：只用中文数字匹配章节，不用阿拉伯数字（阿拉伯数字多用于小节内部编号）
    FINANCIAL_PATTERNS = [
        # 通用模式：中文数字+、+财务报告/财务报表/财务会计报告
        re.compile(r'^[一二三四五六七八九十百零第一]+、\s*财务会计报告', re.MULTILINE),
        re.compile(r'^[一二三四五六七八九十百零第一]+、\s*财务报表', re.MULTILINE),
        re.compile(r'^[一二三四五六七八九十百零第一]+、\s*财务报告', re.MULTILINE),
        # 第X章格式（无顿号，如"第十章 财务报告"）
        re.compile(r'^第[一二三四五六七八九十百零第一]+章\s*财务[审计会计]?报告', re.MULTILINE),
        re.compile(r'^第[一二三四五六七八九十百零第一]+章\s*财务报表', re.MULTILINE),
        # 第X节格式（多种变体）
        re.compile(r'^第[一二三四五六七八九十百零第一]+节\s*财务[审计]?[会计]?报告', re.MULTILINE),
        re.compile(r'^第[一二三四五六七八九十百零第一]+节\s*财务报表', re.MULTILINE),
        # (见附件)格式
        re.compile(r'财务会计报告\s*\(见附件\)', re.MULTILINE),
    ]

    @classmethod
    def _is_likely_toc_entry(cls, content: str, match_pos: int, matched_text: str) -> bool:
        """判断是否是目录条目"""
        # 目录中的点号字符（用于过滤目录条目）
        TOC_DOT_CHARS = ' \t.·…－-—'

        after = content[match_pos + len(matched_text):match_pos + len(matched_text) + 20]

        # 如果紧跟的是空白或点号字符，说明是目录
        if after and any(after[0] == c for c in TOC_DOT_CHARS):
            return True

        # 如果后面紧跟换行，检查是否是连续章节列表（目录特征）
        if after and after[0] in '\n\r':
            # 查找后续的章节标题模式
            next_section_pattern = re.compile(
                r'^[一二三四五六七八九十百零第一]+、\s*[\u4e00-\u9fff]',
                re.MULTILINE
            )
            search_start = match_pos + len(matched_text)
            search_end = min(search_start + 200, len(content))
            next_match = next_section_pattern.search(content[search_start:search_end])

            # 如果在短距离内找到另一个章节标题，说明是目录列表
            if next_match and next_match.start() < 100:
                return True

        return False

    @classmethod
    def _find_financial_section(cls, content: str) -> Optional[dict]:
        """查找财务章节位置，返回位置信息或None"""
        matches = []
        for pattern in cls.FINANCIAL_PATTERNS:
            for match in pattern.finditer(content):
                # 跳过目录中的条目
                if cls._is_likely_toc_entry(content, match.start(), match.group()):
                    continue
                matches.append({
                    "position": match.start(),
                    "matched": match.group(),
                    "pattern": pattern.pattern
                })

        if not matches:
            return None

        # 返回位置最靠前的有效匹配
        return min(matches, key=lambda x: x["position"])

    @classmethod
    def _trim_after_section(cls, content: str, position: int) -> str:
        """删除位置之后的内容"""
        return content[:position]

    @classmethod
    def _calc_keep_ratio(cls, original: str, trimmed: str) -> float:
        """计算保留字数比例"""
        return len(trimmed) / len(original) if original else 0

    @classmethod
    def _is_problem_file(cls, original: str, trimmed: str, threshold: float = 0.5) -> bool:
        """判断是否为问题文件（保留字数少于50%）"""
        return cls._calc_keep_ratio(original, trimmed) < threshold

    @classmethod
    def _read_file_with_fallback(cls, filepath: Path) -> str:
        """尝试多种编码读取文件"""
        for encoding in ['utf-8', 'gbk', 'gb2312', 'gb18030']:
            try:
                return filepath.read_text(encoding=encoding)
            except UnicodeDecodeError:
                continue
        raise ValueError("无法解码文件")

    @classmethod
    def clean_single(cls, filepath: Path) -> CleanResult:
        """清洗单个年报文件"""
        try:
            content = cls._read_file_with_fallback(filepath)
            original_chars = len(content)

            # 查找财务章节
            section_info = cls._find_financial_section(content)
            if section_info is None:
                return CleanResult(
                    file=filepath.name,
                    original_chars=original_chars,
                    kept_chars=original_chars,
                    keep_ratio=1.0,
                    is_problem=False,
                    status="not_found"
                )

            # 截断
            trimmed = cls._trim_after_section(content, section_info["position"])
            kept_chars = len(trimmed)
            keep_ratio = cls._calc_keep_ratio(content, trimmed)
            is_problem = cls._is_problem_file(content, trimmed)

            return CleanResult(
                file=filepath.name,
                original_chars=original_chars,
                kept_chars=kept_chars,
                keep_ratio=keep_ratio,
                is_problem=is_problem,
                status="problem" if is_problem else "ok"
            )

        except Exception as e:
            return CleanResult(
                file=filepath.name,
                original_chars=0,
                kept_chars=0,
                keep_ratio=0,
                is_problem=True,
                status="error",
                error_msg=str(e)
            )

    @classmethod
    def process_directory(cls, input_dir: Path, output_dir: Path, max_workers: int = 8) -> dict:
        """批量处理目录（多线程）"""
        output_dir.mkdir(parents=True, exist_ok=True)

        # 收集所有文件
        files = list(input_dir.rglob("*.txt"))

        def process_file(year_file: Path) -> tuple:
            """处理单个文件，返回(result, year_file)"""
            result = cls.clean_single(year_file)
            return result, year_file

        results = []

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(process_file, f): f for f in files}

            for future in as_completed(futures):
                result, year_file = future.result()
                results.append(result)

                # 写入输出
                if result.status in ("ok", "problem", "not_found"):
                    relative = year_file.relative_to(input_dir)
                    output_file = output_dir / relative

                    content = cls._read_file_with_fallback(year_file)

                    if result.status == "ok":
                        section_info = cls._find_financial_section(content)
                        if section_info:
                            content = content[:section_info["position"]]

                    output_file.parent.mkdir(parents=True, exist_ok=True)
                    output_file.write_text(content, encoding='utf-8')

        return cls._summarize(results)

    @classmethod
    def _summarize(cls, results: list) -> dict:
        """生成统计摘要"""
        total = len(results)
        ok = sum(1 for r in results if r.status == "ok")
        problem = sum(1 for r in results if r.status == "problem")
        not_found = sum(1 for r in results if r.status == "not_found")
        errors = sum(1 for r in results if r.status == "error")

        avg_ratio = sum(r.keep_ratio for r in results) / total if total else 0

        return {
            "total": total,
            "ok": ok,
            "problem": problem,
            "not_found": not_found,
            "errors": errors,
            "avg_keep_ratio": round(avg_ratio, 3)
        }


def main():
    parser = argparse.ArgumentParser(description="年报正文提取工具 - 删除财务报告附件")
    parser.add_argument("--input_dir", required=True, help="原始年报目录")
    parser.add_argument("--output_dir", required=True, help="输出目录")

    args = parser.parse_args()

    input_path = Path(args.input_dir)
    output_path = Path(args.output_dir)

    summary = AnnualReportCleaner.process_directory(input_path, output_path)

    print(f"处理完成:")
    print(f"  总文件: {summary['total']}")
    print(f"  正常: {summary['ok']}")
    print(f"  问题(字数<50%): {summary['problem']}")
    print(f"  未找到财务章节: {summary['not_found']}")
    print(f"  错误: {summary['errors']}")
    print(f"  平均保留比例: {summary['avg_keep_ratio']*100:.1f}%")


if __name__ == "__main__":
    main()