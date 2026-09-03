# API 测试用例

## 功能名称
Oncall Callback Handler - Oncall 工单回调处理服务

## PSM
oec.governance.oncall_opinion_analyse

---

## 接口列表

### 接口 1: GetOncallCallback

| 项目 | 值 |
|------|-----|
| 接口名称 | GetOncallCallback |
| 请求方法 | POST |
| URI | `/api/v:version/oec/oncall/workorder/callback` |
| 接口描述 | Oncall 工单回调处理 |

---

### 测试场景 1.1: 正常工单回调处理 [P0]

**Given (前置条件)**
- 服务正常运行
- 请求带有有效的 Content-Type: application/json

**When (操作)**
- 发送 POST 请求到 `/api/v1/oec/oncall/workorder/callback`
- 请求体包含有效的 OncallWorkOrderCallbackRequest 数据

**Then (预期结果)**
- HTTP 状态码为 200
- 响应体中 code 字段为 0 (Success)
- 响应体中 message 字段为成功消息

**测试数据**
```json
{
  "oncall_flow": {
    "id": 123456789,
    "tenant_id": 1001,
    "level": "P0",
    "stage": "in_progress",
    "name": "测试工单",
    "source_location": "https://oncall.bytedance.net/test",
    "create_time": "2026-04-29T10:00:00Z",
    "is_solved": false
  },
  "action": "init"
}
```

---

### 测试场景 1.2: 缺少必填参数 [P2]

**Given (前置条件)**
- 服务正常运行

**When (操作)**
- 发送 POST 请求到 `/api/v1/oec/oncall/workorder/callback`
- 请求体为空或缺少必填字段

**Then (预期结果)**
- HTTP 状态码为 400
- 响应体包含错误信息

---

## 接口 2: GetOncallArgosDIYCardCallback

| 项目 | 值 |
|------|-----|
| 接口名称 | GetOncallArgosDIYCardCallback |
| 请求方法 | POST |
| URI | `/api/v:version/oec/governance/qa/argos/callback` |
| 接口描述 | Argos DIY Card 回调处理 |

---

### 测试场景 2.1: WorkOrderLevel 类型卡片构建 [P0]

**Given (前置条件)**
- 服务正常运行
- 请求包含 WorkOrderLevel 类型的告警

**When (操作)**
- 发送 POST 请求到 `/api/v1/oec/governance/qa/argos/callback`
- 请求体包含 metricType=WorkOrderLevel 的告警数据

**Then (预期结果)**
- HTTP 状态码为 200
- 响应体中 code 字段为 0
- 响应体 data.tags 包含工单相关信息（TenantName、Name、OncallUrl 等）

**测试数据**
```json
{
  "alert_context": {
    "tags": [
      {"key": "metricType", "value": "WorkOrderLevel"},
      {"key": "originalOncallId", "value": "123456789"},
      {"key": "WorkOrderLevel", "value": "P0"}
    ],
    "vars": [],
    "alert_timestamp": 1714387200
  }
}
```

---

### 测试场景 2.2: 通用卡片构建 [P0]

**Given (前置条件)**
- 服务正常运行
- 请求不包含特殊告警类型

**When (操作)**
- 发送 POST 请求到 `/api/v1/oec/governance/qa/argos/callback`
- 请求体包含非 WorkOrderLevel 类型的告警数据

**Then (预期结果)**
- HTTP 状态码为 200
- 响应体中 code 字段为 0
- 响应体 data.tags 直接返回原始 tags

---

## 接口 3: HandleAlarmCallback

| 项目 | 值 |
|------|-----|
| 接口名称 | HandleAlarmCallback |
| 请求方法 | POST |
| URI | `/osgw_v4/api/osgw/wares_alarm/alarm_detail/callback` |
| 接口描述 | 告警回调代理（跨区域调用） |

---

### 测试场景 3.1: 正常告警回调转发 [P0]

**Given (前置条件)**
- 服务正常运行
- 跨区域调用链路正常

**When (操作)**
- 发送 POST 请求到 `/osgw_v4/api/osgw/wares_alarm/alarm_detail/callback`
- 请求体包含有效的告警数据

**Then (预期结果)**
- HTTP 状态码为 200
- 响应体 err_code 字段为 0
- 日志记录了回调请求信息

**测试数据**
```json
{
  "alarm_data": {
    "rule_uid": "rule-12345",
    "rule_name": "测试告警规则",
    "check_vregion": "sg1",
    "alert_time": "2026-04-29T10:00:00Z",
    "tags": [
      {"key": "service", "value": "test-service"}
    ],
    "vars": [],
    "alarm_foreign_id": {
      "send_item_id": "send-12345"
    },
    "user_action_result": {
      "acked": false,
      "action_type_from": ""
    }
  }
}
```

---

### 测试场景 3.2: 跨区域调用超时 [P2]

**Given (前置条件)**
- 服务正常运行
- 跨区域调用链路异常（模拟超时）

**When (操作)**
- 发送 POST 请求到 `/osgw_v4/api/osgw/wares_alarm/alarm_detail/callback`

**Then (预期结果)**
- HTTP 状态码为 504 (Gateway Timeout)
- 或返回内部错误状态码

---

## 接口 4: Ping

| 项目 | 值 |
|------|-----|
| 接口名称 | Ping |
| 请求方法 | GET |
| URI | `/ping` |
| 接口描述 | 健康检查 |

---

### 测试场景 4.1: 健康检查 [P0]

**Given (前置条件)**
- 服务正常运行

**When (操作)**
- 发送 GET 请求到 `/ping`

**Then (预期结果)**
- HTTP 状态码为 200
- 响应体为 `{"message": "pong"}`

---

## 接口 5: HandleAlarmCallback (补充场景)

| 项目 | 值 |
|------|-----|
| 接口名称 | HandleAlarmCallback |
| 请求方法 | POST |
| URI | `/osgw_v4/api/osgw/wares_alarm/alarm_detail/callback` |
| 接口描述 | 告警回调代理（跨区域调用） |

---

### 测试场景 5.1: 绑定参数错误 [P0]

**Given (前置条件)**
- 服务正常运行

**When (操作)**
- 发送 POST 请求到 `/osgw_v4/api/osgw/wares_alarm/alarm_detail/callback`
- 请求体格式错误（非 JSON 格式或缺少必要字段）

**Then (预期结果)**
- HTTP 状态码为 200
- 响应体包含 "bind parameter err" 错误信息

**测试数据**
```json
{
  "invalid_field": "not_alarm_data"
}
```

---

## 接口 6: GetOncallArgosDIYCardCallback (补充场景)

| 项目 | 值 |
|------|-----|
| 接口名称 | GetOncallArgosDIYCardCallback |
| 请求方法 | POST |
| URI | `/api/v:version/oec/governance/qa/argos/callback` |
| 接口描述 | Argos DIY Card 回调处理（边界场景） |

---

### 测试场景 6.1: 无效的 oncallId 格式 [P0]

**Given (前置条件)**
- 服务正常运行
- 请求包含 WorkOrderLevel 类型但 oncallId 格式无效

**When (操作)**
- 发送 POST 请求到 `/api/v1/oec/governance/qa/argos/callback`
- 请求体包含 metricType=WorkOrderLevel 但 originalOncallId 为非数字字符串

**Then (预期结果)**
- HTTP 状态码为 200
- 响应体中 code 字段为 0
- 响应回退为通用卡片（BuildGeneralCard）

**测试数据**
```json
{
  "alert_context": {
    "tags": [
      {"key": "metricType", "value": "WorkOrderLevel"},
      {"key": "originalOncallId", "value": "invalid_id_format"},
      {"key": "WorkOrderLevel", "value": "P0"}
    ],
    "vars": [],
    "alert_timestamp": 1714387200
  }
}
```

---

### 测试场景 6.2: 数据库中不存在对应工单记录 [P0]

**Given (前置条件)**
- 服务正常运行
- 请求包含 WorkOrderLevel 类型但数据库中无对应记录

**When (操作)**
- 发送 POST 请求到 `/api/v1/oec/governance/qa/argos/callback`
- 请求体包含有效的 metricType=WorkOrderLevel 和 originalOncallId，但该 ID 在数据库中不存在

**Then (预期结果)**
- HTTP 状态码为 200
- 响应体中 code 字段为 0
- 响应回退为通用卡片（BuildGeneralCard）

**测试数据**
```json
{
  "alert_context": {
    "tags": [
      {"key": "metricType", "value": "WorkOrderLevel"},
      {"key": "originalOncallId", "value": "999999999999"},
      {"key": "WorkOrderLevel", "value": "P0"}
    ],
    "vars": [],
    "alert_timestamp": 1714387200
  }
}
```

---

### 测试场景 6.3: 缺少 metricType 标签 [P0]

**Given (前置条件)**
- 服务正常运行
- 请求不包含 metricType 标签

**When (操作)**
- 发送 POST 请求到 `/api/v1/oec/governance/qa/argos/callback`
- 请求体 tags 中不包含 metricType 字段

**Then (预期结果)**
- HTTP 状态码为 200
- 响应体中 code 字段为 0
- 响应为通用卡片（BuildGeneralCard）

**测试数据**
```json
{
  "alert_context": {
    "tags": [
      {"key": "someOtherKey", "value": "someValue"}
    ],
    "vars": [],
    "alert_timestamp": 1714387200
  }
}
```

---

## 测试总结

| 接口 | P0 用例数 | P1 用例数 | P2 用例数 |
|------|-----------|-----------|-----------|
| GetOncallCallback | 1 | 0 | 1 |
| GetOncallArgosDIYCardCallback | 5 | 0 | 0 |
| HandleAlarmCallback | 2 | 0 | 1 |
| Ping | 1 | 0 | 0 |
| **合计** | **9** | **0** | **2** |
