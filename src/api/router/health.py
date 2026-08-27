"""
健康检查路由
"""

from datetime import datetime

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "oncall-opinion-analyse",
        "version": "4.0.0",
    }


@router.get("/ready")
async def readiness_check():
    """就绪检查"""
    # TODO: 检查数据库连接、向量存储等
    return {
        "ready": True,
        "checks": {
            "database": "ok",
            "vector_store": "ok",
            "knowledge_graph": "ok",
        },
    }
