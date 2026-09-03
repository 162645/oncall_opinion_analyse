# 一键部署指南

> 快速部署 Oncall Opinion Analyse 到服务器

---

## 一、服务器要求

### 1.1 最低配置

| 资源 | 要求 |
|------|------|
| CPU | 2 核 |
| 内存 | 4 GB |
| 磁盘 | 20 GB |
| 系统 | Ubuntu 20.04+ / CentOS 7+ |

### 1.2 软件要求

| 软件 | 版本 |
|------|------|
| Docker | >= 20.10 |
| Docker Compose | >= 2.0 |
| Git | latest |

---

## 二、一键部署

### 2.1 克隆项目

```bash
git clone <your-repo-url>
cd oncall_opinion_analyse
```

### 2.2 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置 (必须填写 API Keys)
vim .env
```

**必须配置的项目:**
- `OPENAI_API_KEY` - OpenAI API Key
- `ANTHROPIC_API_KEY` - Claude API Key (可选)

### 2.3 启动服务

```bash
# 一键启动
./scripts/deploy.sh start
```

### 2.4 验证部署

```bash
# 检查服务状态
./scripts/deploy.sh status

# 健康检查
./scripts/deploy.sh health

# 查看日志
./scripts/deploy.sh logs
```

---

## 三、访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| 前端界面 | http://localhost:5173 | React Web 应用 |
| API 文档 | http://localhost:8000/docs | Swagger UI |
| gRPC 服务 | localhost:50051 | gRPC 端口 |
| Qdrant 控制台 | http://localhost:6333/dashboard | 向量数据库 |
| MinIO 控制台 | http://localhost:9001 | 对象存储 |

---

## 四、常用命令

```bash
# 启动服务
./scripts/deploy.sh start

# 停止服务
./scripts/deploy.sh stop

# 重启服务
./scripts/deploy.sh restart

# 查看状态
./scripts/deploy.sh status

# 查看日志
./scripts/deploy.sh logs python-service

# 健康检查
./scripts/deploy.sh health

# 本地开发
./scripts/deploy.sh dev
```

---

## 五、手动部署

如果不想使用一键脚本，可以手动部署：

### 5.1 启动数据库

```bash
cd docker
docker-compose up -d qdrant redis minio neo4j
```

### 5.2 启动后端

```bash
# 方式一: Docker
docker-compose up -d python-service

# 方式二: 直接运行
pip install -r requirements.txt
uvicorn src.api.main:app --host 0.0.0.0 --port 8000
```

### 5.3 启动前端

```bash
cd frontend
npm install
npm run build
# 使用 nginx 托管静态文件
```

---

## 六、生产环境配置

### 6.1 Nginx 配置

项目已包含 `docker/nginx.conf`，可直接使用：

```nginx
# 主要配置
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
    }

    # API 代理
    location /api/ {
        proxy_pass http://python-service:8000;
        proxy_set_header Host $host;
    }
}
```

### 6.2 HTTPS 配置

```bash
# 使用 Let's Encrypt
certbot --nginx -d your-domain.com
```

### 6.3 数据持久化

Docker Compose 已配置数据卷：
- `qdrant-data` - 向量数据
- `redis-data` - 缓存数据
- `minio-data` - 文件存储
- `knowledge-data` - 知识库数据

---

## 七、监控与日志

### 7.1 日志位置

```bash
# 容器日志
docker logs oncall-python-service

# 应用日志 (如果配置了文件日志)
tail -f /var/log/oncall/app.log
```

### 7.2 监控指标

访问以下端点获取监控数据：
- `/health` - 健康检查
- `/api/agent/status` - Agent 状态
- `/api/llm/costs` - LLM 成本统计
- `/api/skills/stats/overview` - Skill 统计

---

## 八、故障排查

### 8.1 服务无法启动

```bash
# 检查端口占用
netstat -tlnp | grep 8000

# 检查容器日志
docker logs oncall-python-service

# 检查环境变量
docker exec oncall-python-service env | grep API
```

### 8.2 API 调用失败

```bash
# 测试 API 连通性
curl http://localhost:8000/health

# 检查 CORS 配置
curl -H "Origin: http://localhost:5173" \
     -H "Access-Control-Request-Method: POST" \
     -X OPTIONS http://localhost:8000/api/chat/send
```

### 8.3 数据库连接失败

```bash
# 检查 Qdrant
curl http://localhost:6333/health

# 检查 Redis
docker exec oncall-redis redis-cli ping

# 检查网络
docker network inspect oncall-network
```

---

## 九、更新部署

```bash
# 拉取最新代码
git pull

# 重新构建并启动
docker-compose -f docker/docker-compose.yml up -d --build python-service

# 清理旧镜像
docker image prune -f
```

---

## 十、备份与恢复

### 10.1 备份数据

```bash
# 备份 Qdrant 数据
docker exec oncall-qdrant tar -czf /tmp/backup.tar.gz /qdrant/storage
docker cp oncall-qdrant:/tmp/backup.tar.gz ./backup/

# 备份 Redis 数据
docker exec oncall-redis redis-cli BGSAVE
docker cp oncall-redis:/data/dump.rdb ./backup/
```

### 10.2 恢复数据

```bash
# 恢复 Qdrant
docker cp ./backup/backup.tar.gz oncall-qdrant:/tmp/
docker exec oncall-qdrant tar -xzf /tmp/backup.tar.gz -C /

# 恢复 Redis
docker cp ./backup/dump.rdb oncall-redis:/data/
docker restart oncall-redis
```

---

## 十一、安全建议

1. **API Keys**: 不要将 `.env` 文件提交到 Git
2. **网络隔离**: 使用 Docker 内部网络
3. **访问控制**: 配置防火墙规则
4. **HTTPS**: 生产环境必须使用 HTTPS
5. **定期备份**: 设置自动备份任务

---

## 十二、联系方式

如有问题，请提交 Issue 或联系维护团队。
