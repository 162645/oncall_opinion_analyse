# Oncall 运维 Skills 索引

> 本项目推荐使用的 TTADK Skills 清单

## 核心 Skills (必装)

### 监控告警

| Skill | 调用方式 | 用途 |
|-------|---------|------|
| argos-alarm | `/argos-alarm` | 管理告警规则 |
| metrics | `/metrics` | 查询监控指标 |
| trace-query | `/trace-query` | 链路追踪 |

### 日志查询

| Skill | 调用方式 | 用途 |
|-------|---------|------|
| argos-query | `/argos-query` | 搜索服务日志 |
| diag | `/diag` | Diag Notebook 诊断 |

### 数据查询

| Skill | 调用方式 | 用途 |
|-------|---------|------|
| redis | `/redis` | 查询 Redis 缓存 |
| rds | `/rds` | 执行 SQL 查询 |

### 配置管理

| Skill | 调用方式 | 用途 |
|-------|---------|------|
| tcc-query | `/tcc-query` | 查询 TCC 配置 |
| neptune-stability | `/neptune-stability` | 查询 RPC 超时配置 |

## 使用示例

```bash
# 查询告警规则
gdpa-cli run argos-alarm --action list --psm oncall_opinion_analyse

# 查询监控指标
gdpa-cli run metrics --psm oncall_opinion_analyse --metric latency

# 查询日志
gdpa-cli run argos-query --psm oncall_opinion_analyse --keyword "error" --time_range 1h

# 链路追踪
gdpa-cli run trace-query --trace_id xxx

# 查询 Redis
gdpa-cli run redis --key "oncall:*" --command KEYS

# 查询数据库
gdpa-cli run rds --sql "SELECT * FROM alerts LIMIT 10"

# 查询配置
gdpa-cli run tcc-query --psm oncall_opinion_analyse --key "timeout"
```

## Skill 分类

```
运维 Skills
├── 监控层
│   ├── argos-alarm (告警)
│   ├── metrics (指标)
│   └── trace-query (链路)
│
├── 日志层
│   ├── argos-query (日志)
│   └── diag (诊断)
│
├── 数据层
│   ├── redis (缓存)
│   └── rds (数据库)
│
└── 配置层
    ├── tcc-query (配置查询)
    └── neptune-stability (超时配置)
```
