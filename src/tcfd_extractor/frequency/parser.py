import re
from typing import Dict, Optional
from pathlib import Path


def parse_filename(filename: str) -> Optional[Dict]:
    """解析年报文件名，提取公司ID、名称、年份

    支持格式:
    - 000001-平安银行-2023年年度报告.txt
    - 000001_平安银行_2023年年度报告.txt
    - 600125_铁龙物流_600125_铁龙物流_2024年_年度报告.txt
    - 600572_康恩贝_年报全文.txt (无年份，返回None)
    """
    # 移除路径
    name = Path(filename).stem

    def try_parse(parts: list[str]) -> Optional[Dict]:
        if len(parts) < 3:
            return None
        company_id = parts[0]
        # 优先在最后两部分查找年份（更可能是年份位置）
        year_match = None
        year_part_idx = -1
        # 从后往前找，先检查后面部分更可能是年份
        for i in range(len(parts) - 1, 0, -1):
            part = parts[i]
            m = re.match(r'^(\d{4})年?', part)
            if m and 1900 <= int(m.group(1)) <= 2100:
                year_match = m
                year_part_idx = i
                break
        # 如果没找到，往前搜索所有部分
        if year_match is None:
            for i, part in enumerate(parts[1:], 1):
                m = re.match(r'^(\d{4})年?', part)
                if m and 1900 <= int(m.group(1)) <= 2100:
                    year_match = m
                    year_part_idx = i
                    break
        if not year_match:
            return None
        year = int(year_match.group(1))
        # 公司名是中间部分（排除年份部分）
        if year_part_idx == len(parts) - 1:
            # 年份在最后一部分
            company_name = parts[1] if len(parts) == 3 else '_'.join(parts[1:-1])
        else:
            # 年份在中间，公司名取第一个和最后一个之间的部分
            company_name = '_'.join(parts[1:year_part_idx])
        return {
            "company_id": company_id,
            "company_name": company_name,
            "year": year
        }

    # 尝试用-分隔
    parts = name.split('-')
    result = try_parse(parts)
    if result:
        return result

    # 尝试用_分隔
    parts = name.split('_')
    result = try_parse(parts)
    if result:
        return result

    return None
