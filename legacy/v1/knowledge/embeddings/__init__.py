"""
向量嵌入模块
使用 BGE-M3 模型生成文本向量
"""

from typing import List, Optional
import hashlib


class BGEEmbedding:
    """
    BGE-M3 向量嵌入

    特点:
    - 支持中英文
    - 最大长度 8192 tokens
    - 向量维度 1024
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-m3",
        device: str = "cpu",
        max_length: int = 8192,
    ):
        self.model_name = model_name
        self.device = device
        self.max_length = max_length
        self._model = None
        self.dimension = 1024

    def _load_model(self):
        """延迟加载模型"""
        if self._model is None:
            try:
                from FlagEmbedding import BGEM3FlagModel
                self._model = BGEM3FlagModel(
                    self.model_name,
                    use_fp16=self.device == "cuda",
                    device=self.device,
                )
            except ImportError:
                raise ImportError(
                    "请安装 FlagEmbedding: pip install FlagEmbedding"
                )

    def embed(
        self,
        texts: List[str],
        batch_size: int = 12,
        max_length: Optional[int] = None,
    ) -> List[List[float]]:
        """
        生成文本向量

        Args:
            texts: 文本列表
            batch_size: 批处理大小
            max_length: 最大长度（覆盖默认值）

        Returns:
            向量列表，每个向量维度为 1024
        """
        self._load_model()

        max_len = max_length or self.max_length

        # 截断过长文本
        truncated_texts = [
            t[:max_len * 2] if len(t) > max_len * 2 else t
            for t in texts
        ]

        embeddings = self._model.encode(
            truncated_texts,
            batch_size=batch_size,
            max_length=max_len,
        )['dense_vecs']

        return embeddings.tolist()

    def embed_single(self, text: str) -> List[float]:
        """生成单个文本的向量"""
        return self.embed([text])[0]

    def compute_similarity(
        self,
        vec1: List[float],
        vec2: List[float],
    ) -> float:
        """计算两个向量的余弦相似度"""
        import numpy as np

        v1 = np.array(vec1)
        v2 = np.array(vec2)

        dot_product = np.dot(v1, v2)
        norm1 = np.linalg.norm(v1)
        norm2 = np.linalg.norm(v2)

        if norm1 == 0 or norm2 == 0:
            return 0.0

        return float(dot_product / (norm1 * norm2))


class MockEmbedding:
    """
    模拟嵌入（用于测试）
    不加载实际模型，生成确定性向量
    """

    def __init__(self, dimension: int = 1024):
        self.dimension = dimension

    def embed(self, texts: List[str], **kwargs) -> List[List[float]]:
        """生成模拟向量"""
        result = []
        for text in texts:
            # 使用文本 hash 生成确定性向量
            h = hashlib.sha256(text.encode()).digest()
            vec = []
            for i in range(self.dimension):
                # 循环使用 hash 字节
                byte_idx = i % len(h)
                vec.append(float(h[byte_idx]) / 255.0)
            result.append(vec)
        return result

    def embed_single(self, text: str) -> List[float]:
        return self.embed([text])[0]

    def compute_similarity(
        self,
        vec1: List[float],
        vec2: List[float],
    ) -> float:
        import numpy as np
        v1, v2 = np.array(vec1), np.array(vec2)
        return float(np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2) + 1e-8))
