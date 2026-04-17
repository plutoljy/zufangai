"""
Dog Retriever Agent - 猎犬检索师
职责: 法律条文检索 + 案例匹配 + 建议生成
"""

from openai import OpenAI
from typing import Dict, List
import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import settings
from prompts import dog_retriever_prompt
from knowledge.retriever import get_retriever


class DogRetriever:
    """猎犬检索师 - 法律条文检索和案例匹配"""

    def __init__(self):
        self.client = OpenAI(api_key=settings.openai_api_key)
        self.model = "gpt-4o-mini"  # 使用更经济的模型
        self.temperature = 0.1

        # 初始化知识库检索器
        try:
            self.retriever = get_retriever()
            self.use_rag = True
            print("[OK] Dog Retriever: 知识库已加载")
        except FileNotFoundError as e:
            print(f"[WARN] Dog Retriever: 知识库未构建，使用 mock 数据")
            print(f"   请运行: python -m knowledge.vectorize")
            self.retriever = None
            self.use_rag = False

    def retrieve(self, risk_items: List[Dict], location: str = "beijing") -> Dict:
        """
        检索相关法律条文和案例

        Args:
            risk_items: 风险条款列表，格式:
                [
                    {
                        "clause": "押金为两个月租金",
                        "risk_level": "high",
                        "issue": "押金超限"
                    }
                ]
            location: 地理位置，用于案例检索优先级

        Returns:
            {
                "legal_references": [...],  # 法律条文引用
                "case_references": [...],   # 案例引用
                "suggestions": [...],       # 可操作建议
                "negotiation_tips": [...]   # 协商话术
            }
        """
        # 1. 检索相关法律和案例
        if self.use_rag:
            # 使用真实的 RAG 检索
            query = " ".join([item.get("issue", "") for item in risk_items])
            search_results = self.retriever.search_all(query, top_k=3)
            legal_docs = self._format_legal_docs(search_results['legal_docs'])
            cases = self._format_cases(search_results['cases'])
        else:
            # 降级到 mock 数据
            legal_docs = dog_retriever_prompt.MOCK_LEGAL_DOCS
            cases = dog_retriever_prompt.MOCK_CASES

        # 2. 构建prompt
        prompt = dog_retriever_prompt.FORMATTING_PROMPT_TEMPLATE.format(
            legal_docs=json.dumps(legal_docs, ensure_ascii=False, indent=2),
            cases=json.dumps(cases, ensure_ascii=False, indent=2),
            risk_items=json.dumps(risk_items, ensure_ascii=False, indent=2)
        )

        # 3. 调用LLM格式化输出
        try:
            messages = [
                {"role": "system", "content": dog_retriever_prompt.SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ]

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                timeout=30,
                response_format={"type": "json_object"}
            )

            result = json.loads(response.choices[0].message.content)

            # 验证返回结构
            if not self._validate_result(result):
                print("Warning: LLM返回结构不完整，使用降级数据")
                return self._build_fallback_result(legal_docs, cases)

            return result

        except json.JSONDecodeError as e:
            print(f"JSON解析错误: {e}")
            return self._build_fallback_result(legal_docs, cases)
        except Exception as e:
            print(f"Dog Retriever调用失败: {e}")
            return self._build_fallback_result(legal_docs, cases)

    def _validate_result(self, result: Dict) -> bool:
        """验证返回结果结构是否完整"""
        required_keys = ["legal_references", "case_references", "suggestions", "negotiation_tips"]
        return all(key in result for key in required_keys)

    def _format_legal_docs(self, search_results: List[Dict]) -> List[Dict]:
        """格式化法律文档检索结果"""
        formatted = []
        for idx, result in enumerate(search_results):
            formatted.append({
                "law_id": f"law_{idx + 1}",
                "title": f"法律条文 {idx + 1}",
                "content": result['text'][:500],  # 限制长度
                "source": result['metadata']['source'],
                "relevance": f"相似度: {result['score']:.4f}"
            })
        return formatted

    def _format_cases(self, search_results: List[Dict]) -> List[Dict]:
        """格式化案例检索结果"""
        formatted = []
        for idx, result in enumerate(search_results):
            formatted.append({
                "case_id": f"case_{idx + 1}",
                "title": f"案例 {idx + 1}",
                "content": result['text'][:500],  # 限制长度
                "source": result['metadata']['source'],
                "relevance": f"相似度: {result['score']:.4f}"
            })
        return formatted

    def _build_fallback_result(self, legal_docs: List[Dict], cases: List[Dict]) -> Dict:
        """构建降级返回数据"""
        return {
            "legal_references": legal_docs,
            "case_references": cases,
            "suggestions": [
                "建议与房东协商降低押金至一个月租金",
                "要求修改不合理的违约金条款",
                "签约时拍照记录房屋现状"
            ],
            "negotiation_tips": [
                {
                    "issue": "押金超限",
                    "strategy": "先说法律规定，再提替代方案",
                    "script": "根据租赁管理办法，押金最多一个月租金。咱们改成合理金额，如果您担心风险，我可以押一付三。"
                }
            ]
        }


if __name__ == "__main__":
    # 测试代码
    retriever = DogRetriever()

    test_risks = [
        {
            "clause": "押金为两个月租金",
            "risk_level": "high",
            "issue": "押金超限"
        },
        {
            "clause": "提前退租需支付剩余租期全部租金作为违约金",
            "risk_level": "critical",
            "issue": "违约金过高"
        }
    ]

    print("=" * 60)
    print("Dog Retriever Agent 测试")
    print("=" * 60)

    result = retriever.retrieve(test_risks, "beijing")

    print("\n法律条文引用:")
    print("-" * 60)
    for ref in result.get("legal_references", []):
        print(f"- {ref.get('title', 'N/A')}")

    print("\n案例引用:")
    print("-" * 60)
    for case in result.get("case_references", []):
        print(f"- {case.get('title', 'N/A')}")

    print("\n建议:")
    print("-" * 60)
    for suggestion in result.get("suggestions", []):
        print(f"- {suggestion}")

    print("\n协商话术:")
    print("-" * 60)
    for tip in result.get("negotiation_tips", []):
        print(f"问题: {tip.get('issue', 'N/A')}")
        print(f"策略: {tip.get('strategy', 'N/A')}")
        print(f"话术: {tip.get('script', 'N/A')}")
        print()

    print("\n完整JSON输出:")
    print("=" * 60)
    print(json.dumps(result, ensure_ascii=False, indent=2))
