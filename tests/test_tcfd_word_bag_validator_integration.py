# tests/test_tcfd_word_bag_validator_integration.py
import json
import pytest
from pathlib import Path


@pytest.fixture
def sample_word_bank(tmp_path):
    """创建测试用词袋文件。"""
    word_bank = {
        "技术": {
            "电动": ["变频电机", "超级电容", "新能源汽车", "智能手机"],
            "其他": ["碳交易", "绿色偏好"]
        },
        "市场": {
            "需求": ["绿电溢价"]
        }
    }

    path = tmp_path / "test_word_bank.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(word_bank, f, ensure_ascii=False, indent=2)

    return path


def test_end_to_end_cli(sample_word_bank, tmp_path):
    """测试完整CLI流程。"""
    import subprocess

    output_path = tmp_path / "output.json"

    result = subprocess.run(
        [
            "uv", "run", "python", "-m", "tcfd_extractor.tcfd_word_bag_validator",
            "--input", str(sample_word_bank),
            "--output", str(output_path),
            "--batch-size", "2",
        ],
        capture_output=True,
        text=True,
        timeout=120
    )

    print("STDOUT:", result.stdout)
    print("STDERR:", result.stderr)

    # Skip if LLM is not available (API returned 404)
    if "Error code: 404" in result.stdout or "Not Found" in result.stdout:
        pytest.skip("LLM API not available (got 404)")

    # Check output file exists
    assert output_path.exists(), f"Output file not created. stderr: {result.stderr}"

    # Check output is valid JSON with same structure
    with open(output_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    assert "技术" in data
    assert "市场" in data
    assert "电动" in data["技术"]
    assert "需求" in data["市场"]

    # Verify some keywords were kept
    all_keywords = []
    for cat in data.values():
        if isinstance(cat, dict):
            for subcat in cat.values():
                if isinstance(subcat, list):
                    all_keywords.extend(subcat)

    assert len(all_keywords) > 0, "No keywords were kept"
    # 智能手机 should be filtered out
    assert "智能手机" not in all_keywords