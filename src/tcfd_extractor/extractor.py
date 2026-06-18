import functools
import re
import time
from pathlib import Path

import requests
from openai import OpenAI
from pydantic import BaseModel, Field


class TCFDKeywords(BaseModel):
    """TCFD关键词输出结构"""

    政策维度: list[str] = Field(
        description="政策法律相关关键词，如碳税、排放限制、碳交易、环保合规成本、政府补贴等。如果没有则为空列表"
    )
    市场维度: list[str] = Field(
        description="市场需求、原材料价格、绿色偏好等关键词。如果没有则为空列表"
    )
    技术维度: list[str] = Field(
        description="低碳技术、可再生能源、研发创新等关键词。如果没有则为空列表"
    )


def load_word_bag(path: str) -> dict[str, list[str]]:
    """从 words_bag.md 加载词袋"""
    content = Path(path).read_text(encoding="utf-8")
    word_bag = {"政策维度": [], "市场维度": [], "技术维度": []}

    # 解析词袋格式
    patterns = {
        "政策维度": r"政策维度[（(][^）)]*[）)]\s*(.+?)(?=\n市场维度|\n技术维度|词袋B|$)",
        "市场维度": r"市场维度[（(][^）)]*[）)]\s*(.+?)(?=\n技术维度|词袋B|$)",
        "技术维度": r"技术维度[（(][^）)]*[）)]\s*(.+?)(?=\n词袋B|$)",
    }

    for dim, pattern in patterns.items():
        match = re.search(pattern, content, re.DOTALL)
        if match:
            words = [w.strip() for w in re.split(r"[、,]", match.group(1)) if w.strip()]
            word_bag[dim] = words

    return word_bag


def read_text_with_fallback(path: Path) -> str:
    """尝试多种编码读取文本"""
    encodings = ["utf-8", "gbk", "gb2312", "latin1"]
    for enc in encodings:
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
    raise ValueError(f"无法解码文件: {path}")


def retry_on_failure(max_retries: int = 3, delay: int = 2):
    """重试装饰器"""

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        time.sleep(delay * (attempt + 1))
            raise last_exception

        return wrapper

    return decorator


def check_sglang_health(base_url: str) -> bool:
    """检查SGLang服务健康状态"""
    try:
        health_url = base_url.replace("/v1", "") + "/health"
        response = requests.get(health_url, timeout=5)
        return response.status_code == 200
    except:
        return False


class TCFDKeywordExtractor:
    """调用SGLang提取TCFD关键词"""

    SYSTEM_PROMPT = """你是一个专业的ESG与气候风险财务分析师，精通TCFD框架。
你的任务是从企业年报文本片段中提取与气候相关的关键词。

请严格按照以下三个维度提取：
1. 绿色政策维度：碳达峰、碳中和、碳交易、碳税、排放限制、环保督察、能耗双控等
2. 绿色市场维度：碳排放配额、绿色信贷、ESG评级、碳关税、绿色供应链等
3. 绿色技术维度：低碳技术、节能技术、清洁能源、提标改造、超低排放等

提取规则：
- 必须提取文本中实际出现的词汇，不要总结或重写
- 优先从以下词袋中选择：{word_bag}
- 如果文本中有符合维度但不在词袋中的新词，也可以提取
- 每个关键词不超过8个字
- 如果某维度没有相关内容，返回空列表[]
- 严格按JSON格式输出"""

    def __init__(
        self,
        base_url: str = "http://127.0.0.1:30000/v1",
        model_name: str = "Qwen/Qwen3.5-35B-A3B",
    ):
        self.client = OpenAI(base_url=base_url, api_key="sk-local")
        self.model_name = model_name

    @retry_on_failure(max_retries=3, delay=2)
    def extract(
        self, text_chunk: str, word_bag: dict[str, list[str]]
    ) -> dict[str, list[str]]:
        """从文本块中提取关键词"""
        word_bag_text = ",".join(
            word_bag.get("政策维度", [])
            + word_bag.get("市场维度", [])
            + word_bag.get("技术维度", [])
        )

        try:
            response = self.client.beta.chat.completions.parse(
                model=self.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": self.SYSTEM_PROMPT.format(word_bag=word_bag_text),
                    },
                    {
                        "role": "user",
                        "content": f"请提取以下年报片段中的TCFD关键词：\n\n{text_chunk}",
                    },
                ],
                response_format=TCFDKeywords,
                temperature=0.1,
                timeout=60,
            )

            parsed_result = response.choices[0].message.parsed
            return {
                "政策维度": parsed_result.政策维度,
                "市场维度": parsed_result.市场维度,
                "技术维度": parsed_result.技术维度,
            }
        except Exception as e:
            print(f"结构化输出失败，使用Fallback: {e}")
            return self._extract_fallback(text_chunk, word_bag)

    def _extract_fallback(
        self, text_chunk: str, word_bag: dict[str, list[str]]
    ) -> dict[str, list[str]]:
        """Fallback提取方式"""
        return {"政策维度": [], "市场维度": [], "技术维度": []}
