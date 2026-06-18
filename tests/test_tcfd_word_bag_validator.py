# tests/test_tcfd_word_bag_validator.py
import json
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from tcfd_extractor.tcfd_word_bag_validator import (
    parse_args,
    load_word_bag,
    TCFDValidationResult,
    validate_batch,
    process_word_bag,
    save_results,
)


def test_parse_args_defaults():
    """Test default argument values."""
    args = parse_args([
        "--input", "input.json",
        "--output", "output.json"
    ])
    assert args.input == "input.json"
    assert args.output == "output.json"
    assert args.batch_size == 20
    assert args.temperature == 0.1
    assert args.api_url == "http://0.0.0.0:30000/v1"
    assert args.model == "Qwen/Qwen3.5-35B-A3B"


def test_parse_args_custom():
    """Test custom argument values."""
    args = parse_args([
        "--input", "in.json",
        "--output", "out.json",
        "--batch-size", "50",
        "--temperature", "0.2",
        "--api-url", "http://localhost:8000/v1/chat/completions",
        "--model", "custom/model"
    ])
    assert args.batch_size == 50
    assert args.temperature == 0.2


def test_tcfd_validation_result_model():
    """Test TCFDValidationResult Pydantic model."""
    result = TCFDValidationResult(valid_keywords=["变频电机", "碳交易", "新能源汽车"])
    assert len(result.valid_keywords) == 3
    assert "变频电机" in result.valid_keywords


def test_validate_batch():
    """Test batch validation returns valid keywords."""
    mock_response = MagicMock()
    mock_parsed = TCFDValidationResult(
        valid_keywords=["变频电机", "新能源汽车"]
    )
    mock_response.choices = [MagicMock(message=MagicMock(parsed=mock_parsed))]

    with patch("tcfd_extractor.tcfd_word_bag_validator.OpenAI") as mock_openai:
        mock_client = MagicMock()
        mock_client.beta.chat.completions.parse.return_value = mock_response
        mock_openai.return_value = mock_client

        result = validate_batch(
            ["变频电机", "智能手机", "新能源汽车"],
            "http://localhost:8000/v1/chat/completions",
            "test/model",
            0.1
        )

        assert isinstance(result, TCFDValidationResult)
        assert "变频电机" in result.valid_keywords
        assert "新能源汽车" in result.valid_keywords
        assert "智能手机" not in result.valid_keywords  # should be excluded


def test_process_word_bag():
    """Test that process_word_bag preserves structure and filters keywords."""

    def mock_validate_batch(keywords, *args, **kwargs):
        # Mock: keep only keywords that contain "电" or "碳"
        valid = [kw for kw in keywords if "电" in kw or "碳" in kw]
        return TCFDValidationResult(valid_keywords=valid)

    from tcfd_extractor.tcfd_word_bag_validator import process_word_bag

    input_data = {
        "技术": {
            "电动": ["变频电机", "智能手机", "新能源汽车"],
            "其他": ["碳交易", "手机"]
        },
        "市场": {
            "需求": ["绿色偏好", "普通商品"]
        }
    }

    valid_result, rejected_result = process_word_bag(input_data, mock_validate_batch, batch_size=10)

    # Check structure is preserved in valid result
    assert "技术" in valid_result
    assert "市场" in valid_result
    assert "电动" in valid_result["技术"]
    assert "其他" in valid_result["技术"]
    assert "需求" in valid_result["市场"]

    # Check keywords were filtered
    assert "变频电机" in valid_result["技术"]["电动"]
    assert "智能手机" not in valid_result["技术"]["电动"]
    assert "新能源汽车" not in valid_result["技术"]["电动"]
    assert "碳交易" in valid_result["技术"]["其他"]
    assert "手机" not in valid_result["技术"]["其他"]
    assert "绿色偏好" not in valid_result["市场"]["需求"]
    assert "普通商品" not in valid_result["市场"]["需求"]

    # Check rejected keywords
    assert "智能手机" in rejected_result["技术"]["电动"]
    assert "新能源汽车" in rejected_result["技术"]["电动"]
    assert "手机" in rejected_result["技术"]["其他"]
    assert "普通商品" in rejected_result["市场"]["需求"]


def test_save_results(tmp_path):
    """Test results are saved correctly to JSON with same structure."""
    data = {
        "技术": {
            "电动": ["变频电机", "新能源汽车"],
            "其他": ["碳交易"]
        },
        "市场": {
            "需求": ["绿色偏好"]
        }
    }

    output_path = tmp_path / "output.json"
    save_results(data, str(output_path))

    with open(output_path, "r", encoding="utf-8") as f:
        saved = json.load(f)

    assert saved == data