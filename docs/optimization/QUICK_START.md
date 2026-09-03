# gRPC 优化快速启动指南

> Go <-> Python 高性能通信

---

## 一、快速启动

### 1. 生成 Proto 代码

```bash
# 安装 protoc (如果未安装)
# macOS:
brew install protobuf

# 安装 Go protoc 插件
go install google.golang.org/protobuf/cmd/protoc-gen-go@latest
go install google.golang.org/grpc/cmd/protoc-gen-go-grpc@latest

# 安装 Python gRPC 工具
pip install grpcio-tools

# 生成代码
./scripts/generate_proto.sh
```

### 2. 启动服务

```bash
cd docker

# 开发模式 (仅 Python 服务)
docker-compose up python-service

# 完整模式 (Go + Python)
docker-compose up go-service python-service

# 监控模式 (含 Prometheus + Grafana)
docker-compose --profile monitoring up
```

### 3. 测试验证

```bash
# HTTP 测试 (兼容旧版)
curl -X POST http://localhost:8000/api/chat/send \
  -H "Content-Type: application/json" \
  -d '{"query": "网络延迟诊断", "mode": "sequential"}'

# gRPC 测试 (推荐)
# 安装 ghz: go install github.com/bojand/ghz/cmd/ghz@latest
ghz --insecure \
  --proto ../proto/agent.proto \
  --call agent.AgentService.Diagnose \
  -d '{"query":"网络延迟诊断","mode":"sequential"}' \
  -n 100 -c 10 \
  localhost:50051

# 健康检查
grpcurl -plaintext localhost:50051 agent.AgentService/HealthCheck
```

---

## 二、服务架构

```
┌──────────────────────────────────────────────────────────────┐
│                        Docker Network                         │
│  ┌─────────────────┐         ┌─────────────────────────────┐ │
│  │   go-service    │  gRPC   │     python-service          │ │
│  │   Port: 8080    │ ──────→ │     HTTP: 8000              │ │
│  │                 │  :50051 │     gRPC: 50051             │ │
│  └─────────────────┘         └─────────────────────────────┘ │
│           │                              │                    │
│           │         ┌────────────────────┼────────────────┐  │
│           │         │                    │                │  │
│  ┌────────▼─────────▼────────────────────▼────────────────┐ │
│  │                    数据层                               │ │
│  │  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────┐  │ │
│  │  │ Qdrant  │ │  Redis  │ │ Neo4j   │ │   MinIO     │  │ │
│  │  │ :6333   │ │  :6379  │ │ :7687   │ │   :9000     │  │ │
│  │  └─────────┘ └─────────┘ └─────────┘ └─────────────┘  │ │
│  └────────────────────────────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────┘
```

---

## 三、配置说明

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `GRPC_PYTHON_ADDRESS` | `localhost:50051` | Python gRPC 服务地址 |
| `HTTP_PORT` | `8000` | HTTP 服务端口 |
| `GRPC_PORT` | `50051` | gRPC 服务端口 |
| `OPENAI_API_KEY` | - | OpenAI API Key |
| `QDRANT_URL` | `http://qdrant:6333` | Qdrant 地址 |

### 模式选择

```bash
# 双模式 (HTTP + gRPC) - 推荐
python -m src.grpc.server --mode dual

# 仅 HTTP
python -m src.grpc.server --mode http

# 仅 gRPC
python -m src.grpc.server --mode grpc
```

---

## 四、性能对比

### 测试环境
- CPU: Apple M1
- Memory: 16GB
- Requests: 1000
- Concurrency: 10

### 预期结果

| 指标 | HTTP | gRPC | 提升 |
|------|------|------|------|
| 平均延迟 | ~150ms | ~100ms | 33% ↓ |
| P99 延迟 | ~300ms | ~180ms | 40% ↓ |
| 吞吐量 | ~500 QPS | ~800 QPS | 60% ↑ |
| 传输体积 | ~5KB | ~1.5KB | 70% ↓ |

---

## 五、故障排查

### 1. Proto 生成失败

```bash
# 检查 protoc 版本
protoc --version  # 需要 3.x+

# 检查插件
which protoc-gen-go
which protoc-gen-go-grpc
```

### 2. gRPC 连接失败

```bash
# 检查服务是否启动
docker-compose ps

# 检查端口
lsof -i :50051

# 查看日志
docker-compose logs python-service
```

### 3. 健康检查失败

```bash
# 进入容器
docker exec -it oncall-python-service bash

# 手动检查
curl http://localhost:8000/health
python -c "from src.grpc.server import *"
```

---

## 六、开发指南

### 添加新的 gRPC 方法

1. 编辑 `proto/agent.proto`，添加新的 RPC 方法和消息定义
2. 运行 `./scripts/generate_proto.sh` 重新生成代码
3. 在 `src/grpc/servicer.py` 中实现新方法
4. 在 `biz/grpc_client/client.go` 中添加调用方法

### 调试技巧

```python
# 启用 gRPC 调试日志
import os
os.environ["GRPC_VERBOSITY"] = "DEBUG"
os.environ["GRPC_TRACE"] = "all"
```

```go
// Go 客户端启用调试
import "google.golang.org/grpc/grpclog"
grpclog.SetLoggerV2(grpclog.NewLoggerV2(os.Stdout, os.Stderr, os.Stderr))
```

---

## 七、回滚方案

如果 gRPC 出现问题，可快速回滚到 HTTP：

```go
// Go 客户端配置
type ClientConfig struct {
    UseGRPC bool `env:"USE_GRPC" default:"true"`
}

func NewClient(cfg *ClientConfig) AIClient {
    if cfg.UseGRPC {
        return NewGRPCClient()
    }
    return NewHTTPClient()
}
```

```yaml
# docker-compose.yml
services:
  python-service:
    environment:
      - GRPC_ENABLED=false  # 回滚到仅 HTTP
```
