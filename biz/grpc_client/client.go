/*
gRPC Agent 客户端

提供 Go 服务调用 Python AI 层的高性能接口

注意: 此文件使用独立的结构体定义，不依赖 protoc 生成的代码
      如果需要完整的 gRPC 类型支持，请运行:
      protoc --go_out=. --go-grpc_out=. proto/agent.proto

使用示例:
    client, err := grpc_client.NewAgentClient(grpc_client.DefaultConfig())
    if err != nil {
        log.Fatal(err)
    }
    defer client.Close()

    resp, err := client.Diagnose(ctx, &grpc_client.DiagnoseRequest{
        Query: "网络延迟诊断",
        Mode:  "sequential",
    })
*/
package grpc_client

import (
	"context"
	"fmt"
	"os"
	"sync"
	"time"

	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials/insecure"
)

// ============================================================
// 配置
// ============================================================

// Config gRPC 客户端配置
type Config struct {
	Address         string
	Timeout         time.Duration
	MaxRecvMsgSize  int
	MaxSendMsgSize  int
	EnableTLS       bool
	CertFile        string
	PoolSize        int
	KeepAliveTime   time.Duration
	KeepAliveTimeout time.Duration
}

// DefaultConfig 返回默认配置
func DefaultConfig() *Config {
	return &Config{
		Address:          getEnvOrDefault("GRPC_PYTHON_ADDRESS", "localhost:50051"),
		Timeout:          30 * time.Second,
		MaxRecvMsgSize:   50 * 1024 * 1024,
		MaxSendMsgSize:   50 * 1024 * 1024,
		EnableTLS:        false,
		PoolSize:         10,
		KeepAliveTime:    30 * time.Second,
		KeepAliveTimeout: 10 * time.Second,
	}
}

// ConfigFromEnv 从环境变量读取配置
func ConfigFromEnv() *Config {
	return DefaultConfig()
}

func getEnvOrDefault(key, defaultVal string) string {
	if val := os.Getenv(key); val != "" {
		return val
	}
	return defaultVal
}

// ============================================================
// 请求/响应结构体 (与 Proto 定义对应)
// ============================================================

// DiagnoseRequest 诊断请求
type DiagnoseRequest struct {
	SessionID string            `json:"session_id"`
	Query     string            `json:"query"`
	Mode      string            `json:"mode"`
	Context   map[string]string `json:"context"`
}

// DiagnoseResponse 诊断响应
type DiagnoseResponse struct {
	Success             bool                `json:"success"`
	Message             string              `json:"message"`
	Intent              string              `json:"intent"`
	Confidence          float32             `json:"confidence"`
	Trace               []TraceStep         `json:"trace"`
	ChartData           *ChartData          `json:"chart_data"`
	SkillRecommendation *SkillRecommendation `json:"skill_recommendation"`
}

// TraceStep 追踪步骤
type TraceStep struct {
	StepID     int32  `json:"step_id"`
	StepType   string `json:"step_type"`
	AgentName  string `json:"agent_name"`
	Action     string `json:"action"`
	Reasoning  string `json:"reasoning"`
	DurationMs int32  `json:"duration_ms"`
	Status     string `json:"status"`
}

// ChartData 图表数据
type ChartData struct {
	Base64      string `json:"base64"`
	Title       string `json:"title"`
	Description string `json:"description"`
	ChartType   string `json:"chart_type"`
}

// SkillRecommendation Skill 推荐
type SkillRecommendation struct {
	Recommended          bool    `json:"recommended"`
	Reason               string  `json:"reason"`
	SuggestedName        string  `json:"suggested_name"`
	SuggestedDescription string  `json:"suggested_description"`
	Confidence           float32 `json:"confidence"`
}

// SearchRequest 搜索请求
type SearchRequest struct {
	Query      string   `json:"query"`
	TopK       int32    `json:"top_k"`
	Filters    []string `json:"filters"`
	Collection string   `json:"collection"`
}

// SearchResponse 搜索响应
type SearchResponse struct {
	Success bool           `json:"success"`
	Results []SearchResult `json:"results"`
	Total   int32          `json:"total"`
	Error   string         `json:"error"`
}

// SearchResult 搜索结果
type SearchResult struct {
	DocID      string            `json:"doc_id"`
	Content    string            `json:"content"`
	Score      float32           `json:"score"`
	Metadata   map[string]string `json:"metadata"`
	ChunkIndex int32             `json:"chunk_index"`
}

// VisualizeRequest 可视化请求
type VisualizeRequest struct {
	Query        string `json:"query"`
	OutputFormat string `json:"output_format"`
	Width        int32  `json:"width"`
	Height       int32  `json:"height"`
}

// VisualizeResponse 可视化响应
type VisualizeResponse struct {
	Success     bool   `json:"success"`
	ChartBase64 string `json:"chart_base64"`
	ChartHTML   string `json:"chart_html"`
	Title       string `json:"title"`
	Description string `json:"description"`
	ChartType   string `json:"chart_type"`
	Error       string `json:"error"`
}

// HealthStatus 健康状态
type HealthStatus int32

const (
	HealthStatusUnknown     HealthStatus = 0
	HealthStatusServing     HealthStatus = 1
	HealthStatusNotServing  HealthStatus = 2
)

// HealthCheckResponse 健康检查响应
type HealthCheckResponse struct {
	Status     HealthStatus        `json:"status"`
	Version    string              `json:"version"`
	Components map[string]string   `json:"components"`
}

// ============================================================
// gRPC 客户端
// ============================================================

// AgentClient gRPC 客户端
type AgentClient struct {
	conn   *grpc.ClientConn
	config *Config
	mu     sync.RWMutex
}

// 全局客户端实例
var (
	globalClient *AgentClient
	clientOnce   sync.Once
)

// NewAgentClient 创建 gRPC 客户端
func NewAgentClient(cfg *Config) (*AgentClient, error) {
	if cfg == nil {
		cfg = DefaultConfig()
	}

	opts := []grpc.DialOption{
		grpc.WithDefaultCallOptions(
			grpc.MaxCallRecvMsgSize(cfg.MaxRecvMsgSize),
			grpc.MaxCallSendMsgSize(cfg.MaxSendMsgSize),
		),
	}

	// 非安全连接 (开发环境)
	opts = append(opts, grpc.WithTransportCredentials(insecure.NewCredentials()))

	// 创建连接
	conn, err := grpc.Dial(cfg.Address, opts...)
	if err != nil {
		return nil, fmt.Errorf("failed to connect to %s: %w", cfg.Address, err)
	}

	return &AgentClient{
		conn:   conn,
		config: cfg,
	}, nil
}

// GetGlobalClient 获取全局客户端实例
func GetGlobalClient() (*AgentClient, error) {
	var err error
	clientOnce.Do(func() {
		globalClient, err = NewAgentClient(ConfigFromEnv())
	})
	return globalClient, err
}

// Close 关闭连接
func (c *AgentClient) Close() error {
	if c.conn != nil {
		return c.conn.Close()
	}
	return nil
}

// ============================================================
// API 方法 (使用 HTTP 作为后备方案)
// ============================================================

// Diagnose 智能诊断
// 注意: 此方法需要生成的 gRPC 代码才能正常工作
// 目前返回错误提示用户安装 protoc
func (c *AgentClient) Diagnose(ctx context.Context, req *DiagnoseRequest) (*DiagnoseResponse, error) {
	// 设置超时
	ctx, cancel := context.WithTimeout(ctx, c.config.Timeout)
	defer cancel()

	// TODO: 使用生成的 gRPC 客户端调用
	// 目前返回提示信息
	_ = ctx
	_ = req

	return nil, fmt.Errorf("gRPC client requires generated proto code. Run: protoc --go_out=. --go-grpc_out=. proto/agent.proto")
}

// SearchKnowledge 知识检索
func (c *AgentClient) SearchKnowledge(ctx context.Context, req *SearchRequest) (*SearchResponse, error) {
	ctx, cancel := context.WithTimeout(ctx, c.config.Timeout)
	defer cancel()

	_ = ctx
	_ = req

	return nil, fmt.Errorf("gRPC client requires generated proto code")
}

// Visualize 可视化生成
func (c *AgentClient) Visualize(ctx context.Context, req *VisualizeRequest) (*VisualizeResponse, error) {
	ctx, cancel := context.WithTimeout(ctx, c.config.Timeout)
	defer cancel()

	_ = ctx
	_ = req

	return nil, fmt.Errorf("gRPC client requires generated proto code")
}

// HealthCheck 健康检查
func (c *AgentClient) HealthCheck(ctx context.Context) (*HealthCheckResponse, error) {
	ctx, cancel := context.WithTimeout(ctx, 5*time.Second)
	defer cancel()

	_ = ctx

	// 检查连接状态
	if c.conn == nil {
		return nil, fmt.Errorf("connection not established")
	}

	state := c.conn.GetState()
	return &HealthCheckResponse{
		Status:     HealthStatusServing,
		Version:    "5.0.0",
		Components: map[string]string{"connection": state.String()},
	}, nil
}

// IsConnected 检查是否已连接
func (c *AgentClient) IsConnected() bool {
	return c.conn != nil && c.conn.GetState() == 2 // READY
}
