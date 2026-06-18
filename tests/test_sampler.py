import pytest
from pathlib import Path
from tcfd_extractor.sampler import AnnualReportSampler


def test_sampler_init():
    """测试采样器初始化"""
    sampler = AnnualReportSampler("/fake/path", sample_size=100)
    assert sampler.data_dir == Path("/fake/path")
    assert sampler.sample_size == 100


def test_get_all_reports():
    """测试获取所有年报"""
    sampler = AnnualReportSampler("/home/bo/projects/data/A股年报")
    reports = sampler.get_all_reports(years=(2023, 2024))
    assert len(reports) > 0


def test_random_sample():
    """测试随机采样"""
    sampler = AnnualReportSampler("/home/bo/projects/data/A股年报", sample_size=10)
    reports = sampler.random_sample(years=(2023, 2024))
    assert len(reports) == 10
