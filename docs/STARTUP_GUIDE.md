# 项目启动指南

> 快速启动 Oncall Opinion Analyse 项目

---

## 一、环境要求

### 1.1 后端 (Python)

| 依赖 | 版本 |
|------|------|
| Python | >= 3.9 |
| pip | latest |

### 1.2 前端 (Node.js)

| 依赖 | 版本 |
|------|------|
| Node.js | >= 18.0 |
| npm | >= 9.0 |

### 1.3 数据库 (可选)

| 服务 | 用途 |
|------|------|
| Qdrant | 向量数据库 |
| Redis | 缓存 |
| Neo4j | 知识图谱 |

---

## 二、快速启动

### 2.1 后端启动

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 启动 HTTP 服务 (端口 8000)
uvicorn src.api.main:app --reload --port 8000

# 3. 或启动双模式服务 (HTTP + gRPC)
python -m src.grpc_service.server --mode dual
```

**验证后端:**
```bash
curl http://localhost:8000/health
# 返回: {"success": true, "status": "healthy"}
```

### 2.2 前端启动

```bash
# 1. 进入前端目录
cd frontend

# 2. 安装依赖
npm install

# 3. 启动开发服务器
npm run dev
```

**访问前端:**
```
http://localhost:5173
```

---

## 三、功能验证清单

### 3.1 后端 API 验证

```bash
# 健康检查
curl http://localhost:8000/health

# 知识检索
curl -X POST http://localhost:8000/api/knowledge/search \
  -H "Content-Type: application/json" \
  -d '{"query": "网络延迟"}'

# 智能诊断
curl -X POST http://localhost:8000/api/chat/send \
  -H "Content-Type: application/json" \
  -d '{"query": "新加坡区域网络延迟突增", "mode": "sequential"}'

# Skill 列表
curl http://localhost:8000/api/skills/
```

### 3.2 前端页面验证

| 页面 | 路径 | 功能 |
|------|------|------|
| 首页 | `/home` | 系统概览 |
| 知识库 | `/knowledge` | 文档管理、检索 |
| 智能对话 | `/chat` | Agent 诊断、多模式协作 |
| Skill 管理 | `/skills` | 创建、执行、管理 Skill |
| 可视化 | `/visualization` | 图表生成 |
| 设置 | `/settings` | 系统配置 |

### 3.3 gRPC 验证

```bash
# 启动 gRPC 服务
python -m src.grpc_service.server --mode grpc --grpc-port 50051

# 运行测试
python3 tests/test_full_chain.py
```

---

## 四、Docker 部署

### 4.1 单服务部署

```bash
# Python 服务
cd docker
docker-compose up python-service

# Go 服务 (可选)
docker-compose up go-service
```

### 4.2 完整部署

```bash
cd docker

# 启动所有服务
docker-compose up -d

# 查看日志
docker-compose logs -f python-service
```

### 4.3 访问地址

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:5173 |
| HTTP API | http://localhost:8000 |
| gRPC | localhost:50051 |
| Qdrant | http://localhost:6333 |
| Redis | localhost:6379 |
| MinIO Console | http://localhost:9001 |

---

## 五、常见问题

### Q1: 模块导入失败

```bash
# 确保 PYTHONPATH 正确
export PYTHONPATH="${PYTHONPATH}:$(pwd)"

# 或使用 -m 运行
python -m uvicorn src.api.main:app --reload
```

### Q2: 前端无法连接后端

```bash
# 检查后端是否启动
curl http://localhost:8000/health

# 检查 CORS 配置 (已在 main.py 中配置)
```

### Q3: gRPC 启动失败

```bash
# 确保 grpcio 已安装
pip install grpcio grpcio-tools

# 重新生成 proto 文件
python3 -m grpc_tools.protoc -I./proto \
  --python_out=./proto_gen/python \
  --grpc_python_out=./proto_gen/python \
  proto/agent.proto
```

### Q4: 数据库连接失败

```bash
# 使用 Docker 启动数据库
cd docker
docker-compose up -d qdrant redis

# 或配置环境变量
export QDRANT_URL=http://localhost:6333
export REDIS_URL=redis://localhost:6379
```

---

## 六、开发调试

### 6.1 开启调试日志

```bash
# Python
export LOG_LEVEL=DEBUG
uvicorn src.api.main:app --reload --log-level debug
```

### 6.2 前端热重载

```bash
cd frontend
npm run dev  # 自动热重载
```

### 6.3 运行测试

```bash
# 全链路测试
python3 tests/test_full_chain.py

# gRPC 测试
python3 tests/grpc_test/test_grpc_server.py
```

---

## 七、配置说明

### 7.1 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `OPENAI_API_KEY` | - | OpenAI API Key |
| `ANTHROPIC_API_KEY` | - | Claude API Key |
| `QDRANT_URL` | http://localhost:6333 | Qdrant 地址 |
| `REDIS_URL` | redis://localhost:6379 | Redis 地址 |
| `GRPC_PYTHON_ADDRESS` | localhost:50051 | gRPC 服务地址 |

### 7.2 配置文件

- 后端配置: `src/core/config.py`
- 前端配置: `frontend/vite.config.ts`
- Docker 配置: `docker/docker-compose.yml`

---

## 八、生产部署

### 8.1 构建

```bash
# 后端
pip install -r requirements.txt

# 前端
cd frontend && npm run build

# Docker
docker build -f docker/Dockerfile.python -t oncall-python .
docker build -f docker/Dockerfile.go -t oncall-go .
```

### 8.2 部署检查清单

- [ ] 环境变量配置正确
- [ ] API Keys 已设置
- [ ] 数据库连接正常
- [ ] 前端构建成功
- [ ] Docker 容器健康
- [ ] 日志收集配置
- [ ] 监控告警配置
