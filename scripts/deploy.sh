#!/bin/bash
# 一键部署脚本
# 用法: ./scripts/deploy.sh [start|stop|restart|status|logs]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 打印函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查依赖
check_dependencies() {
    log_info "检查依赖..."

    # 检查 Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi

    # 检查 Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi

    log_info "依赖检查通过"
}

# 初始化环境
init_env() {
    if [ ! -f ".env" ]; then
        log_info "初始化环境变量..."
        cp .env.example .env
        log_warn "请编辑 .env 文件，填写实际的 API Keys"
    fi
}

# 启动服务
start() {
    log_info "启动服务..."

    check_dependencies
    init_env

    # 创建网络
    docker network create oncall-network 2>/dev/null || true

    # 启动基础服务
    log_info "启动数据库服务..."
    docker-compose -f docker/docker-compose.yml up -d qdrant redis minio neo4j

    sleep 5

    # 启动应用服务
    log_info "启动应用服务..."
    docker-compose -f docker/docker-compose.yml up -d python-service toolbox

    # 等待服务就绪
    log_info "等待服务就绪..."
    sleep 10

    # 健康检查
    check_health

    log_info "服务启动完成!"
    echo ""
    echo "访问地址:"
    echo "  前端:     http://localhost:5173"
    echo "  API 文档: http://localhost:8000/docs"
    echo "  Qdrant:   http://localhost:6333/dashboard"
    echo "  MinIO:    http://localhost:9001"
}

# 停止服务
stop() {
    log_info "停止服务..."
    docker-compose -f docker/docker-compose.yml down
    log_info "服务已停止"
}

# 重启服务
restart() {
    stop
    sleep 3
    start
}

# 查看状态
status() {
    echo "服务状态:"
    docker-compose -f docker/docker-compose.yml ps
}

# 查看日志
logs() {
    local service=$1
    if [ -z "$service" ]; then
        docker-compose -f docker/docker-compose.yml logs -f --tail=100
    else
        docker-compose -f docker/docker-compose.yml logs -f --tail=100 "$service"
    fi
}

# 健康检查
check_health() {
    log_info "健康检查..."

    # 检查 Python 服务
    local max_retries=30
    local retry=0
    while [ $retry -lt $max_retries ]; do
        if curl -s http://localhost:8000/health > /dev/null 2>&1; then
            log_info "Python 服务: 健康"
            break
        fi
        retry=$((retry + 1))
        sleep 2
    done

    if [ $retry -eq $max_retries ]; then
        log_warn "Python 服务: 未就绪"
    fi

    # 检查 Qdrant
    if curl -s http://localhost:6333/health > /dev/null 2>&1; then
        log_info "Qdrant: 健康"
    else
        log_warn "Qdrant: 未就绪"
    fi

    # 检查 Redis
    if docker exec oncall-redis redis-cli ping > /dev/null 2>&1; then
        log_info "Redis: 健康"
    else
        log_warn "Redis: 未就绪"
    fi

    # 检查 MinIO
    if curl -s http://localhost:9000/minio/health/live > /dev/null 2>&1; then
        log_info "MinIO: 健康"
    else
        log_warn "MinIO: 未就绪"
    fi

    # 检查 Neo4j
    if curl -s http://localhost:7474 > /dev/null 2>&1; then
        log_info "Neo4j: 健康"
    else
        log_warn "Neo4j: 未就绪"
    fi

    # 检查 Toolbox
    if curl -s http://localhost:5000/health > /dev/null 2>&1; then
        log_info "MCP Toolbox: 健康"
    else
        log_warn "MCP Toolbox: 未就绪"
    fi
}

# 本地开发启动
dev() {
    log_info "启动本地开发环境..."

    # 检查 Python
    if ! command -v python3 &> /dev/null; then
        log_error "Python3 未安装"
        exit 1
    fi

    # 安装依赖
    if [ ! -d "venv" ]; then
        log_info "创建虚拟环境..."
        python3 -m venv venv
    fi

    source venv/bin/activate

    log_info "安装 Python 依赖..."
    pip install -r requirements.txt -q

    # 启动后端
    log_info "启动后端服务..."
    uvicorn src.api.main:app --reload --port 8000 &
    BACKEND_PID=$!

    # 检查前端
    if [ -d "frontend/node_modules" ]; then
        log_info "启动前端服务..."
        cd frontend && npm run dev &
        FRONTEND_PID=$!
        cd ..
    else
        log_warn "前端依赖未安装，请运行: cd frontend && npm install"
    fi

    echo ""
    echo "开发服务已启动:"
    echo "  后端 PID: $BACKEND_PID"
    echo "  前端 PID: $FRONTEND_PID"
    echo ""
    echo "访问地址:"
    echo "  前端: http://localhost:5173"
    echo "  后端: http://localhost:8000/docs"
}

# 显示帮助
show_help() {
    echo "用法: $0 {start|stop|restart|status|logs|dev|health}"
    echo ""
    echo "命令:"
    echo "  start   - 启动所有服务 (Docker)"
    echo "  stop    - 停止所有服务"
    echo "  restart - 重启所有服务"
    echo "  status  - 查看服务状态"
    echo "  logs    - 查看日志 (可选: logs python-service)"
    echo "  dev     - 启动本地开发环境"
    echo "  health  - 健康检查"
}

# 主入口
case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs "$2"
        ;;
    dev)
        dev
        ;;
    health)
        check_health
        ;;
    *)
        show_help
        exit 1
        ;;
esac
