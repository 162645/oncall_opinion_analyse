"""
统一配置管理模块

所有配置项集中管理，从环境变量读取

使用方式:
    from src.core.config import settings

    # 获取配置
    api_key = settings.OPENAI_API_KEY
    qdrant_url = settings.QDRANT_URL
"""

import os
from typing import Optional
from dataclasses import dataclass, field
from functools import lru_cache


@dataclass
class Settings:
    """应用配置"""

    # ============ LLM 配置 ============
    OPENAI_API_KEY: str = ""
    ANTHROPIC_API_KEY: str = ""
    OPENAI_BASE_URL: Optional[str] = None
    OPENAI_MODEL: str = "gpt-4o"
    LLM_PROVIDER: str = "bupt"
    LLM_MODEL: str = ""
    DEEPSEEK_API_KEY: str = ""
    DEEPSEEK_BASE_URL: str = "https://api.deepseek.com"
    DEEPSEEK_MODEL: str = "deepseek-chat"
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"

    # ============ ClickHouse 配置 ============
    CLICKHOUSE_HOST: str = "localhost"
    CLICKHOUSE_PORT: int = 8123
    CLICKHOUSE_DATABASE: str = "network_telemetry"
    CLICKHOUSE_USER: str = "default"
    CLICKHOUSE_PASSWORD: str = ""
    CLICKHOUSE_PROTOCOL: str = "https"
    CLICKHOUSE_SECURE: bool = True

    # ============ Qdrant 向量数据库 ============
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: Optional[str] = None
    QDRANT_COLLECTION: str = "knowledge"

    # ============ Redis 缓存 ============
    REDIS_URL: str = "redis://localhost:6379"
    REDIS_DB: int = 0
    REDIS_PASSWORD: Optional[str] = None

    # ============ Neo4j 知识图谱 ============
    NEO4J_URI: str = "bolt://localhost:7687"
    NEO4J_USER: str = "neo4j"
    NEO4J_PASSWORD: str = "password"

    # ============ MinIO 对象存储 ============
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_SECURE: bool = False
    MINIO_BUCKET: str = "knowledge"

    # ============ gRPC 配置 ============
    GRPC_PYTHON_ADDRESS: str = "localhost:50051"
    GRPC_GO_ADDRESS: str = "localhost:50052"

    # ============ 服务端口 ============
    HTTP_PORT: int = 8000
    GRPC_PORT: int = 50051

    # ============ 日志配置 ============
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False

    # ============ 其他配置 ============
    ENABLE_TLS: bool = False
    ENVIRONMENT: str = "development"

    @property
    def clickhouse_url(self) -> str:
        """获取 ClickHouse 连接 URL"""
        protocol = self.CLICKHOUSE_PROTOCOL
        host = self.CLICKHOUSE_HOST
        port = self.CLICKHOUSE_PORT
        return f"{protocol}://{host}:{port}"

    @property
    def is_production(self) -> bool:
        """是否生产环境"""
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        """是否开发环境"""
        return self.ENVIRONMENT == "development"


@lru_cache()
def get_settings() -> Settings:
    """获取配置单例"""
    return Settings(
        # LLM
        OPENAI_API_KEY=os.getenv("OPENAI_API_KEY", ""),
        ANTHROPIC_API_KEY=os.getenv("ANTHROPIC_API_KEY", ""),
        OPENAI_BASE_URL=os.getenv("OPENAI_BASE_URL"),
        OPENAI_MODEL=os.getenv("OPENAI_MODEL", "gpt-4o"),
        LLM_PROVIDER=os.getenv("LLM_PROVIDER", "bupt"),
        LLM_MODEL=os.getenv("LLM_MODEL", ""),
        DEEPSEEK_API_KEY=os.getenv("DEEPSEEK_API_KEY", ""),
        DEEPSEEK_BASE_URL=os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com"),
        DEEPSEEK_MODEL=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
        ANTHROPIC_MODEL=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-20250514"),

        # ClickHouse
        CLICKHOUSE_HOST=os.getenv("CLICKHOUSE_HOST", "localhost"),
        CLICKHOUSE_PORT=int(os.getenv("CLICKHOUSE_PORT", "8123")),
        CLICKHOUSE_DATABASE=os.getenv("CLICKHOUSE_DATABASE", "network_telemetry"),
        CLICKHOUSE_USER=os.getenv("CLICKHOUSE_USER", "default"),
        CLICKHOUSE_PASSWORD=os.getenv("CLICKHOUSE_PASSWORD", ""),
        CLICKHOUSE_PROTOCOL=os.getenv("CLICKHOUSE_PROTOCOL", "https"),
        CLICKHOUSE_SECURE=os.getenv("CLICKHOUSE_SECURE", "true").lower() == "true",

        # Qdrant
        QDRANT_URL=os.getenv("QDRANT_URL", "http://localhost:6333"),
        QDRANT_API_KEY=os.getenv("QDRANT_API_KEY"),
        QDRANT_COLLECTION=os.getenv("QDRANT_COLLECTION", "knowledge"),

        # Redis
        REDIS_URL=os.getenv("REDIS_URL", "redis://localhost:6379"),
        REDIS_DB=int(os.getenv("REDIS_DB", "0")),
        REDIS_PASSWORD=os.getenv("REDIS_PASSWORD"),

        # Neo4j
        NEO4J_URI=os.getenv("NEO4J_URI", "bolt://localhost:7687"),
        NEO4J_USER=os.getenv("NEO4J_USER", "neo4j"),
        NEO4J_PASSWORD=os.getenv("NEO4J_PASSWORD", "password"),

        # MinIO
        MINIO_ENDPOINT=os.getenv("MINIO_ENDPOINT", "localhost:9000"),
        MINIO_ACCESS_KEY=os.getenv("MINIO_ACCESS_KEY", "minioadmin"),
        MINIO_SECRET_KEY=os.getenv("MINIO_SECRET_KEY", "minioadmin"),
        MINIO_SECURE=os.getenv("MINIO_SECURE", "false").lower() == "true",
        MINIO_BUCKET=os.getenv("MINIO_BUCKET", "knowledge"),

        # gRPC
        GRPC_PYTHON_ADDRESS=os.getenv("GRPC_PYTHON_ADDRESS", "localhost:50051"),
        GRPC_GO_ADDRESS=os.getenv("GRPC_GO_ADDRESS", "localhost:50052"),

        # 服务端口
        HTTP_PORT=int(os.getenv("HTTP_PORT", "8000")),
        GRPC_PORT=int(os.getenv("GRPC_PORT", "50051")),

        # 日志
        LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO"),
        DEBUG=os.getenv("DEBUG", "false").lower() == "true",

        # 其他
        ENABLE_TLS=os.getenv("ENABLE_TLS", "false").lower() == "true",
        ENVIRONMENT=os.getenv("ENVIRONMENT", "development"),
    )


# 全局配置实例
settings = get_settings()


def reload_settings():
    """重新加载配置（清除缓存）"""
    get_settings.cache_clear()
    global settings
    settings = get_settings()
    return settings
