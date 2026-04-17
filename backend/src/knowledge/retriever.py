"""
检索接口模块
功能：封装向量检索逻辑，提供简单的API
"""

from pathlib import Path
from typing import List, Dict
from .vectorize import VectorStore


class KnowledgeRetriever:
    """知识库检索器"""

    def __init__(self, vectorstore_dir: str = "src/knowledge/vectorstore"):
        """
        初始化检索器

        Args:
            vectorstore_dir: 向量库目录路径
        """
        self.vector_store = VectorStore()

        # 检查向量库是否存在
        vectorstore_path = Path(vectorstore_dir)
        if not (vectorstore_path / "index.faiss").exists():
            raise FileNotFoundError(
                f"向量库不存在: {vectorstore_dir}\n"
                "请先运行: python -m knowledge.vectorize"
            )

        # 加载向量库
        self.vector_store.load(vectorstore_dir)

    def search_legal_docs(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        检索法律条文

        Args:
            query: 查询文本（如："押金超过一个月租金"）
            top_k: 返回结果数量

        Returns:
            List[Dict]: 检索结果，每个Dict包含 text, metadata, score
        """
        results = self.vector_store.search(query, top_k)

        # 只返回法律相关的结果
        legal_results = [
            r for r in results
            if '租房法律' in r['metadata']['source']
        ]

        return legal_results[:top_k]

    def search_cases(self, query: str, top_k: int = 3) -> List[Dict]:
        """
        检索案例

        Args:
            query: 查询文本
            top_k: 返回结果数量

        Returns:
            List[Dict]: 案例检索结果
        """
        results = self.vector_store.search(query, top_k)

        # 只返回案例相关的结果
        case_results = [
            r for r in results
            if '案例' in r['metadata']['source']
        ]

        return case_results[:top_k]

    def search_utility_info(self, query: str, top_k: int = 2) -> List[Dict]:
        """
        检索水电费信息

        Args:
            query: 查询文本
            top_k: 返回结果数量

        Returns:
            List[Dict]: 水电费信息
        """
        results = self.vector_store.search(query, top_k)

        # 只返回水电相关的结果
        utility_results = [
            r for r in results
            if '水电' in r['metadata']['source']
        ]

        return utility_results[:top_k]

    def search_all(self, query: str, top_k: int = 5) -> Dict[str, List[Dict]]:
        """
        综合检索（法律+案例+水电）

        Args:
            query: 查询文本
            top_k: 每类返回结果数量

        Returns:
            Dict: 包含 legal_docs, cases, utility_info 三个键
        """
        return {
            'legal_docs': self.search_legal_docs(query, top_k),
            'cases': self.search_cases(query, top_k),
            'utility_info': self.search_utility_info(query, top_k)
        }


# 全局单例（避免重复加载）
_retriever_instance = None


def get_retriever() -> KnowledgeRetriever:
    """获取检索器单例"""
    global _retriever_instance
    if _retriever_instance is None:
        _retriever_instance = KnowledgeRetriever()
    return _retriever_instance


if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("知识库检索测试")
    print("=" * 60)

    retriever = get_retriever()

    test_queries = [
        ("押金超过一个月租金怎么办", "legal_docs"),
        ("提前退租违约金案例", "cases"),
        ("北京水费多少钱一吨", "utility_info")
    ]

    for query, search_type in test_queries:
        print(f"\n查询: {query} (类型: {search_type})")
        print("-" * 60)

        if search_type == "legal_docs":
            results = retriever.search_legal_docs(query, top_k=2)
        elif search_type == "cases":
            results = retriever.search_cases(query, top_k=2)
        else:
            results = retriever.search_utility_info(query, top_k=2)

        for i, result in enumerate(results, 1):
            print(f"{i}. [{result['metadata']['source']}]")
            print(f"   {result['text'][:150]}...")
            print()
