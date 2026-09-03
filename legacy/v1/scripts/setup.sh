#!/bin/bash
# 环境初始化脚本

set -e

echo "=== Oncall Agent Extension 环境初始化 ==="

# 检查 Docker
if ! command -v docker &> /dev/null; then
    echo "错误: Docker 未安装"
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "错误: docker-compose 未安装"
    exit 1
fi

# 检查 .env 文件
if [ ! -f "../config/.env" ]; then
    echo "创建 .env 文件..."
    cp ../config/.env.example ../config/.env
    echo "请编辑 ../config/.env 配置你的环境变量"
fi

# 启动服务
echo "启动 Docker 服务..."
cd ../docker
docker-compose up -d

echo ""
echo "=== 服务状态 ==="
docker-compose ps

echo ""
echo "=== 下一步 ==="
echo "1. 编辑 config/.env 配置数据库连接"
echo "2. 访问 http://localhost:5000 测试 MCP Toolbox"
echo "3. 访问 http://localhost:6333/dashboard 测试 Qdrant"
