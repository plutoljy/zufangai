"""
知识库数据加载模块
功能：读取txt文件并按段落分块
"""

from typing import List, Dict
from pathlib import Path


def load_txt_file(file_path: str) -> List[Dict[str, any]]:
    """
    读取txt文件并按段落分块

    Args:
        file_path: txt文件路径

    Returns:
        List[Dict]: 每个Dict包含 'text' 和 'metadata'

    Example:
        >>> chunks = load_txt_file("data/租房法律.txt")
        >>> print(chunks[0])
        {'text': '一、押金退还纠纷...', 'metadata': {'source': '租房法律.txt', 'chunk_id': 0}}
    """
    path = Path(file_path)

    # 读取文件（尝试多种编码）
    encodings = ['utf-8', 'gbk', 'gb2312']
    content = None

    for encoding in encodings:
        try:
            with open(path, 'r', encoding=encoding) as f:
                content = f.read()
            break
        except UnicodeDecodeError:
            continue

    if content is None:
        raise ValueError(f"无法解码文件 {path}，尝试了编码: {encodings}")

    # 按空行分割段落
    paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]

    # 构建chunks
    chunks = []
    for idx, text in enumerate(paragraphs):
        chunks.append({
            'text': text,
            'metadata': {
                'source': path.name,
                'chunk_id': idx,
                'chunk_count': len(paragraphs)
            }
        })

    return chunks


def load_all_knowledge(data_dir: str = "knowledge/data") -> Dict[str, List[Dict]]:
    """
    加载所有知识库文件

    Args:
        data_dir: 数据目录路径

    Returns:
        Dict: 键为文件名，值为chunks列表
    """
    data_path = Path(data_dir)
    knowledge = {}

    for txt_file in data_path.glob("*.txt"):
        file_key = txt_file.stem  # 不带扩展名的文件名
        knowledge[file_key] = load_txt_file(str(txt_file))

    return knowledge


if __name__ == "__main__":
    # 测试代码
    print("=" * 60)
    print("知识库加载测试")
    print("=" * 60)

    knowledge = load_all_knowledge("data")

    for file_name, chunks in knowledge.items():
        print(f"\n文件: {file_name}")
        print(f"段落数: {len(chunks)}")
        print(f"第一段预览: {chunks[0]['text'][:100]}...")
