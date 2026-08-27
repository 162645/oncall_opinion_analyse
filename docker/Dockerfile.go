# Go 核心服务 Dockerfile
# 多阶段构建: 构建 -> 运行

# ==================== 构建阶段 ====================
FROM golang:1.21-alpine AS builder

WORKDIR /build

# 安装依赖
RUN apk add --no-cache git make

# 复制 go.mod/go.sum
COPY go.mod go.sum ./
RUN go mod download

# 复制源代码
COPY . .

# 构建
RUN CGO_ENABLED=0 GOOS=linux go build -o /app/server .

# ==================== 运行阶段 ====================
FROM alpine:3.18

WORKDIR /app

# 安装运行时依赖
RUN apk add --no-cache ca-certificates tzdata

# 从构建阶段复制二进制
COPY --from=builder /app/server .

# 复制配置文件
COPY conf/ ./conf/

# 暴露端口
EXPOSE 8080

# 环境变量
ENV TZ=Asia/Shanghai
ENV GRPC_PYTHON_ADDRESS=python-service:50051

# 启动
CMD ["./server"]
