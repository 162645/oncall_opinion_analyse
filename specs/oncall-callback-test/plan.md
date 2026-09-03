# Implementation Plan: Oncall Callback Handler

## 1. 技术方案

### 1.1 架构设计

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Oncall API    │────▶│  Callback API   │────▶│   Database      │
│   Argos Alert   │     │   (Hertz)       │     │   (MySQL)       │
└─────────────────┘     └─────────────────┘     └─────────────────┘
```

### 1.2 技术栈

| 组件 | 技术 |
|------|------|
| HTTP 框架 | Hertz |
| ORM | GORM |
| 配置中心 | TCC |
| 日志 | logs/v2 |
| 监控 | metrics |

## 2. 实现任务

### Phase 1: 核心功能
- [x] GetOncallCallback - Oncall 工单回调
- [x] GetOncallArgosDIYCardCallback - Argos DIY Card 回调
- [x] HandleAlarmCallback - 告警回调代理
- [x] Ping - 健康检查

### Phase 2: 数据持久化
- [x] OncallOriginRecord 表操作
- [x] AlertTask 表操作

### Phase 3: 监控与日志
- [x] 日志记录
- [x] 监控打点

## 3. 部署信息

| 环境 | PSM |
|------|-----|
| PPE | oec.governance.oncall_opinion_analyse |
| PROD | oec.governance.oncall_opinion_analyse |

## 4. 依赖服务

- MySQL (RDS)
- TCC 配置中心
- 跨区域 RPC 调用
