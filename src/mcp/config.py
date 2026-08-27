"""
MCP 配置管理
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional
import os


@dataclass
class MCPServerConfig:
    """MCP Server 配置"""
    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command": self.command,
            "args": self.args,
            "env": self.env,
        }

    @classmethod
    def from_dict(cls, name: str, data: Dict[str, Any]) -> "MCPServerConfig":
        return cls(
            name=name,
            command=data.get("command", ""),
            args=data.get("args", []),
            env=data.get("env", {}),
            enabled=data.get("enabled", True),
        )


@dataclass
class MCPConfig:
    """MCP 配置"""
    servers: Dict[str, MCPServerConfig] = field(default_factory=dict)
    default_timeout: int = 30000  # ms
    max_retries: int = 3

    def get_server(self, name: str) -> Optional[MCPServerConfig]:
        """获取服务器配置"""
        return self.servers.get(name)

    def list_servers(self) -> List[str]:
        """列出所有服务器"""
        return list(self.servers.keys())

    def add_server(self, config: MCPServerConfig) -> None:
        """添加服务器"""
        self.servers[config.name] = config

    def remove_server(self, name: str) -> bool:
        """移除服务器"""
        if name in self.servers:
            del self.servers[name]
            return True
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mcpServers": {
                name: config.to_dict()
                for name, config in self.servers.items()
            },
            "settings": {
                "defaultTimeout": self.default_timeout,
                "maxRetries": self.max_retries,
            },
        }


# 默认 MCP 配置 - 独立项目可用的 MCP Servers
DEFAULT_MCP_CONFIG = MCPConfig(
    servers={
        # 文件系统操作
        "filesystem": MCPServerConfig(
            name="filesystem",
            command="npx",
            args=[
                "-y",
                "@modelcontextprotocol/server-filesystem",
                "/tmp",
            ],
            env={},
        ),
        # 时间工具
        "time": MCPServerConfig(
            name="time",
            command="uvx",
            args=["mcp-server-time"],
            env={},
        ),
        # 内存/知识存储
        "memory": MCPServerConfig(
            name="memory",
            command="npx",
            args=["-y", "@modelcontextprotocol/server-memory"],
            env={},
        ),
        # SQLite 数据库
        "sqlite": MCPServerConfig(
            name="sqlite",
            command="uvx",
            args=["mcp-server-sqlite", "--db-path", "/tmp/mcp.db"],
            env={},
        ),
    },
    default_timeout=30000,
    max_retries=3,
)


def load_mcp_config(config_path: Optional[str] = None) -> MCPConfig:
    """
    加载 MCP 配置

    Args:
        config_path: 配置文件路径，默认为项目根目录的 .mcp.json

    Returns:
        MCPConfig
    """
    if config_path is None:
        # 查找配置文件
        candidates = [
            ".mcp.json",
            "mcp.json",
            "config/mcp.json",
        ]
        for candidate in candidates:
            if os.path.exists(candidate):
                config_path = candidate
                break

    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)

            config = MCPConfig()

            # 解析服务器配置
            servers_data = data.get("mcpServers", {})
            for name, server_data in servers_data.items():
                server_config = MCPServerConfig.from_dict(name, server_data)
                config.servers[name] = server_config

            # 解析设置
            settings = data.get("settings", {})
            config.default_timeout = settings.get("defaultTimeout", 30000)
            config.max_retries = settings.get("maxRetries", 3)

            return config

        except Exception as e:
            print(f"Warning: Failed to load MCP config from {config_path}: {e}")

    # 返回默认配置
    return DEFAULT_MCP_CONFIG


def save_mcp_config(config: MCPConfig, config_path: str = ".mcp.json") -> None:
    """保存 MCP 配置"""
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)
