from pathlib import Path

import pytest

from src.mcp.base import ToolStatus
from src.mcp.tools.file_tools import FileTools
from src.mcp.tools.memory_tools import MemoryTools
from src.mcp.tools.time_tools import TimeTools


@pytest.mark.asyncio
async def test_file_tools_use_real_implementation(tmp_path: Path):
    tools = FileTools(str(tmp_path))
    written = await tools.write_file("report.txt", "hello")
    assert written.status == ToolStatus.SUCCESS
    loaded = await tools.read_file("report.txt")
    assert loaded.data["content"] == "hello"
    listed = await tools.list_directory(".")
    assert [item["name"] for item in listed.data["items"]] == ["report.txt"]


@pytest.mark.asyncio
async def test_file_tools_block_path_escape(tmp_path: Path):
    tools = FileTools(str(tmp_path))
    result = await tools.read_file("../outside.txt")
    assert result.status == ToolStatus.ERROR
    assert "outside allowed roots" in result.error


@pytest.mark.asyncio
async def test_memory_tools_use_real_implementation(tmp_path: Path):
    tools = MemoryTools(str(tmp_path / "memory"))
    saved = await tools.save("incident", {"status": "open"})
    assert saved.status == ToolStatus.SUCCESS
    loaded = await tools.load("incident")
    assert loaded.data["found"] is True
    assert loaded.data["value"] == {"status": "open"}


@pytest.mark.asyncio
async def test_time_tools_use_real_implementation():
    tools = TimeTools()
    now = await tools.current_time("UTC")
    assert now.status == ToolStatus.SUCCESS
    assert now.data["timezone"] == "UTC"
