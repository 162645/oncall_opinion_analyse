#!/bin/bash
# gRPC 代码生成脚本
#
# 生成 Go 和 Python 的 gRPC 代码

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

echo "============================================"
echo "gRPC 代码生成"
echo "============================================"

# 创建目录
mkdir -p "$PROJECT_ROOT/proto_gen/go/agent"
mkdir -p "$PROJECT_ROOT/proto_gen/python"

# 检查 protoc 是否安装
if ! command -v protoc &> /dev/null; then
    echo "❌ protoc not found. Please install:"
    echo "   macOS: brew install protobuf"
    echo "   Linux: apt install protobuf-compiler"
    exit 1
fi

echo "✅ protoc version: $(protoc --version)"

# 生成 Go 代码
echo ""
echo "📦 Generating Go code..."
protoc \
    --proto_path="$PROJECT_ROOT/proto" \
    --go_out="$PROJECT_ROOT/proto_gen/go" \
    --go_opt=paths=source_relative \
    --go-grpc_out="$PROJECT_ROOT/proto_gen/go" \
    --go-grpc_opt=paths=source_relative \
    "$PROJECT_ROOT/proto/agent.proto"

echo "✅ Go code generated: proto_gen/go/agent/"

# 生成 Python 代码
echo ""
echo "📦 Generating Python code..."
python3 -m grpc_tools.protoc \
    -I"$PROJECT_ROOT/proto" \
    --python_out="$PROJECT_ROOT/proto_gen/python" \
    --grpc_python_out="$PROJECT_ROOT/proto_gen/python" \
    "$PROJECT_ROOT/proto/agent.proto"

# 添加 __init__.py
touch "$PROJECT_ROOT/proto_gen/python/__init__.py"

echo "✅ Python code generated: proto_gen/python/"

# 创建 Go 包初始化文件
cat > "$PROJECT_ROOT/proto_gen/go/agent/__init__.py" << 'EOF'
# Generated gRPC code for Go
EOF

echo ""
echo "============================================"
echo "✅ gRPC code generation completed!"
echo "============================================"
echo ""
echo "Generated files:"
echo "  - proto_gen/go/agent/agent.pb.go"
echo "  - proto_gen/go/agent/agent_grpc.pb.go"
echo "  - proto_gen/python/agent_pb2.py"
echo "  - proto_gen/python/agent_pb2_grpc.py"
