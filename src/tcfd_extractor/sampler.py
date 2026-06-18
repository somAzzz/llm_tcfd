import random
from pathlib import Path
from typing import List, Tuple


class AnnualReportSampler:
    """从A股年报目录中随机抽取样本"""

    def __init__(self, data_dir: str, sample_size: int = 1000):
        self.data_dir = Path(data_dir)
        self.sample_size = sample_size

    def get_all_reports(self, years: Tuple[int, int] = (2000, 2024)) -> List[Path]:
        """获取指定年份范围内的所有年报文件路径"""
        reports = []
        for year in range(years[0], years[1] + 1):
            year_dir = self.data_dir / str(year)
            if year_dir.exists():
                reports.extend(year_dir.glob("*.txt"))
        return reports

    def random_sample(self, years: Tuple[int, int] = (2000, 2024)) -> List[Path]:
        """随机抽取指定数量的年报"""
        all_reports = self.get_all_reports(years)
        if len(all_reports) <= self.sample_size:
            return all_reports
        return random.sample(all_reports, self.sample_size)
