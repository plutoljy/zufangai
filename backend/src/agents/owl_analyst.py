"""
Owl Analyst Agent - 猫头鹰解析师
负责合同条款提取和风险识别
"""

from openai import OpenAI
from typing import Dict, List, Optional
import json
import time
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from prompts import owl_analyst_prompt


class OwlAnalyst:
    """猫头鹰解析师 - 合同条款提取和风险识别"""

    def __init__(self):
        """初始化 DeepSeek 客户端"""
        self.client = OpenAI(
            api_key=settings.deepseek_api_key,
            base_url=settings.deepseek_base_url
        )
        self.model = settings.deepseek_model
        self.temperature = 0.1
        self.timeout = 30
        print("[OK] Owl Analyst: 使用 DeepSeek 模型")

    def analyze(self, contract_text: str) -> Dict:
        """
        分析租房合同

        Args:
            contract_text: 合同文本

        Returns:
            {
                "entities": {
                    "landlord": "甲方姓名",
                    "tenant": "乙方姓名",
                    "rent": 5000,
                    "deposit": 10000,
                    "duration": "12个月",
                    ...
                },
                "risk_items": [
                    {
                        "type": "违约金过高",
                        "description": "...",
                        "severity": "high"
                    },
                    ...
                ]
            }
        """
        if not contract_text or not contract_text.strip():
            return {
                "entities": {},
                "risk_items": []
            }

        # 1. 构建prompt
        user_prompt = owl_analyst_prompt.USER_PROMPT_TEMPLATE.format(
            contract_text=contract_text
        )

        messages = [
            {"role": "system", "content": owl_analyst_prompt.SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt}
        ]

        # 2. 调用LLM (带重试)
        try:
            response_text = self._call_llm_with_retry(messages)
            result = json.loads(response_text)

            # 验证返回结构
            if not isinstance(result, dict):
                raise ValueError("LLM返回的不是字典格式")

            if "entities" not in result:
                result["entities"] = {}
            if "risk_items" not in result:
                result["risk_items"] = []

            return result

        except json.JSONDecodeError as e:
            print(f"Owl Analyst JSON解析错误: {e}")
            return {
                "entities": {},
                "risk_items": []
            }
        except Exception as e:
            print(f"Owl Analyst分析错误: {e}")
            return {
                "entities": {},
                "risk_items": []
            }

    def _call_llm_with_retry(self, messages: List[Dict], max_retries: int = 3) -> str:
        """
        调用LLM,带重试机制

        Args:
            messages: 消息列表
            max_retries: 最大重试次数

        Returns:
            LLM响应文本

        Raises:
            Exception: 所有重试失败后抛出异常
        """
        last_error = None

        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=self.temperature,
                    timeout=self.timeout,
                    response_format={"type": "json_object"}
                )

                content = response.choices[0].message.content

                if not content:
                    raise ValueError("LLM返回内容为空")

                return content

            except Exception as e:
                last_error = e

                if attempt == max_retries - 1:
                    # 最后一次重试失败,抛出异常
                    raise Exception(f"LLM调用失败(已重试{max_retries}次): {str(e)}")

                # 指数退避
                wait_time = 2 ** attempt
                print(f"LLM调用失败,重试 {attempt + 1}/{max_retries} (等待{wait_time}秒)...")
                time.sleep(wait_time)

        # 理论上不会到这里,但为了类型安全
        raise Exception(f"LLM调用失败: {str(last_error)}")


# 测试代码
if __name__ == "__main__":
    print("=== Owl Analyst 测试 ===\n")

    analyst = OwlAnalyst()

    test_contract = """
    租房合同

    甲方(出租方): 张三
    乙方(承租方): 李四
    房屋地址: 北京市朝阳区某小区1号楼101室
    月租金: 5000元
    押金: 10000元
    租期: 12个月 (2026年1月1日至2026年12月31日)

    特别约定:
    1. 乙方提前退租的,甲方有权扣除全部押金作为违约金
    2. 水费按9元/立方米收取,电费按1.5元/度收取
    3. 房屋维修费用由乙方承担
    4. 甲方有权随时进入房屋检查
    """

    print("输入合同文本:")
    print("-" * 50)
    print(test_contract)
    print("-" * 50)
    print("\n分析中...\n")

    result = analyst.analyze(test_contract)

    print("分析结果:")
    print("=" * 50)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("=" * 50)

    # 测试空输入
    print("\n测试空输入:")
    empty_result = analyst.analyze("")
    print(json.dumps(empty_result, ensure_ascii=False, indent=2))
