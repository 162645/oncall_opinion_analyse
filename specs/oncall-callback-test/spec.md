# Feature Specification: Oncall Callback Handler

## 1. 功能概述

Oncall 工单回调处理服务，用于接收和处理来自 Oncall 系统的工单回调、Argos 告警回调等。

## 2. User Stories

### US-001: Oncall 工单回调处理
**作为** Oncall 系统
**我希望** 能够通过 API 回调通知工单状态变更
**以便于** 系统能够自动记录和处理工单信息

**验收标准:**
- 接收 POST 请求 `/api/v:version/oec/oncall/workorder/callback`
- 正确解析 OncallFlow 数据结构
- 返回成功响应 (code: 0)

### US-002: Argos DIY Card 回调处理
**作为** Argos 告警系统
**我希望** 能够通过回调获取自定义告警卡片数据
**以便于** 展示更丰富的告警信息

**验收标准:**
- 接收 POST 请求 `/api/v:version/oec/governance/qa/argos/callback`
- 根据 alertType 构建不同类型的卡片
- 返回包含 tags 和 vars 的响应

### US-003: 告警回调代理
**作为** 告警系统
**我希望** 能够通过代理转发告警回调
**以便于** 实现跨区域告警通知

**验收标准:**
- 接收 POST 请求 `/osgw_v4/api/osgw/wares_alarm/alarm_detail/callback`
- 解析 AlarmData 结构
- 跨区域调用 sg1 区域服务
- 返回处理结果

### US-004: 健康检查
**作为** 运维人员
**我希望** 能够检查服务健康状态
**以便于** 确认服务正常运行

**验收标准:**
- GET `/ping` 返回 `{"message": "pong"}`

## 3. 接口定义

### 3.1 GetOncallCallback

| 项目 | 值 |
|------|-----|
| Method | POST |
| Path | `/api/v:version/oec/oncall/workorder/callback` |
| Content-Type | application/json |

**Request Body:** `OncallWorkOrderCallbackRequest`

**Response:** `OncallWorkOrderCallbackResponse`

### 3.2 GetOncallArgosDIYCardCallback

| 项目 | 值 |
|------|-----|
| Method | POST |
| Path | `/api/v:version/oec/governance/qa/argos/callback` |
| Content-Type | application/json |

**Request Body:** `ArgosTagValsCallBackRequest`

**Response:** `ArgosTagValsCallBackResponse`

### 3.3 HandleAlarmCallback

| 项目 | 值 |
|------|-----|
| Method | POST |
| Path | `/osgw_v4/api/osgw/wares_alarm/alarm_detail/callback` |
| Content-Type | application/json |

**Request Body:** `AlarmCallbackReq`

**Response:** `Response`

### 3.4 Ping

| 项目 | 值 |
|------|-----|
| Method | GET |
| Path | `/ping` |

**Response:** `{"message": "pong"}`

## 4. 数据模型

### OncallFlow
- `id`: int64 - 工单ID
- `tenant_id`: int64 - 租户ID
- `level`: string - 工单级别
- `stage`: string - 工单阶段
- `name`: string - 工单名称
- `source_location`: string - 来源链接
- `create_time`: timestamp - 创建时间
- `is_solved`: bool - 是否已解决

### AlarmData
- `rule_uid`: string - 规则唯一标识
- `rule_name`: string - 规则名称
- `alert_time`: timestamp - 告警时间
- `tags`: []KeyValue - 标签列表
- `vars`: []KeyValue - 变量列表

## 5. 非功能性需求

- 响应时间 < 500ms
- 支持跨区域调用
- 完整的日志记录
- 错误处理和重试机制
