"""
文件操作工具
提供文件读写、搜索等功能
"""

import os
import glob
import hashlib
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import aiofiles

from ..base import ToolResult, ToolStatus


class FileTools:
    """
    文件操作工具

    提供:
    - read_file: 读取文件
    - write_file: 写入文件
    - list_directory: 列出目录
    - search_files: 搜索文件
    - delete_file: 删除文件
    - copy_file: 复制文件
    """

    def __init__(self, base_path: str = "/tmp"):
        self.base_path = Path(base_path)
        self._allowed_paths = [self.base_path]

    def get_handlers(self) -> Dict[str, Callable]:
        """获取工具处理器"""
        return {
            "read_file": self.read_file,
            "write_file": self.write_file,
            "list_directory": self.list_directory,
            "search_files": self.search_files,
            "delete_file": self.delete_file,
            "copy_file": self.copy_file,
            "file_info": self.file_info,
            "create_directory": self.create_directory,
        }

    def _resolve_path(self, path: str) -> Path:
        """解析路径，确保在允许的范围内"""
        p = Path(path)
        if not p.is_absolute():
            p = self.base_path / p

        # 规范化路径
        p = p.resolve()

        # 安全检查：解析符号链接后仍必须位于 allowlist 根目录内
        if not any(p == allowed.resolve() or p.is_relative_to(allowed.resolve()) for allowed in self._allowed_paths):
            raise PermissionError(f"Path is outside allowed roots: {path}")
        return p

    async def read_file(
        self,
        path: str,
        encoding: str = "utf-8",
        start_line: int = 0,
        end_line: Optional[int] = None,
    ) -> ToolResult:
        """
        读取文件内容

        Args:
            path: 文件路径
            encoding: 编码
            start_line: 起始行
            end_line: 结束行
        """
        try:
            file_path = self._resolve_path(path)

            if not file_path.exists():
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"File not found: {path}",
                )

            if not file_path.is_file():
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Not a file: {path}",
                )

            async with aiofiles.open(file_path, "r", encoding=encoding) as f:
                content = await f.read()

            lines = content.split("\n")

            # 处理行范围
            if end_line is not None:
                lines = lines[start_line:end_line]
            else:
                lines = lines[start_line:]

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "path": str(file_path),
                    "content": "\n".join(lines),
                    "total_lines": len(content.split("\n")),
                    "returned_lines": len(lines),
                },
            )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
            )

    async def write_file(
        self,
        path: str,
        content: str,
        mode: str = "write",  # write, append
        encoding: str = "utf-8",
    ) -> ToolResult:
        """
        写入文件

        Args:
            path: 文件路径
            content: 内容
            mode: 写入模式 (write/append)
            encoding: 编码
        """
        try:
            file_path = self._resolve_path(path)

            # 确保目录存在
            file_path.parent.mkdir(parents=True, exist_ok=True)

            write_mode = "a" if mode == "append" else "w"

            async with aiofiles.open(file_path, write_mode, encoding=encoding) as f:
                await f.write(content)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "path": str(file_path),
                    "bytes_written": len(content.encode(encoding)),
                    "mode": mode,
                },
            )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
            )

    async def list_directory(
        self,
        path: str = ".",
        pattern: str = "*",
        include_hidden: bool = False,
    ) -> ToolResult:
        """
        列出目录内容

        Args:
            path: 目录路径
            pattern: 匹配模式
            include_hidden: 是否包含隐藏文件
        """
        try:
            dir_path = self._resolve_path(path)

            if not dir_path.exists():
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Directory not found: {path}",
                )

            if not dir_path.is_dir():
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Not a directory: {path}",
                )

            items = []

            for item in dir_path.glob(pattern):
                # 跳过隐藏文件
                if not include_hidden and item.name.startswith("."):
                    continue

                stat = item.stat()
                items.append({
                    "name": item.name,
                    "path": str(item),
                    "type": "directory" if item.is_dir() else "file",
                    "size": stat.st_size if item.is_file() else 0,
                    "modified": stat.st_mtime,
                })

            # 排序：目录优先，然后按名称
            items.sort(key=lambda x: (x["type"] == "file", x["name"]))

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "path": str(dir_path),
                    "items": items,
                    "total": len(items),
                },
            )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
            )

    async def search_files(
        self,
        path: str,
        pattern: str,
        content_pattern: Optional[str] = None,
        max_results: int = 100,
    ) -> ToolResult:
        """
        搜索文件

        Args:
            path: 搜索路径
            pattern: 文件名模式
            content_pattern: 内容匹配模式
            max_results: 最大结果数
        """
        try:
            search_path = self._resolve_path(path)

            if not search_path.exists():
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Path not found: {path}",
                )

            matches = []

            # 使用 glob 搜索
            for item in search_path.rglob(pattern):
                if len(matches) >= max_results:
                    break

                match_info = {
                    "path": str(item),
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                }

                # 如果需要搜索内容
                if content_pattern and item.is_file():
                    try:
                        with open(item, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                            if content_pattern in content:
                                match_info["matched"] = True
                                matches.append(match_info)
                    except Exception:
                        pass
                else:
                    matches.append(match_info)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "search_path": str(search_path),
                    "pattern": pattern,
                    "matches": matches,
                    "total": len(matches),
                },
            )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
            )

    async def delete_file(self, path: str) -> ToolResult:
        """删除文件"""
        try:
            file_path = self._resolve_path(path)

            if not file_path.exists():
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"File not found: {path}",
                )

            if file_path.is_dir():
                import shutil
                shutil.rmtree(file_path)
            else:
                file_path.unlink()

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"deleted": str(file_path)},
            )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
            )

    async def copy_file(
        self,
        source: str,
        destination: str,
    ) -> ToolResult:
        """复制文件"""
        try:
            import shutil

            src_path = self._resolve_path(source)
            dst_path = self._resolve_path(destination)

            if not src_path.exists():
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"Source not found: {source}",
                )

            # 确保目标目录存在
            dst_path.parent.mkdir(parents=True, exist_ok=True)

            if src_path.is_dir():
                shutil.copytree(src_path, dst_path)
            else:
                shutil.copy2(src_path, dst_path)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "source": str(src_path),
                    "destination": str(dst_path),
                },
            )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
            )

    async def file_info(self, path: str) -> ToolResult:
        """获取文件信息"""
        try:
            file_path = self._resolve_path(path)

            if not file_path.exists():
                return ToolResult(
                    status=ToolStatus.ERROR,
                    error=f"File not found: {path}",
                )

            stat = file_path.stat()

            # 计算文件哈希
            file_hash = None
            if file_path.is_file():
                with open(file_path, "rb") as f:
                    file_hash = hashlib.md5(f.read()).hexdigest()

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={
                    "path": str(file_path),
                    "name": file_path.name,
                    "type": "directory" if file_path.is_dir() else "file",
                    "size": stat.st_size,
                    "created": stat.st_ctime,
                    "modified": stat.st_mtime,
                    "accessed": stat.st_atime,
                    "md5": file_hash,
                },
            )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
            )

    async def create_directory(
        self,
        path: str,
        parents: bool = True,
    ) -> ToolResult:
        """创建目录"""
        try:
            dir_path = self._resolve_path(path)

            dir_path.mkdir(parents=parents, exist_ok=True)

            return ToolResult(
                status=ToolStatus.SUCCESS,
                data={"created": str(dir_path)},
            )

        except Exception as e:
            return ToolResult(
                status=ToolStatus.ERROR,
                error=str(e),
            )
