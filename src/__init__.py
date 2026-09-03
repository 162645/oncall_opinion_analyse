"""
Oncall Opinion Analyse Agent
智能运维诊断平台
"""

__version__ = "4.0.0"

# 延迟导入，避免循环依赖
__all__ = [
    # Knowledge
    "KnowledgeDocument",
    "DocumentChunk",
    "DocumentType",
    "DocumentStatus",
    "ParserFactory",
    # Storage
    "LocalStorage",
    "MinIOStorage",
    "FileInfo",
    # Cache
    "RedisClient",
    "CacheService",
]

def __getattr__(name):
    """延迟导入"""
    if name in ["KnowledgeDocument", "DocumentChunk", "DocumentType", "DocumentStatus", "ParserFactory"]:
        from .knowledge import KnowledgeDocument, DocumentChunk, DocumentType, DocumentStatus, ParserFactory
        return locals()[name]
    elif name in ["LocalStorage", "MinIOStorage", "FileInfo"]:
        from .storage import LocalStorage, MinIOStorage, FileInfo
        return locals()[name]
    elif name in ["RedisClient", "CacheService"]:
        from .cache import RedisClient, CacheService
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
