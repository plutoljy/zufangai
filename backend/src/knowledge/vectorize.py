"""
向量化模块：使用千问 Embeddings + FAISS 构建向量索引
"""

import os
import pickle
import sys
import time
from pathlib import Path
from typing import Dict, List

import faiss
import numpy as np
from openai import OpenAI

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import settings
from knowledge.load_knowledge import load_all_knowledge


class VectorStore:
    """向量存储和检索（使用千问 Embedding）"""

    def __init__(self):
        """初始化千问 Embedding 客户端"""
        self.client = OpenAI(
            api_key=settings.embedding_api_key,
            base_url=settings.embedding_base_url
        )
        self.model = settings.embedding_model
        self.dimension = 1536  # text-embedding-v1 的维度
        self.index = None
        self.chunks = []
        print(f"使用千问 Embedding: {self.model}")

    def embed_texts(self, texts: List[str], max_retries: int = 3) -> np.ndarray:
        """批量生成 embeddings（带重试机制，自动截断过长文本）"""
        if not texts:
            return np.empty((0, self.dimension), dtype="float32")

        # 截断过长文本（千问限制 2048 tokens，约 1500 字符安全）
        truncated_texts = [text[:1500] if len(text) > 1500 else text for text in texts]

        for attempt in range(max_retries):
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=truncated_texts
                )
                embeddings = [item.embedding for item in response.data]
                return np.array(embeddings, dtype='float32')
            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    print(f"   请求失败，{wait_time}秒后重试... ({attempt + 1}/{max_retries})")
                    time.sleep(wait_time)
                else:
                    raise Exception(f"Embedding生成失败（已重试{max_retries}次）: {e}") from e

    def build_index(self, chunks: List[Dict], batch_size: int = 20):
        """构建 FAISS 索引（批量处理，千问限制最多25个）"""
        self.chunks = chunks
        texts = [chunk["text"] for chunk in chunks]
        total = len(texts)
        total_batches = (total + batch_size - 1) // batch_size if total else 0

        print(f"正在生成 {total} 个文本的 embeddings（批量大小: {batch_size}）...")
        all_embeddings = []
        for i in range(0, total, batch_size):
            batch_texts = texts[i : i + batch_size]
            batch_num = i // batch_size + 1
            print(f"   处理批次 {batch_num}/{total_batches} ({len(batch_texts)} 个文本)...")
            all_embeddings.append(self.embed_texts(batch_texts))

        embeddings = (
            np.vstack(all_embeddings)
            if all_embeddings
            else np.empty((0, self.dimension), dtype="float32")
        )

        print("正在构建FAISS索引...")
        self.index = faiss.IndexFlatL2(self.dimension)
        if len(embeddings):
            self.index.add(embeddings)

        print(f"[OK] 索引构建完成！共 {self.index.ntotal} 个向量")

    def save(self, save_dir: str = "vectorstore"):
        """保存索引和 chunks"""
        save_path = Path(save_dir)
        save_path.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(save_path / "index.faiss"))
        with open(save_path / "chunks.pkl", "wb") as f:
            pickle.dump(self.chunks, f)
        print(f"[OK] 向量库已保存到: {save_dir}")

    def load(self, load_dir: str = "vectorstore"):
        """加载索引和 chunks"""
        load_path = Path(load_dir)
        self.index = faiss.read_index(str(load_path / "index.faiss"))
        with open(load_path / "chunks.pkl", "rb") as f:
            self.chunks = pickle.load(f)
        print(f"[OK] 向量库已加载，共 {len(self.chunks)} 个 chunks")

    def search(self, query: str, top_k: int = 5) -> List[Dict]:
        """语义检索"""
        if self.index is None:
            raise ValueError("向量索引未加载，请先构建或加载向量库")

        query_embedding = self.embed_texts([query])
        distances, indices = self.index.search(query_embedding, top_k)

        results = []
        for idx, distance in zip(indices[0], distances[0]):
            if idx == -1 or idx >= len(self.chunks):
                continue
            results.append({**self.chunks[idx], "score": float(distance)})
        return results


def build_knowledge_base(
    data_dir: str = "src/knowledge/data",
    save_dir: str = "src/knowledge/vectorstore",
):
    """构建知识库（一次性执行）"""
    print("=" * 60)
    print("开始构建知识库")
    print("=" * 60)

    print("\n1. 加载知识文件...")
    knowledge = load_all_knowledge(data_dir)
    total_chunks = sum(len(chunks) for chunks in knowledge.values())
    print(f"   共加载 {len(knowledge)} 个文件，{total_chunks} 个段落")

    all_chunks = []
    for chunks in knowledge.values():
        all_chunks.extend(chunks)

    print("\n2. 构建向量索引...")
    vector_store = VectorStore()
    vector_store.build_index(all_chunks)

    print("\n3. 保存向量库...")
    vector_store.save(save_dir)

    print("\n" + "=" * 60)
    print("[OK] 知识库构建完成！")
    print("=" * 60)
    return vector_store


if __name__ == "__main__":
    build_knowledge_base()
