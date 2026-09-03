"""
知识库管理路由
提供文档上传、检索、管理等 API
"""

import os
import uuid
import hashlib
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, UploadFile, File, HTTPException, Query, Form
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from src.knowledge.service import get_knowledge_service, KnowledgeService
from src.knowledge import DocumentStatus

router = APIRouter()


# ===== 请求/响应模型 =====

class DocumentUploadResponse(BaseModel):
    """文档上传响应"""
    success: bool
    document_id: str
    message: str
    file_name: str
    file_size: int


class DocumentListItem(BaseModel):
    """文档列表项"""
    id: str
    title: str
    doc_type: str
    file_name: str
    file_size: int
    status: str
    chunk_count: int
    created_at: str
    updated_at: str


class DocumentListResponse(BaseModel):
    """文档列表响应"""
    success: bool
    total: int
    documents: List[DocumentListItem]
    page: int
    page_size: int


class DocumentDetailResponse(BaseModel):
    """文档详情响应"""
    success: bool
    document: Optional[dict] = None
    error: Optional[str] = None


class SearchRequest(BaseModel):
    """搜索请求"""
    query: str
    top_k: int = 10
    filters: Optional[dict] = None


class SearchResult(BaseModel):
    """搜索结果项"""
    chunk_id: str
    doc_id: str
    doc_title: str
    content: str
    score: float


class SearchResponse(BaseModel):
    """搜索响应"""
    success: bool
    query: str
    results: List[SearchResult]
    total: int


class StatsResponse(BaseModel):
    """统计信息响应"""
    success: bool
    stats: dict


# ===== 临时存储 (后续替换为数据库) =====

_documents_db: dict = {}  # document_id -> document_data


# ===== API 端点 =====

@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Form(None),
    metadata: Optional[str] = Form(None),
):
    """
    上传文档

    支持格式: PDF, Word, Excel, Markdown, TXT, JSON, CSV
    """
    try:
        # 获取知识库服务
        service = get_knowledge_service()

        # 读取文件内容
        content = await file.read()

        # 解析元数据
        meta = {}
        if metadata:
            import json
            try:
                meta = json.loads(metadata)
            except:
                pass

        # 上传文档
        document = await service.upload_document(
            file_content=content,
            file_name=file.filename or "unknown",
            title=title,
            metadata=meta,
        )

        return DocumentUploadResponse(
            success=True,
            document_id=document.id,
            message="Document uploaded successfully, processing started",
            file_name=file.filename or "unknown",
            file_size=document.file_size,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/documents", response_model=DocumentListResponse)
async def list_documents(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    doc_type: Optional[str] = None,
    status: Optional[str] = None,
    search: Optional[str] = None,
):
    """
    获取文档列表

    支持分页、类型筛选、状态筛选、关键词搜索
    """
    service = get_knowledge_service()
    result = service.list_documents(
        page=page,
        page_size=page_size,
        doc_type=doc_type,
        status=status,
    )

    documents = [
        DocumentListItem(
            id=d.id,
            title=d.title,
            doc_type=d.doc_type.value,
            file_name=d.file_name,
            file_size=d.file_size,
            status=d.status.value,
            chunk_count=len(d.chunks),
            created_at=d.created_at.isoformat() if hasattr(d.created_at, 'isoformat') else str(d.created_at),
            updated_at=d.updated_at.isoformat() if hasattr(d.updated_at, 'isoformat') else str(d.updated_at),
        )
        for d in result["documents"]
    ]

    return DocumentListResponse(
        success=True,
        total=result["total"],
        documents=documents,
        page=result["page"],
        page_size=result["page_size"],
    )


@router.get("/documents/{doc_id}", response_model=DocumentDetailResponse)
async def get_document(doc_id: str):
    """获取文档详情"""
    service = get_knowledge_service()
    doc = service.get_document(doc_id)

    if not doc:
        return DocumentDetailResponse(
            success=False,
            error="Document not found",
        )

    return DocumentDetailResponse(
        success=True,
        document={
            "id": doc.id,
            "title": doc.title,
            "doc_type": doc.doc_type.value,
            "file_name": doc.file_name,
            "file_size": doc.file_size,
            "status": doc.status.value,
            "chunk_count": len(doc.chunks),
            "created_at": doc.created_at.isoformat() if hasattr(doc.created_at, 'isoformat') else str(doc.created_at),
            "updated_at": doc.updated_at.isoformat() if hasattr(doc.updated_at, 'isoformat') else str(doc.updated_at),
            "metadata": doc.metadata,
            "content_preview": doc.content[:500] if doc.content else "",
        },
    )


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    """
    删除文档

    完整删除：
    - 向量数据库中的向量
    - 关键词索引
    - 知识图谱节点
    - 内存数据
    """
    service = get_knowledge_service()

    # 使用异步删除
    success = await service.delete_document_async(doc_id)

    if not success:
        raise HTTPException(status_code=404, detail="Document not found")

    return {"success": True, "message": "Document deleted completely"}


@router.post("/search", response_model=SearchResponse)
async def search_knowledge(request: SearchRequest):
    """
    知识检索

    根据查询文本检索相关文档片段
    使用混合检索: 向量检索 + 关键词检索
    """
    service = get_knowledge_service()

    # 执行混合检索
    context = await service.search(
        query=request.query,
        top_k=request.top_k,
        use_vector=True,
        use_keyword=True,
    )

    # 转换结果
    results = []
    for r in context.results:
        doc = service.get_document(r.doc_id)
        results.append(SearchResult(
            chunk_id=f"{r.doc_id}-{r.metadata.get('position', 0)}",
            doc_id=r.doc_id,
            doc_title=doc.title if doc else r.metadata.get("doc_title", "Unknown"),
            content=r.content,
            score=r.score,
        ))

    return SearchResponse(
        success=True,
        query=request.query,
        results=results,
        total=len(results),
    )


@router.get("/stats", response_model=StatsResponse)
async def get_stats():
    """获取知识库统计信息"""
    service = get_knowledge_service()
    stats = service.get_stats()

    return StatsResponse(
        success=True,
        stats=stats,
    )


@router.post("/batch")
async def batch_upload(files: List[UploadFile] = File(...)):
    """批量上传文档"""
    results = []

    for file in files:
        try:
            result = await upload_document(file=file)
            results.append(result.dict())
        except Exception as e:
            results.append({
                "success": False,
                "file_name": file.filename,
                "error": str(e),
            })

    return {
        "success": True,
        "total": len(files),
        "results": results,
    }
