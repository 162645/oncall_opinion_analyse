---
name: network-telemetry
description: 分析 ClickHouse 中的网络测量数据，包括延迟、流量、丢包等指标，支持查询网络异常事件和链路质量
---

# Network Telemetry Skill

通过 MCP Toolbox 连接 ClickHouse，分析网络测量数据。

## 功能说明

本 Skill 提供以下能力：

| Action | 描述 | 使用场景 |
|--------|------|---------|
| `query_latency` | 查询网络延迟 | 分析网络性能、定位延迟问题 |
| `query_anomalies` | 查询异常事件 | 快速定位异常时段和事件 |
| `query_traffic` | 查询流量统计 | 容量分析、异常流量检测 |
| `query_link_quality` | 查询链路质量 | 跨区域链路健康检查 |
| `analyze_trend` | 分析延迟趋势 | 检测异常延迟变化 |

## 使用方式

### 1. 查询网络延迟

```bash
gdpa-cli run network-telemetry --action query_latency \
  --start-time "2025-01-15T00:00:00Z" \
  --end-time "2025-01-15T01:00:00Z" \
  --source-region "Singapore-Central"
```

**参数说明:**
- `start_time`: 开始时间 (ISO 8601 格式)
- `end_time`: 结束时间
- `source_region`: 源区域过滤 (可选)
- `target_region`: 目标区域过滤 (可选)

**返回字段:**
- `timestamp`: 时间戳
- `avg_latency_ms`: 平均延迟 (毫秒)
- `p99_latency_ms`: P99 延迟
- `p95_latency_ms`: P95 延迟
- `packet_loss_rate`: 丢包率
- `throughput_mbps`: 吞吐量

### 2. 查询网络异常事件

```bash
gdpa-cli run network-telemetry --action query_anomalies \
  --time-range-minutes 60 \
  --severity critical
```

**参数说明:**
- `time_range_minutes`: 查询时间范围 (分钟)
- `severity`: 严重级别 (warning/critical)
- `event_type`: 事件类型 (latency_spike/packet_loss/connection_failure/dns_error)
- `region`: 区域过滤

**返回字段:**
- `event_id`: 事件ID
- `event_type`: 事件类型
- `severity`: 严重级别
- `source_region`: 源区域
- `target_region`: 目标区域
- `metric_value`: 指标值
- `threshold`: 阈值

### 3. 查询链路质量

```bash
gdpa-cli run network-telemetry --action query_link_quality \
  --start-time "2025-01-15T00:00:00Z" \
  --end-time "2025-01-15T01:00:00Z" \
  --link-id "Singapore-Central-US-East"
```

**返回字段:**
- `link_id`: 链路ID
- `avg_rtt_ms`: 平均 RTT
- `jitter_ms`: 抖动
- `loss_rate`: 丢包率
- `health_score`: 健康分数 (0-100)
- `status`: 状态 (healthy/degraded/unhealthy)

## 典型场景

### 场景1: 延迟突增诊断

当收到延迟告警时，按以下步骤诊断：

1. 查询最近 30 分钟的延迟数据
2. 对比历史基线，确认异常幅度
3. 查询同时段的异常事件
4. 检查链路质量分数

### 场景2: 跨区域链路问题

当用户反馈跨区域访问慢时：

1. 查询两端区域的延迟数据
2. 检查链路健康分数
3. 查看是否有丢包事件
4. 分析流量统计，确认是否有拥塞

## 数据源

通过 MCP Toolbox 连接 ClickHouse：

```yaml
# v1/config/tools.yaml
source: clickhouse-network
database: network_telemetry
tables:
  - network_latency
  - network_events
  - traffic_stats
  - link_quality
```

## 依赖

- MCP Toolbox (已配置)
- ClickHouse 数据库
- Python 3.9+

## 错误处理

| 错误 | 原因 | 解决方案 |
|------|------|---------|
| Connection refused | ClickHouse 不可达 | 检查网络连接和数据库状态 |
| Authentication failed | 认证信息错误 | 检查 .env 配置 |
| Query timeout | 查询超时 | 缩小时间范围或添加过滤条件 |
