# 网络运维项目 Skills 和工具介绍

> 本文档详细介绍网络主动测量数据分析平台中使用的 Skills 和工具。
>
> 文档版本：v3.0
> 更新日期：2026-05-24

---

## 目录

- [一、项目概述](#一项目概述)
- [二、Skills 概览](#二skills-概览)
- [三、Intelligent Diagnosis Skill](#三intelligent-diagnosis-skill)
- [四、Network Telemetry Skill](#四network-telemetry-skill)
- [五、Knowledge Search Skill](#五knowledge-search-skill)
- [六、自定义工具](#六自定义工具)
- [七、数据模型](#七数据模型)
- [八、配置详解](#八配置详解)
- [九、API 接口](#九api-接口)
- [十、错误处理](#十错误处理)
- [十一、Skills 协作流程](#十一skills-协作流程)
- [十二、部署说明](#十二部署说明)
- [十三、测试相关](#十三测试相关)
- [十四、技术栈总结](#十四技术栈总结)
- [十五、性能指标](#十五性能指标)
- [十六、版本历史](#十六版本历史)
- [十七、最佳实践](#十七最佳实践)
- [十八、故障排查指南](#十八故障排查指南)
- [十九、安全设计](#十九安全设计)
- [二十、可观测性](#二十可观测性)
- [二十一、扩展开发指南](#二十一扩展开发指南)
- [二十二、常见问题解答](#二十二常见问题解答)
- [二十三、实战案例](#二十三实战案例)
- [附录](#附录)

---

## 一、项目概述

### 1.1 项目定位

网络主动测量数据分析平台，通过 AI Agent 技术实现：

- **网络测量数据分析**：分析 Ping、Traceroute 等主动测量数据
- **故障自动诊断**：多 Agent 协作，自动分析根因
- **知识库检索**：RAG 技术检索历史案例和 SOP
- **智能可视化**：自动生成网络路径图、延迟趋势图

### 1.2 核心功能

| 功能模块 | 描述 |
|---------|------|
| 数据采集 | 从 ClickHouse 查询网络测量数据 |
| 故障诊断 | 多 Agent 协作，自动定位根因 |
| 知识检索 | 向量相似度检索历史案例 |
| 可视化 | 自动生成分析图表 |

---

## 二、Skills 概览

本项目包含 3 个自定义 Skills，用于实现智能故障诊断的完整流程：

| Skill | 功能定位 | 核心能力 | 触发场景 |
|-------|---------|---------|---------|
| Intelligent Diagnosis | 智能故障诊断 | 多 Agent 协作、根因分析、生成解决方案 | 收到告警、用户发起诊断请求 |
| Network Telemetry | 网络测量数据分析 | Ping/Traceroute 数据查询、延迟趋势分析、链路质量评估 | 需要查询网络数据时 |
| Knowledge Search | 知识库检索 | 向量相似度检索、SOP 文档查找、历史案例匹配 | 需要参考历史经验时 |

### 2.1 Skills 依赖关系

```
┌─────────────────────────────────────────────────────────┐
│                    用户请求 / 告警                        │
└─────────────────────────┬───────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────┐
│               Intelligent Diagnosis (编排层)             │
│                                                          │
│    负责解析请求、协调其他 Skills、生成最终报告              │
└───────────┬─────────────────────────┬───────────────────┘
            │                         │
            ↓                         ↓
┌───────────────────┐     ┌───────────────────┐
│ Network Telemetry │     │  Knowledge Search │
│    (数据查询层)    │     │    (知识检索层)    │
└───────────────────┘     └───────────────────┘
```

---

## 三、Intelligent Diagnosis Skill

### 3.1 功能定位

智能故障诊断 Skill，通过多 Agent 协作实现故障自动诊断，定位根因并生成解决方案。

### 3.2 核心能力

| Action | 功能 | 输入 | 输出 |
|--------|------|------|------|
| `diagnose_alert` | 诊断告警 | 告警信息 | 根因分析报告 |
| `correlate_data` | 关联分析 | 会话 ID | 数据关联结果 |
| `generate_report` | 生成报告 | 会话 ID、格式 | 诊断报告文档 |

### 3.3 架构设计

采用**多 Agent 协作架构**，包含 3 个核心 Agent：

```
┌─────────────────────────────────────────────────────────────┐
│                    Agent Orchestrator                        │
│                       (编排调度器)                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐   │
│  │  Knowledge   │    │   Analysis   │    │  Diagnosis   │   │
│  │    Agent     │───▶│    Agent     │───▶│    Agent     │   │
│  │              │    │              │    │              │   │
│  │ • 检索历史案例│    │ • 分析网络数据│    │ • 综合诊断   │   │
│  │ • 匹配 SOP   │    │ • 查询异常事件│    │ • 生成建议   │   │
│  │ • 相似度评分 │    │ • 趋势分析   │    │ • 置信度计算 │   │
│  └──────────────┘    └──────────────┘    └──────────────┘   │
│         │                    │                    │          │
│         └────────────────────┼────────────────────┘          │
│                              ↓                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │                RAG Knowledge Base                    │    │
│  │           (Vector DB + Embedding Model)             │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 3.4 Agent 详细说明

#### 3.4.1 Knowledge Agent

**职责：** 从知识库中检索相关的历史案例和 SOP 文档。

| 属性 | 说明 |
|------|------|
| 输入 | 告警标题、告警描述、关键实体（区域、服务等） |
| 输出 | 相似案例列表、SOP 文档、相似度评分 |
| 调用服务 | Knowledge Search Skill |

**处理逻辑：**

```python
async def process(self, alert_info: dict) -> dict:
    # 1. 提取关键词
    keywords = self._extract_keywords(alert_info)
    
    # 2. 构建查询
    query = f"{alert_info['title']} {alert_info['description']}"
    
    # 3. 调用 Knowledge Search
    similar_cases = await self.knowledge_search.search_similar(
        query=query,
        top_k=5,
        doc_type="ticket"
    )
    
    # 4. 查找 SOP
    sops = await self.knowledge_search.find_sop(
        query=keywords,
        category=alert_info.get('category', 'network')
    )
    
    return {
        "similar_cases": similar_cases,
        "sops": sops,
        "top_keywords": keywords
    }
```

#### 3.4.2 Analysis Agent

**职责：** 查询和分析网络测量数据，识别异常模式。

| 属性 | 说明 |
|------|------|
| 输入 | 时间范围、区域、指标类型 |
| 输出 | 网络指标数据、异常事件列表、趋势分析结果 |
| 调用服务 | Network Telemetry Skill |

**处理逻辑：**

```python
async def process(self, context: dict) -> dict:
    # 1. 确定查询时间范围
    time_range = self._determine_time_range(context)
    
    # 2. 查询延迟数据
    latency_data = await self.telemetry.query_latency(
        start_time=time_range['start'],
        end_time=time_range['end'],
        region=context.get('region')
    )
    
    # 3. 查询异常事件
    anomalies = await self.telemetry.query_anomalies(
        time_range_minutes=time_range['duration_minutes'],
        severity="critical"
    )
    
    # 4. 分析趋势
    trend = self._analyze_trend(latency_data)
    
    return {
        "latency_data": latency_data,
        "anomalies": anomalies,
        "trend": trend,
        "baseline": self._get_baseline(context['region'])
    }
```

#### 3.4.3 Diagnosis Agent

**职责：** 综合分析，定位根因，生成诊断报告和解决方案。

| 属性 | 说明 |
|------|------|
| 输入 | Knowledge Agent 输出、Analysis Agent 输出 |
| 输出 | 根因分类、置信度评分、解决方案建议 |

**处理逻辑：**

```python
async def process(self, knowledge_result: dict, analysis_result: dict) -> dict:
    # 1. 特征提取
    features = self._extract_features(knowledge_result, analysis_result)
    
    # 2. 根因分类
    root_cause = self._classify_root_cause(features)
    
    # 3. 置信度计算
    confidence = self._calculate_confidence(
        knowledge_similarity=knowledge_result['max_similarity'],
        data_anomaly_score=analysis_result['anomaly_score'],
        pattern_match_score=features['pattern_score']
    )
    
    # 4. 生成建议
    recommendations = self._generate_recommendations(
        root_cause=root_cause,
        similar_cases=knowledge_result['similar_cases'],
        sops=knowledge_result['sops']
    )
    
    return {
        "root_cause": root_cause,
        "confidence": confidence,
        "recommendations": recommendations,
        "evidence": self._build_evidence(knowledge_result, analysis_result)
    }
```

### 3.5 执行流程

```
┌─────────────────────────────────────────────────────────────┐
│                     1. 接收告警信息                          │
│                                                              │
│  输入: {                                                     │
│    "alert_id": "ALT-12345",                                 │
│    "title": "网络延迟突增",                                  │
│    "region": "Singapore-Central",                           │
│    "timestamp": "2025-01-15T00:30:00Z"                      │
│  }                                                          │
└─────────────────────────────┬───────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              2. Knowledge Agent 检索历史案例                 │
│                                                              │
│  • 提取关键词: ["延迟", "突增", "Singapore"]                 │
│  • 向量检索: 找到 3 个相似案例                               │
│  • SOP 匹配: 找到 "网络延迟排查流程"                         │
│  • 输出相似度评分: 0.85                                      │
└─────────────────────────────┬───────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              3. Analysis Agent 查询网络数据                  │
│                                                              │
│  • 查询延迟: P99 从 45ms 上升到 150ms                        │
│  • 查询异常事件: 发现 2 个 latency_spike 事件                │
│  • 趋势分析: 检测到上升拐点                                  │
│  • 异常评分: 0.78                                            │
└─────────────────────────────┬───────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│              4. Diagnosis Agent 综合诊断                     │
│                                                              │
│  • 根因分类: network > latency                               │
│  • 置信度: 0.35×0.85 + 0.40×0.78 + 0.25×0.72 = 0.79        │
│  • 生成建议: 检查链路拥塞、参考案例 TK-12345                 │
└─────────────────────────────┬───────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                     5. 输出诊断报告                          │
└─────────────────────────────────────────────────────────────┘
```

### 3.6 根因分类模型

#### 3.6.1 分类层次结构

```
根因分类
├── network (网络层)
│   ├── latency (延迟问题)
│   │   ├── 链路拥塞
│   │   ├── 设备故障
│   │   └── 路由异常
│   ├── packet_loss (丢包问题)
│   │   ├── 设备故障
│   │   └── 链路质量差
│   └── connection (连接问题)
│       ├── 防火墙规则
│       └── 连接数超限
├── service (服务层)
│   ├── overload (过载)
│   │   ├── 容量不足
│   │   └── 流量突发
│   └── error (错误)
│       ├── 代码缺陷
│       └── 配置错误
└── unknown (未知)
    └── 需要人工介入
```

#### 3.6.2 分类规则

| 特征条件 | 分类结果 |
|---------|---------|
| 延迟突增 + 无丢包 | network > latency |
| 丢包率 > 阈值 | network > packet_loss |
| 连接失败 + 无延迟异常 | network > connection |
| CPU/内存高 + 延迟高 | service > overload |
| 错误日志 + 无网络异常 | service > error |

### 3.7 置信度计算

#### 3.7.1 计算公式

```python
def calculate_confidence(
    knowledge_similarity: float,  # 知识相似度 [0, 1]
    data_anomaly_score: float,    # 数据异常分数 [0, 1]
    pattern_match_score: float    # 模式匹配分数 [0, 1]
) -> float:
    """
    计算诊断置信度
    
    权重分配:
    - 知识相似度: 35%
    - 数据异常分数: 40%
    - 模式匹配分数: 25%
    """
    WEIGHT_KNOWLEDGE = 0.35
    WEIGHT_ANOMALY = 0.40
    WEIGHT_PATTERN = 0.25
    
    confidence = (
        WEIGHT_KNOWLEDGE * knowledge_similarity +
        WEIGHT_ANOMALY * data_anomaly_score +
        WEIGHT_PATTERN * pattern_match_score
    )
    
    return round(confidence, 2)
```

#### 3.7.2 置信度等级

| 置信度范围 | 等级 | 说明 |
|-----------|------|------|
| 0.9 - 1.0 | 高 | 诊断结果可信，可直接执行建议 |
| 0.7 - 0.9 | 中 | 诊断结果较可信，建议人工确认后执行 |
| 0.5 - 0.7 | 低 | 诊断结果存疑，建议人工分析 |
| < 0.5 | 极低 | 无法自动诊断，需人工介入 |

### 3.8 输出示例

#### 3.8.1 完整诊断报告

```json
{
  "session_id": "diag-20250115-001",
  "timestamp": "2025-01-15T00:35:00Z",
  "duration_ms": 1250,
  
  "root_cause": {
    "category": "network",
    "subcategory": "latency",
    "description": "网络延迟异常，由新加坡区域链路拥塞导致",
    "confidence": 0.88,
    "confidence_level": "high"
  },
  
  "evidence": [
    {
      "source": "network_telemetry",
      "type": "latency_anomaly",
      "details": {
        "avg_latency_ms": 150.5,
        "baseline_ms": 45.2,
        "deviation": "3.3x baseline",
        "p99_latency_ms": 280.3
      }
    },
    {
      "source": "network_telemetry",
      "type": "anomaly_event",
      "details": {
        "event_type": "latency_spike",
        "severity": "critical",
        "occurred_at": "2025-01-15T00:28:00Z"
      }
    },
    {
      "source": "knowledge_base",
      "type": "similar_case",
      "details": {
        "doc_id": "TK-12345",
        "title": "新加坡区域网络延迟异常",
        "similarity": 0.92,
        "resolution": "链路切换后恢复"
      }
    },
    {
      "source": "knowledge_base",
      "type": "sop_reference",
      "details": {
        "sop_id": "SOP-001",
        "title": "网络延迟排查流程"
      }
    }
  ],
  
  "recommendations": [
    {
      "priority": 1,
      "action": "检查新加坡区域出口链路状态",
      "rationale": "延迟突增通常与链路拥塞相关"
    },
    {
      "priority": 2,
      "action": "参考历史案例 TK-12345 的处理方案",
      "rationale": "相似度 92%，解决方案: 链路切换"
    },
    {
      "priority": 3,
      "action": "按照 SOP-001 执行排查流程",
      "rationale": "标准延迟排查 SOP"
    },
    {
      "priority": 4,
      "action": "如问题持续，联系网络运维团队",
      "rationale": "需要专业设备检查"
    }
  ],
  
  "related_data": {
    "latency_chart_url": "/charts/diag-20250115-001-latency.png",
    "topology_chart_url": "/charts/diag-20250115-001-topo.png",
    "similar_cases_count": 3,
    "anomaly_events_count": 2
  }
}
```

### 3.9 配置说明

```yaml
# config/diagnosis.yaml

# Agent 配置
agents:
  knowledge:
    enabled: true
    top_k: 5                    # 检索返回数量
    similarity_threshold: 0.7   # 相似度阈值
    timeout_ms: 5000            # 超时时间
    
  analysis:
    enabled: true
    time_range_hours: 1         # 默认查询时间范围
    baseline_window_days: 7     # 基线计算窗口
    timeout_ms: 10000
    
  diagnosis:
    enabled: true
    confidence_threshold: 0.6   # 最低置信度阈值
    max_recommendations: 5      # 最大建议数量

# 工作流配置
workflow:
  mode: "sequential"           # sequential | parallel
  steps:
    - knowledge
    - analysis
    - diagnosis
  
  # 并行模式配置
  parallel:
    knowledge_weight: 0.5
    analysis_weight: 0.5
    merge_strategy: "weighted_average"

# 根因分类配置
classification:
  categories:
    network:
      weight: 0.6
      subcategories:
        latency: {threshold: 0.7}
        packet_loss: {threshold: 0.05}
        connection: {threshold: 0.1}
    service:
      weight: 0.4
      subcategories:
        overload: {cpu_threshold: 80}
        error: {error_rate_threshold: 0.01}

# 置信度权重
confidence_weights:
  knowledge_similarity: 0.35
  data_anomaly_score: 0.40
  pattern_match_score: 0.25
```

---

## 四、Network Telemetry Skill

### 4.1 功能定位

连接 ClickHouse 数据库，分析网络测量数据（Ping、Traceroute），提供延迟、流量、丢包等指标的查询和分析能力。

### 4.2 核心能力

| Action | 功能 | 使用场景 | 数据源 |
|--------|------|---------|--------|
| `query_latency` | 查询网络延迟 | 分析网络性能、定位延迟问题 | network_latency 表 |
| `query_anomalies` | 查询异常事件 | 快速定位异常时段和事件 | network_events 表 |
| `query_traffic` | 查询流量统计 | 容量分析、异常流量检测 | traffic_stats 表 |
| `query_link_quality` | 查询链路质量 | 跨区域链路健康检查 | link_quality 表 |
| `analyze_trend` | 分析延迟趋势 | 检测异常延迟变化 | 多表关联 |

### 4.3 数据查询能力

#### 4.3.1 延迟查询 (`query_latency`)

**功能：** 查询指定时间范围和区域的网络延迟数据。

**输入参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `start_time` | string | 否 | 1小时前 | 开始时间 (ISO 8601 格式) |
| `end_time` | string | 否 | 当前时间 | 结束时间 |
| `source_region` | string | 否 | - | 源区域过滤 |
| `target_region` | string | 否 | - | 目标区域过滤 |
| `interval` | string | 否 | "minute" | 聚合间隔 (minute/hour/day) |
| `percentiles` | array | 否 | [50, 95, 99] | 需要计算的百分位 |

**返回字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `timestamp` | datetime | 时间戳 |
| `source_region` | string | 源区域 |
| `target_region` | string | 目标区域 |
| `sample_count` | int | 样本数量 |
| `avg_latency_ms` | float | 平均延迟 (毫秒) |
| `min_latency_ms` | float | 最小延迟 |
| `max_latency_ms` | float | 最大延迟 |
| `p50_latency_ms` | float | P50 延迟 |
| `p95_latency_ms` | float | P95 延迟 |
| `p99_latency_ms` | float | P99 延迟 |
| `std_dev_ms` | float | 标准差 |
| `packet_loss_rate` | float | 丢包率 (0-1) |

**请求示例：**

```json
{
  "action": "query_latency",
  "params": {
    "start_time": "2025-01-15T00:00:00Z",
    "end_time": "2025-01-15T01:00:00Z",
    "source_region": "Singapore-Central",
    "target_region": "US-East",
    "interval": "minute",
    "percentiles": [50, 95, 99]
  }
}
```

**响应示例：**

```json
{
  "success": true,
  "data": [
    {
      "timestamp": "2025-01-15T00:00:00Z",
      "source_region": "Singapore-Central",
      "target_region": "US-East",
      "sample_count": 1500,
      "avg_latency_ms": 45.2,
      "min_latency_ms": 32.1,
      "max_latency_ms": 89.3,
      "p50_latency_ms": 42.5,
      "p95_latency_ms": 68.2,
      "p99_latency_ms": 82.1,
      "std_dev_ms": 12.3,
      "packet_loss_rate": 0.001
    }
  ],
  "meta": {
    "total_records": 60,
    "query_time_ms": 125,
    "cache_hit": false
  }
}
```

#### 4.3.2 异常事件查询 (`query_anomalies`)

**功能：** 查询网络异常事件，如延迟突增、丢包、连接失败等。

**输入参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `time_range_minutes` | int | 否 | 60 | 查询时间范围 (分钟) |
| `severity` | string | 否 | - | 严重级别过滤 (warning/critical) |
| `event_type` | string | 否 | - | 事件类型过滤 |
| `region` | string | 否 | - | 区域过滤 |
| `limit` | int | 否 | 100 | 返回数量限制 |

**事件类型枚举：**

| 事件类型 | 说明 | 判定条件 |
|---------|------|---------|
| `latency_spike` | 延迟突增 | P99 超过基线 2 倍 |
| `packet_loss` | 丢包事件 | 丢包率 > 1% |
| `connection_failure` | 连接失败 | 连接失败率 > 阈值 |
| `dns_error` | DNS 解析错误 | DNS 超时或失败 |
| `route_change` | 路由变化 | 检测到路径变化 |
| `jitter_high` | 抖动过高 | Jitter > 阈值 |

**请求示例：**

```json
{
  "action": "query_anomalies",
  "params": {
    "time_range_minutes": 60,
    "severity": "critical",
    "event_type": "latency_spike",
    "region": "Singapore-Central"
  }
}
```

**响应示例：**

```json
{
  "success": true,
  "data": [
    {
      "event_id": "EVT-20250115-001",
      "event_type": "latency_spike",
      "severity": "critical",
      "source_region": "Singapore-Central",
      "target_region": "US-East",
      "occurred_at": "2025-01-15T00:28:00Z",
      "metric_value": 280.5,
      "baseline_value": 45.2,
      "deviation_ratio": 6.2,
      "duration_seconds": 180,
      "affected_samples": 450,
      "threshold": 90.4,
      "description": "P99 延迟从 45ms 突增至 280ms"
    }
  ],
  "meta": {
    "total_events": 2,
    "critical_count": 1,
    "warning_count": 1
  }
}
```

#### 4.3.3 链路质量查询 (`query_link_quality`)

**功能：** 查询跨区域链路的健康状态和质量指标。

**输入参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `start_time` | string | 否 | 1小时前 | 开始时间 |
| `end_time` | string | 否 | 当前时间 | 结束时间 |
| `link_id` | string | 否 | - | 链路 ID (格式: source-target) |
| `min_health_score` | int | 否 | 0 | 最小健康分数过滤 |

**返回字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `link_id` | string | 链路 ID |
| `source_region` | string | 源区域 |
| `target_region` | string | 目标区域 |
| `avg_rtt_ms` | float | 平均 RTT |
| `min_rtt_ms` | float | 最小 RTT |
| `max_rtt_ms` | float | 最大 RTT |
| `jitter_ms` | float | 抖动 (标准差) |
| `loss_rate` | float | 丢包率 |
| `hop_count` | int | 跳数 |
| `health_score` | int | 健康分数 (0-100) |
| `status` | string | 状态 (healthy/degraded/unhealthy) |
| `last_updated` | datetime | 最后更新时间 |

**健康分数计算：**

```python
def calculate_health_score(
    avg_rtt_ms: float,
    jitter_ms: float,
    loss_rate: float
) -> int:
    """
    计算链路健康分数 (0-100)
    """
    # RTT 评分 (0-40分)
    if avg_rtt_ms < 50:
        rtt_score = 40
    elif avg_rtt_ms < 100:
        rtt_score = 30
    elif avg_rtt_ms < 200:
        rtt_score = 20
    else:
        rtt_score = 10
    
    # 抖动评分 (0-30分)
    if jitter_ms < 10:
        jitter_score = 30
    elif jitter_ms < 30:
        jitter_score = 20
    else:
        jitter_score = 10
    
    # 丢包评分 (0-30分)
    if loss_rate < 0.001:
        loss_score = 30
    elif loss_rate < 0.01:
        loss_score = 20
    else:
        loss_score = 10
    
    return rtt_score + jitter_score + loss_score
```

**状态判定规则：**

| 健康分数 | 状态 | 说明 |
|---------|------|------|
| 80-100 | healthy | 链路状态良好 |
| 50-79 | degraded | 链路状态降级 |
| 0-49 | unhealthy | 链路状态异常 |

#### 4.3.4 流量统计查询 (`query_traffic`)

**功能：** 查询网络流量统计，用于容量分析和异常流量检测。

**输入参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `start_time` | string | 否 | 开始时间 |
| `end_time` | string | 否 | 结束时间 |
| `region` | string | 否 | 区域过滤 |
| `direction` | string | 否 | 方向 (inbound/outbound/both) |
| `interval` | string | 否 | 聚合间隔 |

**返回字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `timestamp` | datetime | 时间戳 |
| `region` | string | 区域 |
| `direction` | string | 方向 |
| `bytes_total` | long | 总字节数 |
| `packets_total` | long | 总包数 |
| `throughput_mbps` | float | 吞吐量 (Mbps) |
| `unique_flows` | int | 唯一流数 |
| `top_protocols` | array | 协议分布 |

#### 4.3.5 趋势分析 (`analyze_trend`)

**功能：** 分析延迟随时间的变化趋势，检测异常拐点。

**输入参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `metric` | string | 是 | 指标类型 (latency/loss/throughput) |
| `region` | string | 是 | 区域 |
| `time_range_hours` | int | 否 | 时间范围，默认 24 |
| `detect_anomalies` | bool | 否 | 是否检测异常点，默认 true |

**返回字段：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `trend_direction` | string | 趋势方向 (up/stable/down) |
| `trend_slope` | float | 趋势斜率 |
| `change_points` | array | 变化拐点列表 |
| `anomaly_points` | array | 异常点列表 |
| `forecast` | array | 预测值 (未来 6 个时间点) |

### 4.4 典型应用场景

#### 场景 1：延迟突增诊断

```
触发条件：收到延迟告警

执行步骤:
┌─────────────────────────────────────────────────────────────┐
│ Step 1: 查询最近 30 分钟的延迟数据                           │
│         query_latency(time_range_minutes=30)                │
└─────────────────────────────┬───────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 2: 对比历史基线，确认异常幅度                           │
│         计算当前值 vs 基线的偏差比例                         │
│         deviation = (current - baseline) / baseline         │
└─────────────────────────────┬───────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 3: 查询同时段的异常事件                                 │
│         query_anomalies(time_range_minutes=30)              │
└─────────────────────────────┬───────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 4: 检查链路质量分数                                     │
│         query_link_quality()                                │
└─────────────────────────────┬───────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 5: 输出诊断结论                                         │
│         - 异常确认: 是/否                                    │
│         - 异常类型: latency_spike/packet_loss/...           │
│         - 影响范围: 区域、链路                               │
│         - 相关事件: 事件列表                                 │
└─────────────────────────────────────────────────────────────┘
```

#### 场景 2：跨区域链路问题排查

```
触发条件：用户反馈跨区域访问慢

执行步骤:
┌─────────────────────────────────────────────────────────────┐
│ Step 1: 查询两端区域的延迟数据                               │
│         query_latency(source_region=A, target_region=B)     │
│         query_latency(source_region=B, target_region=A)     │
└─────────────────────────────┬───────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 2: 检查链路健康分数                                     │
│         query_link_quality(link_id="A-B")                   │
└─────────────────────────────┬───────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 3: 查看是否有丢包事件                                   │
│         query_anomalies(event_type="packet_loss")           │
└─────────────────────────────┬───────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 4: 分析流量统计，确认是否有拥塞                         │
│         query_traffic() + analyze_trend()                   │
└─────────────────────────────┬───────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 5: 输出排查结论                                         │
│         - 链路状态: healthy/degraded/unhealthy               │
│         - 问题定位: 延迟/丢包/拥塞                           │
│         - 建议: 链路切换/扩容/其他                           │
└─────────────────────────────────────────────────────────────┘
```

### 4.5 数据源配置

```yaml
# config/telemetry.yaml

# ClickHouse 数据源配置
clickhouse:
  host: ${CLICKHOUSE_HOST:localhost}
  port: ${CLICKHOUSE_PORT:8123}
  database: network_telemetry
  user: ${CLICKHOUSE_USER:default}
  password: ${CLICKHOUSE_PASSWORD:}
  secure: true
  timeout_seconds: 30
  
  # 连接池配置
  pool:
    max_connections: 10
    min_connections: 2
    
  # 查询缓存配置
  cache:
    enabled: true
    ttl_seconds: 60
    max_size: 1000

# 数据表配置
tables:
  network_latency:
    description: "网络延迟数据"
    time_column: "timestamp"
    partition_by: "toYYYYMM(timestamp)"
    
  network_events:
    description: "网络异常事件"
    time_column: "occurred_at"
    
  traffic_stats:
    description: "流量统计"
    time_column: "timestamp"
    
  link_quality:
    description: "链路质量"
    time_column: "last_updated"

# 基线配置
baseline:
  # 基线计算窗口
  window_days: 7
  # 最小样本数
  min_samples: 1000
  # 百分位基线
  percentiles: [50, 95, 99]

# 异常检测配置
anomaly_detection:
  # 延迟突增阈值 (倍数)
  latency_spike_threshold: 2.0
  # 丢包率阈值
  packet_loss_threshold: 0.01
  # 连接失败率阈值
  connection_failure_threshold: 0.05
  # 抖动阈值 (ms)
  jitter_threshold: 50
```

---

## 五、Knowledge Search Skill

### 5.1 功能定位

从向量数据库检索历史案例、SOP 文档、解决方案，支持向量相似度检索和关键词混合检索。

### 5.2 核心能力

| Action | 功能 | 输入 | 返回结果 |
|--------|------|------|---------|
| `search_similar` | 相似案例检索 | 查询文本、数量限制 | 相似度排序的案例列表 |
| `find_sop` | SOP 查找 | 查询文本、分类 | 匹配的 SOP 文档 |
| `get_recommendations` | 推荐方案 | 查询文本、上下文 | 解决方案建议 |

### 5.3 技术架构

```
┌─────────────────────────────────────────────────────────────┐
│                      Query Processing                        │
│                                                              │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐      │
│  │   Query     │    │  Embedding  │    │   Vector    │      │
│  │   Text      │───▶│    Model    │───▶│   Search    │      │
│  │             │    │  (BGE-M3)   │    │             │      │
│  └─────────────┘    └─────────────┘    └─────────────┘      │
│                           │                │                │
│                           ▼                ▼                │
│                    ┌─────────────────────────────┐          │
│                    │      Query Vector           │          │
│                    │      (1024-dimension)       │          │
│                    └─────────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Hybrid Retrieval                        │
│                                                              │
│   ┌─────────────────────────────────────────────────────┐   │
│   │                 Vector Search (70%)                  │   │
│   │                                                      │   │
│   │   score = cosine_similarity(query_vec, doc_vec)     │   │
│   │                                                      │   │
│   └─────────────────────────────────────────────────────┘   │
│                           +                                  │
│   ┌─────────────────────────────────────────────────────┐   │
│   │                Keyword Search (30%)                  │   │
│   │                                                      │   │
│   │   score = BM25(query_terms, doc_terms)              │   │
│   │                                                      │   │
│   └─────────────────────────────────────────────────────┘   │
│                           =                                  │
│   ┌─────────────────────────────────────────────────────┐   │
│   │                   Final Score                        │   │
│   │                                                      │   │
│   │   final = 0.7 * vector_score + 0.3 * keyword_score  │   │
│   │                                                      │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                       Vector Database                        │
│                                                              │
│   ┌─────────────────────────────────────────────────────┐   │
│   │              Collections:                            │   │
│   │                                                      │   │
│   │   oncall_tickets                                     │   │
│   │   ├── 历史工单记录                                    │   │
│   │   ├── 包含问题描述、根因、解决方案                     │   │
│   │   └── 向量数: ~10,000                                │   │
│   │                                                      │   │
│   │   sop_documents                                      │   │
│   │   ├── 标准操作流程文档                               │   │
│   │   ├── 包含步骤、检查项、注意事项                      │   │
│   │   └── 向量数: ~500                                   │   │
│   │                                                      │   │
│   │   solutions                                          │   │
│   │   ├── 解决方案库                                     │   │
│   │   ├── 包含问题描述、解决方案、效果评价                │   │
│   │   └── 向量数: ~2,000                                 │   │
│   │                                                      │   │
│   └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 5.4 检索流程详解

```
┌─────────────────────────────────────────────────────────────┐
│ Step 1: 查询预处理                                           │
│                                                              │
│ 输入: "新加坡区域网络延迟突增，需要排查原因"                  │
│                                                              │
│ 处理:                                                        │
│ • 分词: ["新加坡", "区域", "网络", "延迟", "突增", "排查"]    │
│ • 实体识别: region="新加坡", problem="延迟突增"              │
│ • 意图识别: diagnosis (诊断类查询)                           │
└─────────────────────────────┬───────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 2: 向量生成                                             │
│                                                              │
│ 模型: BAAI/bge-m3                                           │
│ 输出维度: 1024                                               │
│                                                              │
│ query_vector = embedding_model.encode(                      │
│     "新加坡区域网络延迟突增，需要排查原因"                    │
│ )                                                           │
│                                                              │
│ 结果: [0.023, -0.145, 0.678, ..., 0.034] (1024维)           │
└─────────────────────────────┬───────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 3: 向量检索                                             │
│                                                              │
│ 在 Qdrant 中执行相似度搜索:                                  │
│                                                              │
│ results = qdrant.search(                                    │
│     collection_name="oncall_tickets",                       │
│     query_vector=query_vector,                              │
│     limit=10,                                               │
│     score_threshold=0.5                                     │
│ )                                                           │
│                                                              │
│ 返回: Top-10 相似文档，附带相似度分数                        │
└─────────────────────────────┬───────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 4: 关键词检索                                           │
│                                                              │
│ 使用 BM25 算法进行关键词匹配:                                │
│                                                              │
│ results = bm25_search(                                      │
│     query_terms=["新加坡", "延迟", "突增"],                  │
│     collection="oncall_tickets",                            │
│     limit=10                                                │
│ )                                                           │
└─────────────────────────────┬───────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 5: 结果融合与重排序                                     │
│                                                              │
│ 混合评分:                                                    │
│ final_score = 0.7 * vector_score + 0.3 * keyword_score      │
│                                                              │
│ 重排序: 按 final_score 降序排列                              │
│                                                              │
│ 去重: 合并相同 doc_id 的结果                                 │
└─────────────────────────────┬───────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 6: 返回结果                                             │
│                                                              │
│ 返回 Top-K 结果，包含:                                       │
│ • doc_id: 文档唯一标识                                       │
│ • title: 文档标题                                           │
│ • content: 文档内容摘要                                      │
│ • score: 相似度分数                                         │
│ • metadata: 元数据 (严重级别、解决时间等)                    │
└─────────────────────────────────────────────────────────────┘
```

### 5.5 核心功能详解

#### 5.5.1 相似案例检索 (`search_similar`)

**请求参数：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `query` | string | 是 | - | 查询文本 |
| `top_k` | int | 否 | 5 | 返回数量 |
| `doc_type` | string | 否 | "all" | 文档类型 (ticket/sop/solution/all) |
| `filters` | object | 否 | {} | 过滤条件 |
| `score_threshold` | float | 否 | 0.5 | 最低相似度阈值 |

**请求示例：**

```json
{
  "action": "search_similar",
  "params": {
    "query": "新加坡区域网络延迟突增",
    "top_k": 5,
    "doc_type": "ticket",
    "filters": {
      "severity": "critical",
      "time_range": "30d"
    },
    "score_threshold": 0.6
  }
}
```

**响应示例：**

```json
{
  "success": true,
  "results": [
    {
      "doc_id": "TK-12345",
      "doc_type": "ticket",
      "title": "新加坡区域网络延迟异常",
      "content": "问题描述: 2025-01-10 新加坡区域出现网络延迟突增，P99 从 45ms 上升到 180ms...",
      "score": 0.92,
      "vector_score": 0.95,
      "keyword_score": 0.85,
      "metadata": {
        "severity": "critical",
        "category": "network",
        "subcategory": "latency",
        "resolution_time_minutes": 45,
        "resolved_at": "2025-01-10T02:30:00Z",
        "root_cause": "链路拥塞",
        "solution": "流量切换到备用链路"
      },
      "highlights": [
        "<em>新加坡</em>区域<em>网络延迟</em>异常",
        "P99 从 45ms 上升到 180ms"
      ]
    },
    {
      "doc_id": "TK-12340",
      "doc_type": "ticket",
      "title": "跨区域访问延迟高",
      "content": "问题描述: 新加坡到美国东海岸链路延迟偏高...",
      "score": 0.78,
      "metadata": {
        "severity": "warning",
        "resolution_time_minutes": 30
      }
    }
  ],
  "meta": {
    "query_vector_dimension": 1024,
    "total_searched": 10000,
    "search_time_ms": 45
  }
}
```

#### 5.5.2 SOP 查找 (`find_sop`)

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `query` | string | 是 | 查询文本 |
| `category` | string | 否 | 分类过滤 (network/service/database/all) |
| `include_steps` | bool | 否 | 是否包含详细步骤，默认 true |

**请求示例：**

```json
{
  "action": "find_sop",
  "params": {
    "query": "延迟排查",
    "category": "network",
    "include_steps": true
  }
}
```

**响应示例：**

```json
{
  "success": true,
  "results": [
    {
      "sop_id": "SOP-001",
      "title": "网络延迟排查流程",
      "category": "network",
      "description": "用于排查网络延迟异常的标准操作流程",
      "score": 0.88,
      "steps": [
        {
          "step_number": 1,
          "title": "确认延迟范围和影响",
          "description": "确认延迟异常的区域、时间段、影响的服务",
          "checklist": [
            "确认受影响的区域",
            "确认异常开始时间",
            "确认受影响的服务列表"
          ]
        },
        {
          "step_number": 2,
          "title": "查询网络测量数据",
          "description": "从 ClickHouse 查询延迟数据",
          "checklist": [
            "查询 P50/P95/P99 延迟",
            "对比历史基线",
            "确认异常幅度"
          ]
        },
        {
          "step_number": 3,
          "title": "检查链路状态",
          "description": "检查相关链路的健康状态",
          "checklist": [
            "查询链路质量分数",
            "检查是否有丢包",
            "检查是否有路由变化"
          ]
        },
        {
          "step_number": 4,
          "title": "分析历史案例",
          "description": "检索相似的历史案例",
          "checklist": [
            "检索相似度 > 0.7 的案例",
            "参考解决方案",
            "评估适用性"
          ]
        },
        {
          "step_number": 5,
          "title": "执行解决方案",
          "description": "根据分析结果执行相应措施",
          "checklist": [
            "选择合适的解决方案",
            "执行并监控效果",
            "记录处理过程"
          ]
        }
      ],
      "related_sops": ["SOP-002", "SOP-003"],
      "last_updated": "2025-01-01T00:00:00Z"
    }
  ]
}
```

#### 5.5.3 推荐方案 (`get_recommendations`)

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `query` | string | 是 | 查询文本 |
| `context` | object | 否 | 上下文信息 |
| `max_recommendations` | int | 否 | 最大推荐数量，默认 5 |

**请求示例：**

```json
{
  "action": "get_recommendations",
  "params": {
    "query": "网络延迟突增",
    "context": {
      "region": "Singapore",
      "service": "api-gateway",
      "severity": "critical"
    },
    "max_recommendations": 5
  }
}
```

**响应示例：**

```json
{
  "success": true,
  "recommendations": [
    {
      "rank": 1,
      "source": "TK-12345",
      "source_type": "ticket",
      "solution": "重启链路设备，流量切换到备用路径",
      "description": "该案例与当前问题相似度 92%，通过链路切换解决了延迟问题",
      "confidence": 0.85,
      "estimated_time_minutes": 15,
      "risk_level": "low",
      "prerequisites": [
        "确认备用链路状态正常",
        "获得变更审批"
      ]
    },
    {
      "rank": 2,
      "source": "SOP-001",
      "source_type": "sop",
      "solution": "按照网络延迟排查流程执行",
      "description": "标准的延迟排查 SOP，包含完整的排查步骤",
      "confidence": 0.78,
      "estimated_time_minutes": 30,
      "risk_level": "none"
    },
    {
      "rank": 3,
      "source": "TK-12330",
      "source_type": "ticket",
      "solution": "调整负载均衡策略，降低问题链路权重",
      "description": "相似案例，通过调整负载均衡解决了问题",
      "confidence": 0.72,
      "estimated_time_minutes": 10,
      "risk_level": "medium",
      "prerequisites": [
        "确认负载均衡器配置权限"
      ]
    }
  ],
  "meta": {
    "total_candidates": 15,
    "filtered_by_context": true
  }
}
```

### 5.6 数据导入

#### 5.6.1 导入历史工单

```python
from src.knowledge import TicketParser, BGEEmbedding, QdrantRetriever

# 初始化组件
parser = TicketParser()
embedding = BGEEmbedding(model_name="BAAI/bge-m3")
retriever = QdrantRetriever(url="http://localhost:6333")

# 解析工单
raw_content = """
工单ID: TK-12345
标题: 新加坡区域网络延迟异常
问题描述: 2025-01-10 新加坡区域出现网络延迟突增...
根因: 链路拥塞
解决方案: 流量切换到备用链路
解决时间: 45分钟
"""

doc = parser.parse(raw_content)

# 生成向量
vector = embedding.embed_single(doc.content)

# 存入向量库
retriever.upsert(
    collection_name="oncall_tickets",
    doc_id=doc.doc_id,
    vector=vector,
    content=doc.content,
    metadata={
        "title": doc.title,
        "severity": doc.severity,
        "category": doc.category,
        "resolution_time_minutes": doc.resolution_time,
        "resolved_at": doc.resolved_at
    }
)
```

#### 5.6.2 批量导入脚本

```python
import asyncio
from pathlib import Path
from src.knowledge import KnowledgeImporter

async def import_tickets(data_dir: str):
    """批量导入历史工单"""
    importer = KnowledgeImporter()
    
    data_path = Path(data_dir)
    files = list(data_path.glob("*.json"))
    
    results = {
        "total": len(files),
        "success": 0,
        "failed": 0,
        "errors": []
    }
    
    for file in files:
        try:
            await importer.import_from_file(
                file_path=str(file),
                collection="oncall_tickets"
            )
            results["success"] += 1
        except Exception as e:
            results["failed"] += 1
            results["errors"].append({
                "file": str(file),
                "error": str(e)
            })
    
    return results

# 执行导入
if __name__ == "__main__":
    results = asyncio.run(import_tickets("./data/tickets"))
    print(f"导入完成: {results}")
```

### 5.7 向量配置详解

```yaml
# config/qdrant.yaml

# Qdrant 连接配置
connection:
  url: ${QDRANT_URL:http://localhost:6333}
  api_key: ${QDRANT_API_KEY:}
  timeout_seconds: 30

# Collection 配置
collections:
  oncall_tickets:
    description: "历史工单记录"
    vector_size: 1024
    distance: Cosine
    # 索引配置
    index:
      type: Hnsw
      m: 16
      ef_construct: 100
    # 存储配置
    storage:
      on_disk: true
      quantization: scalar  # scalar | product | binary

  sop_documents:
    description: "SOP 文档"
    vector_size: 1024
    distance: Cosine
    index:
      type: Hnsw
      m: 16

  solutions:
    description: "解决方案库"
    vector_size: 1024
    distance: Cosine

# Embedding 模型配置
embedding:
  model: BAAI/bge-m3
  max_length: 8192
  device: cpu  # cpu | cuda
  batch_size: 32
  normalize: true

  # 缓存配置
  cache:
    enabled: true
    max_size: 10000

# 检索配置
retrieval:
  # 混合检索权重
  vector_weight: 0.7
  keyword_weight: 0.3
  
  # 默认参数
  default_top_k: 5
  score_threshold: 0.5
  
  # 重排序配置
  rerank:
    enabled: true
    model: cross-encoder
    top_n: 20  # 重排序候选数量

# BM25 配置
bm25:
  k1: 1.5
  b: 0.75
  language: zh  # 中文分词
```

### 5.8 性能指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 查询延迟 (P50) | < 30ms | 中位数查询延迟 |
| 查询延迟 (P95) | < 50ms | 95% 分位查询延迟 |
| 查询延迟 (P99) | < 100ms | 99% 分位查询延迟 |
| 召回率 (Top-5) | > 85% | 前 5 结果的召回率 |
| 准确率 | > 80% | 返回结果的相关性 |
| 索引大小 | < 1GB | 10,000 文档的索引大小 |
| 向量生成延迟 | < 20ms | 单条文本向量化时间 |

---

## 六、自定义工具

### 6.1 ClickHouse Query Tool

#### 6.1.1 功能定位

查询 ClickHouse 中的网络测量数据，提供 Ping 和 Traceroute 数据的分析能力。

#### 6.1.2 工具元数据

```python
metadata = ToolMetadata(
    name="clickhouse_query",
    description="查询网络测量数据（Ping、Traceroute）",
    category=ToolCategory.DATABASE,
    version="1.0.0",
    author="Network Team"
)
```

#### 6.1.3 查询类型详解

| 查询类型 | 功能 | 输入参数 | 返回字段 |
|---------|------|---------|---------|
| `ping_stats` | Ping 统计 | region, group_by | avg_latency, p99, loss_rate |
| `ping_trend` | Ping 趋势 | region, interval, time_range | timestamp, latency_series |
| `trace_stats` | Traceroute 统计 | region, asn | path_count, unique_hops |
| `path_analysis` | 路径分析 | region, time_range | path_changes, route_flaps |
| `correlation` | 关联分析 | metrics, time_range | correlation_matrix |

#### 6.1.4 完整输入参数

```python
class ClickHouseQueryParams(BaseModel):
    """ClickHouse 查询参数"""
    
    # 必填参数
    query_type: str  # ping_stats | ping_trend | trace_stats | path_analysis | correlation
    region: str      # 地区名称，如 UKRAINE, RUSSIA
    
    # 时间范围
    start_time: Optional[str] = None  # ISO 格式，默认 1 小时前
    end_time: Optional[str] = None    # ISO 格式，默认当前时间
    
    # 过滤条件
    asn: Optional[int] = None         # AS 号过滤
    prefix24: Optional[str] = None    # /24 前缀过滤
    ip_address: Optional[str] = None  # IP 地址过滤
    
    # 分组和聚合
    group_by: Optional[List[str]] = None  # 分组字段，如 ["ip_asn", "region"]
    interval: Optional[str] = "hour"      # 时间间隔: minute | hour | day
    aggregations: Optional[List[str]] = None  # 聚合函数: avg, max, min, p99
    
    # 结果控制
    limit: Optional[int] = 100        # 返回数量限制
    offset: Optional[int] = 0         # 分页偏移
    
    # 高级选项
    use_cache: Optional[bool] = True  # 是否使用缓存
    timeout_ms: Optional[int] = 30000 # 查询超时
```

#### 6.1.5 使用示例

**示例 1：查询 Ping 统计数据**

```python
from src.tools import ClickHouseQueryTool

tool = ClickHouseQueryTool()

# 按 ASN 分组统计 Ping 数据
result = await tool.execute(
    query_type="ping_stats",
    region="UKRAINE",
    group_by=["ip_asn"],
    start_time="2025-01-15T00:00:00Z",
    end_time="2025-01-15T01:00:00Z"
)

print(result)
```

**输出：**

```json
{
  "success": true,
  "data": [
    {
      "ip_asn": 12345,
      "ip_asname": "Provider-A",
      "sample_count": 5000,
      "avg_latency_ms": 45.2,
      "p50_latency_ms": 42.0,
      "p95_latency_ms": 68.5,
      "p99_latency_ms": 82.1,
      "min_latency_ms": 32.1,
      "max_latency_ms": 120.5,
      "packet_loss_rate": 0.005
    },
    {
      "ip_asn": 67890,
      "ip_asname": "Provider-B",
      "sample_count": 3000,
      "avg_latency_ms": 52.3,
      "p99_latency_ms": 95.2,
      "packet_loss_rate": 0.008
    }
  ],
  "meta": {
    "query_time_ms": 125,
    "total_rows": 8000,
    "cache_hit": false
  }
}
```

**示例 2：查询延迟趋势**

```python
# 查询小时级延迟趋势
result = await tool.execute(
    query_type="ping_trend",
    region="UKRAINE",
    interval="hour",
    start_time="2025-01-14T00:00:00Z",
    end_time="2025-01-15T00:00:00Z"
)
```

**输出：**

```json
{
  "success": true,
  "data": [
    {
      "timestamp": "2025-01-14T00:00:00Z",
      "avg_latency_ms": 42.5,
      "p99_latency_ms": 75.2,
      "sample_count": 15000
    },
    {
      "timestamp": "2025-01-14T01:00:00Z",
      "avg_latency_ms": 43.1,
      "p99_latency_ms": 76.8,
      "sample_count": 14500
    },
    // ... 24 hours of data
  ],
  "meta": {
    "interval": "hour",
    "data_points": 24
  }
}
```

**示例 3：路径分析**

```python
# 分析网络路径变化
result = await tool.execute(
    query_type="path_analysis",
    region="RUSSIA",
    start_time="2025-01-15T00:00:00Z",
    end_time="2025-01-15T01:00:00Z"
)
```

**输出：**

```json
{
  "success": true,
  "data": {
    "total_paths": 150,
    "unique_paths": 12,
    "path_changes": 3,
    "route_flaps": [
      {
        "timestamp": "2025-01-15T00:15:00Z",
        "source_path": "AS1→AS2→AS3",
        "target_path": "AS1→AS4→AS3",
        "duration_seconds": 45
      }
    ],
    "top_paths": [
      {
        "path": "AS1→AS2→AS3→AS5",
        "count": 80,
        "avg_latency_ms": 45.2
      },
      {
        "path": "AS1→AS4→AS3→AS5",
        "count": 50,
        "avg_latency_ms": 52.8
      }
    ]
  }
}
```

#### 6.1.6 内部实现

```python
class ClickHouseQueryTool(BaseTool):
    """ClickHouse 查询工具实现"""
    
    def __init__(self, config: ClickHouseConfig):
        self.client = ClickHouseClient(config)
        self.queries = QueryBuilder()
        self.analyzer = PingAnalyzer()
    
    async def execute(self, **params) -> ToolResult:
        """执行查询"""
        try:
            # 1. 验证参数
            validated = self._validate_params(params)
            
            # 2. 构建 SQL
            sql = self._build_query(validated)
            
            # 3. 执行查询
            raw_data = await self.client.query(sql)
            
            # 4. 后处理
            if validated.query_type == "ping_stats":
                result = self.analyzer.analyze_stats(raw_data)
            elif validated.query_type == "ping_trend":
                result = self.analyzer.analyze_trend(raw_data)
            else:
                result = raw_data
            
            return ToolResult(success=True, data=result)
            
        except ClickHouseError as e:
            return ToolResult(
                success=False,
                error=f"ClickHouse error: {e.message}"
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
    
    def _build_query(self, params: ClickHouseQueryParams) -> str:
        """构建 SQL 查询"""
        if params.query_type == "ping_stats":
            return self.queries.build_ping_stats_query(params)
        elif params.query_type == "ping_trend":
            return self.queries.build_ping_trend_query(params)
        # ... other query types
```

---

### 6.2 Network Visualization Tool

#### 6.2.1 功能定位

网络测量数据可视化工具，支持 Traceroute 路径分析、Ping 时序分析、末端节点分析等，自动生成图表并返回 base64 编码的图片。

#### 6.2.2 工具元数据

```python
metadata = ToolMetadata(
    name="network_viz",
    description="网络测量数据可视化工具，支持 Traceroute 路径分析、Ping 时序分析、末端节点分析等",
    category=ToolCategory.NETWORK,
    version="1.0.0",
    author="Network Team"
)
```

#### 6.2.3 Action 类型详解

| Action | 功能 | 输入 | 输出 |
|--------|------|------|------|
| `ping_overall` | Ping 整体分析 | region | 延迟分布图、统计摘要 |
| `ping_trend` | Ping 趋势分析 | region, interval | 时序图、趋势线 |
| `ping_by_asn` | 按 ASN 分析 | region | 各 ASN 延迟对比图 |
| `ping_by_asgeo` | 按地理位置分析 | region | 各地区延迟对比图 |
| `ping_by_datacenter` | 按数据中心分析 | region | 各数据中心延迟对比 |
| `trace_terminal_analysis` | 末端节点分析 | region | 末端节点质量报告 |
| `trace_path_analysis` | 路径分析 | region, time_range | 路径变化统计 |
| `trace_path_detail` | 路径详情 | path | 具体路径节点图 |
| `trace_path_ping_trend` | 路径 Ping 趋势 | path | 路径延迟变化图 |
| `region_overview` | 区域概览 | region | 区域网络质量总览 |

#### 6.2.4 完整输入参数

```python
class NetworkVizParams(BaseModel):
    """网络可视化参数"""
    
    # 必填参数
    action: str    # 分析操作类型
    region: str    # 地区名称
    
    # 路径相关参数 (用于 path_detail 和 path_ping_trend)
    path: Optional[str] = None       # 路径字符串
    path_type: Optional[str] = "as"  # 路径类型: as | asgeo
    
    # 时间参数
    interval: Optional[str] = "hour"  # 时间间隔: minute | hour | day
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    
    # 图表配置
    chart_type: Optional[str] = "auto"  # auto | line | bar | scatter | heatmap
    width: Optional[int] = 800
    height: Optional[int] = 600
    dpi: Optional[int] = 100
    
    # 输出配置
    output_format: Optional[str] = "base64"  # base64 | file
    output_path: Optional[str] = None        # 文件输出路径
```

#### 6.2.5 使用示例

**示例 1：Ping 整体分析**

```python
from src.tools import NetworkVisualizationTool

tool = NetworkVisualizationTool()

result = await tool.execute(
    action="ping_overall",
    region="UKRAINE"
)
```

**输出：**

```json
{
  "success": true,
  "chart_base64": "iVBORw0KGgoAAAANSUhEUgAAA...(base64 encoded image)",
  "chart_type": "distribution",
  "analysis": {
    "total_samples": 10000,
    "time_range": {
      "start": "2025-01-15T00:00:00Z",
      "end": "2025-01-15T01:00:00Z"
    },
    "latency_stats": {
      "avg_ms": 45.2,
      "median_ms": 42.0,
      "p95_ms": 68.5,
      "p99_ms": 82.1,
      "std_dev_ms": 12.3
    },
    "loss_rate": 0.005,
    "anomaly_detected": true,
    "anomaly_ratio": 0.05
  },
  "insights": [
    "检测到 5% 的异常延迟样本",
    "主要异常时段: 2025-01-15 00:30 - 00:45",
    "P99 延迟 (82ms) 高于基线 (65ms) 26%",
    "建议检查链路拥塞情况"
  ]
}
```

**示例 2：路径分析**

```python
result = await tool.execute(
    action="trace_path_analysis",
    region="RUSSIA",
    start_time="2025-01-15T00:00:00Z",
    end_time="2025-01-15T01:00:00Z"
)
```

**输出：**

```json
{
  "success": true,
  "chart_base64": "iVBORw0KGgo...",
  "chart_type": "sankey",
  "analysis": {
    "total_traces": 500,
    "unique_paths": 8,
    "path_stability": 0.92,
    "top_paths": [
      {
        "path": "AS1239→AS20485→AS31133",
        "count": 350,
        "percentage": 70,
        "avg_latency_ms": 52.3
      },
      {
        "path": "AS1239→AS3216→AS31133",
        "count": 120,
        "percentage": 24,
        "avg_latency_ms": 48.5
      }
    ],
    "path_changes": [
      {
        "timestamp": "2025-01-15T00:20:00Z",
        "from_path": "AS1239→AS20485→AS31133",
        "to_path": "AS1239→AS3216→AS31133",
        "duration_seconds": 120
      }
    ]
  },
  "insights": [
    "主要路径占比 70%，网络较稳定",
    "检测到 1 次路径切换事件",
    "备用路径延迟更低 (48.5ms vs 52.3ms)"
  ]
}
```

**示例 3：末端节点分析**

```python
result = await tool.execute(
    action="trace_terminal_analysis",
    region="UKRAINE"
)
```

**输出：**

```json
{
  "success": true,
  "chart_base64": "iVBORw0KGgo...",
  "chart_type": "scatter",
  "analysis": {
    "total_terminals": 150,
    "quality_distribution": {
      "good": 120,      # latency < 50ms, loss < 1%
      "degraded": 25,   # latency 50-100ms, loss 1-5%
      "poor": 5         # latency > 100ms, loss > 5%
    },
    "problematic_terminals": [
      {
        "ip": "192.168.1.100",
        "asn": 12345,
        "avg_latency_ms": 150.5,
        "loss_rate": 0.08,
        "issue": "high_latency_and_loss"
      }
    ],
    "recommendations": [
      "5 个末端节点质量较差，建议检查",
      "节点 192.168.1.100 存在高延迟和丢包"
    ]
  }
}
```

#### 6.2.6 图表类型说明

| 图表类型 | 使用场景 | 说明 |
|---------|---------|------|
| `distribution` | Ping 整体分析 | 延迟分布直方图 |
| `line` | 趋势分析 | 时序折线图 |
| `bar` | 分组对比 | 各维度延迟对比 |
| `scatter` | 散点分布 | 末端节点分布 |
| `sankey` | 路径分析 | 路径流量桑基图 |
| `heatmap` | 时热图 | 24 小时延迟热力图 |
| `boxplot` | 箱线图 | 延迟分布箱线图 |

#### 6.2.7 中文字体支持

工具自动检测并使用系统中的中文字体：

```python
def get_chinese_font():
    """获取支持中文的字体"""
    preferred_fonts = [
        'PingFang HK',      # macOS
        'PingFang SC',      # macOS
        'SimHei',           # Windows
        'Microsoft YaHei',  # Windows
        'WenQuanYi Micro Hei',  # Linux
    ]
    
    available_fonts = set([f.name for f in fm.fontManager.ttflist])
    
    for font in preferred_fonts:
        if font in available_fonts:
            return font
    
    return 'DejaVu Sans'  # 默认字体
```

---

## 七、数据模型

### 7.1 告警数据模型

```python
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict, Any
from enum import Enum

class Severity(str, Enum):
    """告警严重级别"""
    WARNING = "warning"
    CRITICAL = "critical"
    INFO = "info"

class AlertCategory(str, Enum):
    """告警分类"""
    NETWORK = "network"
    SERVICE = "service"
    DATABASE = "database"
    STORAGE = "storage"
    SECURITY = "security"

class AlertInfo(BaseModel):
    """告警信息"""
    alert_id: str = Field(..., description="告警唯一标识")
    title: str = Field(..., description="告警标题")
    description: Optional[str] = Field(None, description="告警描述")
    severity: Severity = Field(..., description="严重级别")
    category: AlertCategory = Field(..., description="告警分类")
    
    # 实体信息
    region: Optional[str] = Field(None, description="区域")
    service: Optional[str] = Field(None, description="服务名")
    psm: Optional[str] = Field(None, description="PSM")
    
    # 时间信息
    triggered_at: datetime = Field(..., description="触发时间")
    resolved_at: Optional[datetime] = Field(None, description="解决时间")
    
    # 指标信息
    metric_name: Optional[str] = Field(None, description="指标名")
    metric_value: Optional[float] = Field(None, description="指标值")
    threshold: Optional[float] = Field(None, description="阈值")
    
    # 标签
    tags: Dict[str, str] = Field(default_factory=dict, description="标签")
    
    class Config:
        json_schema_extra = {
            "example": {
                "alert_id": "ALT-12345",
                "title": "网络延迟突增",
                "description": "新加坡区域 P99 延迟从 45ms 上升到 180ms",
                "severity": "critical",
                "category": "network",
                "region": "Singapore-Central",
                "triggered_at": "2025-01-15T00:30:00Z",
                "metric_name": "p99_latency_ms",
                "metric_value": 180.5,
                "threshold": 100.0,
                "tags": {"env": "prod", "team": "network"}
            }
        }
```

### 7.2 诊断结果模型

```python
class RootCause(BaseModel):
    """根因信息"""
    category: str = Field(..., description="根因类别")
    subcategory: str = Field(..., description="根因子类别")
    description: str = Field(..., description="根因描述")
    confidence: float = Field(..., ge=0, le=1, description="置信度")
    confidence_level: str = Field(..., description="置信度等级")

class Evidence(BaseModel):
    """证据信息"""
    source: str = Field(..., description="数据来源")
    type: str = Field(..., description="证据类型")
    details: Dict[str, Any] = Field(..., description="详细信息")

class Recommendation(BaseModel):
    """建议信息"""
    priority: int = Field(..., ge=1, le=10, description="优先级")
    action: str = Field(..., description="建议动作")
    rationale: str = Field(..., description="建议理由")
    estimated_time_minutes: Optional[int] = Field(None, description="预计耗时")
    risk_level: Optional[str] = Field(None, description="风险等级")

class DiagnosisResult(BaseModel):
    """诊断结果"""
    session_id: str = Field(..., description="会话 ID")
    timestamp: datetime = Field(..., description="诊断时间")
    duration_ms: int = Field(..., description="诊断耗时")
    
    # 根因
    root_cause: RootCause = Field(..., description="根因信息")
    
    # 证据链
    evidence: List[Evidence] = Field(default_factory=list, description="证据列表")
    
    # 建议
    recommendations: List[Recommendation] = Field(
        default_factory=list, 
        description="建议列表"
    )
    
    # 相关数据
    related_data: Optional[Dict[str, Any]] = Field(None, description="相关数据")
```

### 7.3 网络数据模型

```python
class LatencyData(BaseModel):
    """延迟数据"""
    timestamp: datetime
    source_region: str
    target_region: str
    sample_count: int
    
    # 延迟统计
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    p50_latency_ms: float
    p95_latency_ms: float
    p99_latency_ms: float
    std_dev_ms: float
    
    # 丢包
    packet_loss_rate: float

class AnomalyEvent(BaseModel):
    """异常事件"""
    event_id: str
    event_type: str
    severity: str
    source_region: str
    target_region: Optional[str]
    occurred_at: datetime
    metric_value: float
    baseline_value: float
    deviation_ratio: float
    duration_seconds: Optional[int]
    description: str

class LinkQuality(BaseModel):
    """链路质量"""
    link_id: str
    source_region: str
    target_region: str
    
    # RTT
    avg_rtt_ms: float
    min_rtt_ms: float
    max_rtt_ms: float
    
    # 抖动和丢包
    jitter_ms: float
    loss_rate: float
    
    # 跳数
    hop_count: int
    
    # 健康状态
    health_score: int
    status: str  # healthy | degraded | unhealthy
    
    last_updated: datetime
```

### 7.4 知识库数据模型

```python
class KnowledgeDocument(BaseModel):
    """知识库文档"""
    doc_id: str
    doc_type: str  # ticket | sop | solution
    title: str
    content: str
    
    # 向量信息
    vector: Optional[List[float]] = None
    vector_dimension: int = 1024
    
    # 相似度
    score: Optional[float] = None
    vector_score: Optional[float] = None
    keyword_score: Optional[float] = None
    
    # 元数据
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # 高亮
    highlights: Optional[List[str]] = None

class SOPDocument(BaseModel):
    """SOP 文档"""
    sop_id: str
    title: str
    category: str
    description: str
    
    steps: List[Dict[str, Any]]
    related_sops: List[str]
    
    last_updated: datetime
    version: str

class Solution(BaseModel):
    """解决方案"""
    solution_id: str
    title: str
    description: str
    
    # 适用条件
    applicable_conditions: Dict[str, Any]
    
    # 解决步骤
    steps: List[str]
    
    # 效果评估
    success_rate: Optional[float] = None
    avg_resolution_time_minutes: Optional[int] = None
```

---

## 八、配置详解

### 8.1 应用配置

```yaml
# config/app.yaml

# 应用基础配置
app:
  name: "Network Telemetry Analysis Platform"
  version: "3.0.0"
  environment: ${ENVIRONMENT:development}
  debug: ${DEBUG:false}
  log_level: ${LOG_LEVEL:INFO}

# 服务配置
server:
  http:
    host: "0.0.0.0"
    port: ${HTTP_PORT:8000}
  grpc:
    host: "0.0.0.0"
    port: ${GRPC_PORT:50051}

# 安全配置
security:
  enable_tls: ${ENABLE_TLS:false}
  cors:
    allowed_origins: ["*"]
    allowed_methods: ["GET", "POST", "PUT", "DELETE"]
```

### 8.2 数据库配置

```yaml
# config/database.yaml

# ClickHouse 配置
clickhouse:
  host: ${CLICKHOUSE_HOST:localhost}
  port: ${CLICKHOUSE_PORT:8123}
  database: ${CLICKHOUSE_DATABASE:network_telemetry}
  user: ${CLICKHOUSE_USER:default}
  password: ${CLICKHOUSE_PASSWORD:}
  secure: ${CLICKHOUSE_SECURE:true}
  timeout_seconds: 30
  
  pool:
    max_connections: 10
    min_connections: 2
    idle_timeout_seconds: 300

# Qdrant 配置
qdrant:
  url: ${QDRANT_URL:http://localhost:6333}
  api_key: ${QDRANT_API_KEY:}
  timeout_seconds: 30

# Neo4j 配置
neo4j:
  uri: ${NEO4J_URI:bolt://localhost:7687}
  user: ${NEO4J_USER:neo4j}
  password: ${NEO4J_PASSWORD:password}
  max_connection_pool_size: 50

# Redis 配置
redis:
  url: ${REDIS_URL:redis://localhost:6379}
  db: ${REDIS_DB:0}
  password: ${REDIS_PASSWORD:}
  max_connections: 10

# MinIO 配置
minio:
  endpoint: ${MINIO_ENDPOINT:localhost:9000}
  access_key: ${MINIO_ACCESS_KEY:minioadmin}
  secret_key: ${MINIO_SECRET_KEY:minioadmin}
  secure: ${MINIO_SECURE:false}
  bucket: ${MINIO_BUCKET:knowledge}
```

### 8.3 LLM 配置

```yaml
# config/llm.yaml

# OpenAI 配置
openai:
  api_key: ${OPENAI_API_KEY:}
  base_url: ${OPENAI_BASE_URL:}
  model: ${OPENAI_MODEL:gpt-4o}
  temperature: 0.7
  max_tokens: 4096

# Anthropic 配置
anthropic:
  api_key: ${ANTHROPIC_API_KEY:}
  model: ${ANTHROPIC_MODEL:claude-sonnet-4-20250514}
  temperature: 0.7
  max_tokens: 4096

# Embedding 配置
embedding:
  model: "BAAI/bge-m3"
  max_length: 8192
  device: "cpu"
  batch_size: 32
```

---

## 九、API 接口

### 9.1 诊断接口

#### POST /api/v1/diagnosis/start

启动诊断任务。

**请求体：**

```json
{
  "alert_id": "ALT-12345",
  "title": "网络延迟突增",
  "description": "新加坡区域 P99 延迟从 45ms 上升到 180ms",
  "severity": "critical",
  "region": "Singapore-Central",
  "triggered_at": "2025-01-15T00:30:00Z"
}
```

**响应：**

```json
{
  "success": true,
  "session_id": "diag-20250115-001",
  "status": "running"
}
```

#### GET /api/v1/diagnosis/{session_id}

获取诊断结果。

**响应：**

```json
{
  "success": true,
  "session_id": "diag-20250115-001",
  "status": "completed",
  "result": {
    "root_cause": {
      "category": "network",
      "subcategory": "latency",
      "description": "网络延迟异常，由链路拥塞导致",
      "confidence": 0.88
    },
    "recommendations": [
      "1. 检查链路拥塞情况",
      "2. 参考历史案例 TK-12345"
    ]
  }
}
```

### 9.2 查询接口

#### POST /api/v1/telemetry/query

查询网络测量数据。

**请求体：**

```json
{
  "action": "query_latency",
  "params": {
    "start_time": "2025-01-15T00:00:00Z",
    "end_time": "2025-01-15T01:00:00Z",
    "region": "Singapore-Central"
  }
}
```

**响应：**

```json
{
  "success": true,
  "data": [...]
}
```

### 9.3 知识检索接口

#### POST /api/v1/knowledge/search

检索知识库。

**请求体：**

```json
{
  "query": "网络延迟突增",
  "top_k": 5,
  "doc_type": "ticket"
}
```

**响应：**

```json
{
  "success": true,
  "results": [...]
}
```

---

## 十、错误处理

### 10.1 错误码定义

| 错误码 | 说明 | HTTP 状态码 |
|-------|------|------------|
| `SUCCESS` | 成功 | 200 |
| `INVALID_PARAMS` | 参数无效 | 400 |
| `NOT_FOUND` | 资源不存在 | 404 |
| `TIMEOUT` | 请求超时 | 504 |
| `INTERNAL_ERROR` | 内部错误 | 500 |
| `DB_ERROR` | 数据库错误 | 500 |
| `LLM_ERROR` | LLM 服务错误 | 503 |

### 10.2 错误响应格式

```json
{
  "success": false,
  "error": {
    "code": "INVALID_PARAMS",
    "message": "Invalid parameter: region is required",
    "details": {
      "field": "region",
      "constraint": "required"
    }
  }
}
```

### 10.3 常见错误处理

```python
class ErrorHandler:
    """错误处理器"""
    
    @staticmethod
    def handle_clickhouse_error(error: Exception) -> dict:
        """处理 ClickHouse 错误"""
        if "Connection refused" in str(error):
            return {
                "code": "DB_ERROR",
                "message": "ClickHouse 服务不可达，请检查网络连接"
            }
        elif "Authentication failed" in str(error):
            return {
                "code": "DB_ERROR",
                "message": "ClickHouse 认证失败，请检查配置"
            }
        elif "Timeout" in str(error):
            return {
                "code": "TIMEOUT",
                "message": "查询超时，请缩小查询范围"
            }
        else:
            return {
                "code": "DB_ERROR",
                "message": f"数据库错误: {str(error)}"
            }
    
    @staticmethod
    def handle_llm_error(error: Exception) -> dict:
        """处理 LLM 服务错误"""
        if "Rate limit" in str(error):
            return {
                "code": "LLM_ERROR",
                "message": "LLM 服务限流，请稍后重试"
            }
        elif "Invalid API key" in str(error):
            return {
                "code": "LLM_ERROR",
                "message": "LLM API Key 无效"
            }
        else:
            return {
                "code": "LLM_ERROR",
                "message": f"LLM 服务错误: {str(error)}"
            }
```

---

## 十一、Skills 协作流程

### 11.1 完整诊断流程

```
┌─────────────────────────────────────────────────────────────┐
│                        告警触发                              │
│                                                              │
│  • Argos 告警回调                                            │
│  • 用户手动发起                                              │
│  • 定时巡检发现                                              │
└─────────────────────────────┬───────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                  Intelligent Diagnosis                       │
│                      (诊断编排层)                             │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Step 1: 解析告警信息，提取关键实体                    │    │
│  │          • 区域: Singapore-Central                   │    │
│  │          • 问题: 延迟突增                             │    │
│  │          • 严重级别: critical                         │    │
│  └─────────────────────────────────────────────────────┘    │
│                              ↓                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Step 2: 并行调用其他 Skills                          │    │
│  │                                                       │    │
│  │    ┌──────────────────┐  ┌──────────────────┐       │    │
│  │    │ Network Telemetry│  │ Knowledge Search │       │    │
│  │    │                  │  │                  │       │    │
│  │    │ • 查询延迟数据    │  │ • 检索历史案例   │       │    │
│  │    │ • 查询异常事件    │  │ • 匹配 SOP 文档  │       │    │
│  │    │ • 检查链路质量    │  │ • 推荐解决方案   │       │    │
│  │    └──────────────────┘  └──────────────────┘       │    │
│  │             │                     │                  │    │
│  │             └──────────┬──────────┘                  │    │
│  │                        ↓                              │    │
│  │  Step 3: 综合分析，计算置信度                          │    │
│  │          • 根因分类                                   │    │
│  │          • 置信度计算                                 │    │
│  │          • 证据链构建                                 │    │
│  └─────────────────────────────────────────────────────┘    │
│                              ↓                               │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  Step 4: 生成诊断报告和解决方案                        │    │
│  │          • 根因描述                                   │    │
│  │          • 建议列表                                   │    │
│  │          • 可视化图表                                 │    │
│  └─────────────────────────────────────────────────────┘    │
│                                                              │
└─────────────────────────────┬───────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────┐
│                       诊断报告输出                           │
│                                                              │
│  • 根因分类: network > latency                               │
│  • 置信度: 88%                                               │
│  • 证据链: 4 条证据                                          │
│  • 建议: 4 条建议                                            │
│  • 图表: 延迟趋势图、路径分析图                              │
└─────────────────────────────────────────────────────────────┘
```

### 11.2 工具调用关系

```
┌─────────────────────────────────────────────────────────────┐
│                  Intelligent Diagnosis (Skill)              │
└─────────────────────────────┬───────────────────────────────┘
                              │
            ┌─────────────────┴─────────────────┐
            ↓                                   ↓
┌───────────────────────┐           ┌───────────────────────┐
│   Network Telemetry   │           │   Knowledge Search    │
│       (Skill)         │           │       (Skill)         │
└───────────┬───────────┘           └───────────┬───────────┘
            │                                   │
            ↓                                   ↓
┌───────────────────────┐           ┌───────────────────────┐
│ ClickHouse Query Tool │           │    Vector Database    │
│                       │           │      (Qdrant)         │
└───────────┬───────────┘           └───────────────────────┘
            │                                   │
            ↓                                   ↓
┌───────────────────────┐           ┌───────────────────────┐
│   ClickHouse (DB)     │           │  Embedding (BGE-M3)   │
└───────────────────────┘           └───────────────────────┘
            │
            ↓
┌───────────────────────┐
│ Network Visualization │
│        Tool           │
└───────────────────────┘
```

---

## 十二、部署说明

### 12.1 环境要求

| 组件 | 版本要求 |
|------|---------|
| Python | >= 3.9 |
| Go | >= 1.20 |
| Docker | >= 20.0 |
| Docker Compose | >= 2.0 |

### 12.2 Docker Compose 配置

```yaml
# docker/docker-compose.yml
version: '3.8'

services:
  # ClickHouse
  clickhouse:
    image: clickhouse/clickhouse-server:latest
    ports:
      - "8123:8123"
      - "9000:9000"
    environment:
      CLICKHOUSE_DB: network_telemetry
      CLICKHOUSE_USER: default
      CLICKHOUSE_PASSWORD: ${CLICKHOUSE_PASSWORD}
    volumes:
      - clickhouse-data:/var/lib/clickhouse
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8123/ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  # Qdrant
  qdrant:
    image: qdrant/qdrant:latest
    ports:
      - "6333:6333"
    volumes:
      - qdrant-data:/qdrant/storage

  # Neo4j
  neo4j:
    image: neo4j:5-community
    ports:
      - "7474:7474"
      - "7687:7687"
    environment:
      NEO4J_AUTH: neo4j/${NEO4J_PASSWORD}

  # Redis
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

  # MinIO
  minio:
    image: minio/minio:latest
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: ${MINIO_ACCESS_KEY}
      MINIO_ROOT_PASSWORD: ${MINIO_SECRET_KEY}
    command: server /data --console-address ":9001"

volumes:
  clickhouse-data:
  qdrant-data:
```

### 12.3 启动命令

```bash
# 1. 启动基础设施
cd docker && docker-compose up -d

# 2. 安装 Python 依赖
pip install -r requirements.txt

# 3. 初始化数据库
python scripts/init_db.py

# 4. 导入知识库数据
python scripts/import_knowledge.py --source ./data/tickets

# 5. 启动服务
python main.py
```

---

## 十三、测试相关

### 13.1 单元测试

```python
import pytest
from src.skills import IntelligentDiagnosis

class TestIntelligentDiagnosis:
    
    @pytest.fixture
    def skill(self):
        return IntelligentDiagnosis()
    
    @pytest.mark.asyncio
    async def test_diagnose_alert(self, skill):
        """测试告警诊断"""
        alert = {
            "alert_id": "TEST-001",
            "title": "网络延迟突增",
            "region": "Singapore-Central",
            "severity": "critical"
        }
        
        result = await skill.execute(
            action="diagnose_alert",
            params=alert
        )
        
        assert result.success
        assert "root_cause" in result.data
        assert result.data["root_cause"]["confidence"] > 0
```

### 13.2 集成测试

```python
import pytest
from src.tools import ClickHouseQueryTool
from src.config import ClickHouseConfig

@pytest.mark.integration
class TestClickHouseIntegration:
    
    @pytest.fixture
    def tool(self):
        config = ClickHouseConfig.from_env()
        return ClickHouseQueryTool(config)
    
    @pytest.mark.asyncio
    async def test_query_latency(self, tool):
        """测试延迟查询"""
        result = await tool.execute(
            query_type="ping_stats",
            region="UKRAINE",
            group_by=["ip_asn"]
        )
        
        assert result.success
        assert len(result.data) > 0
```

### 13.3 性能测试

```python
import pytest
import time
from src.skills import KnowledgeSearch

@pytest.mark.performance
class TestKnowledgeSearchPerformance:
    
    @pytest.mark.asyncio
    async def test_search_latency(self):
        """测试检索延迟"""
        skill = KnowledgeSearch()
        
        start_time = time.time()
        result = await skill.execute(
            action="search_similar",
            params={"query": "网络延迟突增", "top_k": 5}
        )
        latency_ms = (time.time() - start_time) * 1000
        
        assert latency_ms < 50  # P95 延迟 < 50ms
        assert result.success
```

---

## 十四、技术栈总结

### 14.1 核心依赖

| 组件 | 用途 | 技术选型 | 版本 |
|------|------|---------|------|
| 数据存储 | 网络测量数据 | ClickHouse | >= 23.0 |
| 向量数据库 | 知识库存储与检索 | Qdrant | >= 1.7 |
| 知识图谱 | 故障关联分析 | Neo4j | >= 5.0 |
| 缓存 | Session 缓存 | Redis | >= 7.0 |
| 对象存储 | 图表和报告存储 | MinIO | latest |
| Embedding | 文本向量化 | BGE-M3 | latest |

### 14.2 框架和库

| 类别 | 技术 | 版本 |
|------|------|------|
| Web 框架 | FastAPI | >= 0.109 |
| gRPC | grpcio | >= 1.60 |
| LLM SDK | openai, anthropic | latest |
| 向量客户端 | qdrant-client | >= 1.7 |
| 图表生成 | matplotlib | >= 3.7 |
| 数据处理 | pydantic, httpx | latest |

### 14.3 技术特点

1. **多 Agent 协作**：Knowledge Agent、Analysis Agent、Diagnosis Agent 协同工作
2. **RAG 知识增强**：结合向量检索和关键词检索的混合检索策略
3. **实时数据分析**：连接 ClickHouse 实时查询网络测量数据
4. **智能可视化**：自动生成 Traceroute 路径图、Ping 趋势图等
5. **置信度评分**：多维度计算诊断结果的可信程度

---

## 十五、性能指标

### 15.1 系统性能指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| 诊断延迟 | < 2s | 并行模式下的端到端诊断时间 |
| 检索准确率 | > 85% | Top-5 召回率 |
| 根因准确率 | > 80% | 评估得分 |
| 查询延迟 (P95) | < 50ms | 知识库检索延迟 |
| 查询延迟 (P99) | < 100ms | 知识库检索延迟 |
| 向量生成延迟 | < 20ms | 单条文本向量化时间 |

### 15.2 业务指标

| 指标 | 目标值 | 说明 |
|------|--------|------|
| MTTR 降低 | 60-80% | 相比人工诊断 |
| 自动诊断率 | > 70% | 无需人工介入 |
| 知识命中率 | > 85% | 找到相关历史案例 |

---

## 十六、版本历史

| 版本 | 日期 | 更新内容 |
|------|------|---------|
| v1.0 | 2025-01 | 基础 Agent 框架 + ClickHouse 查询 |
| v2.0 | 2025-03 | 动态工具 + RAG 知识检索 + 知识图谱 |
| v3.0 | 2025-05 | 思考过程可视化 + 自然语言可视化 + 多 Agent 协作 |

---

## 十七、最佳实践

### 17.1 Skill 使用最佳实践

#### 17.1.1 Intelligent Diagnosis 使用建议

| 场景 | 建议 |
|------|------|
| 告警触发诊断 | 确保告警信息完整，包含 region、service、metric 等关键字段 |
| 批量诊断 | 使用异步模式，设置合理的并发数（建议不超过 10） |
| 复杂故障 | 启用详细日志模式，便于追踪 Agent 决策过程 |
| 低置信度结果 | 人工复核，补充更多上下文信息后重新诊断 |

#### 17.1.2 Network Telemetry 查询优化

```python
# ✅ 推荐：合理设置时间范围
result = await telemetry.query_latency(
    start_time="2025-01-15T00:00:00Z",
    end_time="2025-01-15T01:00:00Z",  # 限制在 1 小时内
    region="Singapore-Central"
)

# ❌ 不推荐：查询过长时间范围
result = await telemetry.query_latency(
    start_time="2025-01-01T00:00:00Z",
    end_time="2025-01-15T00:00:00Z",  # 15 天数据，查询慢
    region="Singapore-Central"
)
```

**查询优化建议：**

| 优化点 | 方法 |
|--------|------|
| 时间范围 | 限制在必要的时间范围内，避免全量扫描 |
| 分组字段 | 只选择需要的分组字段，减少聚合计算 |
| 缓存利用 | 相同查询使用缓存，设置合理的 TTL |
| 异步查询 | 大批量查询使用异步模式，避免阻塞 |

#### 17.1.3 Knowledge Search 检索技巧

```python
# ✅ 推荐：提供详细的查询描述
result = await knowledge_search.search_similar(
    query="新加坡区域在 2025 年 1 月出现的网络延迟突增问题，P99 延迟从 45ms 上升到 180ms",
    top_k=5,
    doc_type="ticket"
)

# ❌ 不推荐：过于简短的查询
result = await knowledge_search.search_similar(
    query="延迟高",
    top_k=5
)
```

**查询质量提升技巧：**

| 技巧 | 说明 |
|------|------|
| 包含关键实体 | 查询中包含区域、服务、指标等关键实体 |
| 描述具体现象 | 描述具体的异常现象（如 P99 从 X 上升到 Y） |
| 使用专业术语 | 使用网络运维专业术语（如延迟、丢包、链路） |
| 结合上下文 | 利用 context 参数传递补充信息 |

### 17.2 数据建模最佳实践

#### 17.2.1 告警信息规范

```python
# 标准告警信息格式
alert = {
    "alert_id": "ALT-20250115-001",      # 唯一标识
    "title": "网络延迟突增",              # 简洁明了的标题
    "description": "新加坡区域 P99 延迟从 45ms 上升到 180ms，持续时间 15 分钟",  # 详细描述
    "severity": "critical",              # 严重级别
    "category": "network",               # 分类
    "region": "Singapore-Central",       # 区域
    "service": "api-gateway",            # 服务
    "metric_name": "p99_latency_ms",     # 指标名
    "metric_value": 180.5,               # 指标值
    "threshold": 100.0,                  # 阈值
    "triggered_at": "2025-01-15T00:30:00Z",  # 触发时间
    "tags": {                            # 标签
        "env": "prod",
        "team": "network",
        "oncall": "user@example.com"
    }
}
```

#### 17.2.2 知识库文档规范

```markdown
# 工单模板

## 基本信息
- 工单ID: TK-XXXXX
- 标题: [区域] [问题类型] [简要描述]
- 严重级别: critical/warning/info
- 分类: network/service/database
- 状态: resolved

## 问题描述
[详细描述问题现象，包括时间、区域、影响范围]

## 根因分析
[根因分析过程和结论]

## 解决方案
[具体的解决步骤]

## 效果验证
[验证问题已解决的证据]

## 预防措施
[防止问题再次发生的措施]

## 关联信息
- 相关工单: TK-XXXXX
- 相关 SOP: SOP-XXX
- 相关服务: XXX
```

### 17.3 性能优化最佳实践

#### 17.3.1 查询性能优化

```python
# 使用连接池
from src.clickhouse import ClickHousePool

# 初始化连接池
pool = ClickHousePool(
    max_connections=10,
    min_connections=2,
    idle_timeout_seconds=300
)

# 复用连接
async def query_with_pool():
    async with pool.acquire() as conn:
        result = await conn.query("SELECT ...")
    return result
```

#### 17.3.2 缓存策略

```python
from functools import lru_cache
from datetime import datetime, timedelta
import hashlib

class QueryCache:
    """查询缓存"""
    
    def __init__(self, ttl_seconds: int = 60):
        self.cache = {}
        self.ttl = ttl_seconds
    
    def get_key(self, query_type: str, params: dict) -> str:
        """生成缓存键"""
        content = f"{query_type}:{sorted(params.items())}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def get(self, key: str) -> Optional[dict]:
        """获取缓存"""
        if key in self.cache:
            entry = self.cache[key]
            if datetime.now() < entry["expires_at"]:
                return entry["data"]
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, data: dict):
        """设置缓存"""
        self.cache[key] = {
            "data": data,
            "expires_at": datetime.now() + timedelta(seconds=self.ttl)
        }
```

### 17.4 可靠性最佳实践

#### 17.4.1 重试机制

```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True
)
async def query_with_retry(query: str):
    """带重试的查询"""
    return await client.query(query)
```

#### 17.4.2 熔断机制

```python
from circuitbreaker import circuit

class QueryService:
    
    @circuit(failure_threshold=5, recovery_timeout=30)
    async def query_clickhouse(self, query: str):
        """带熔断的 ClickHouse 查询"""
        return await self.client.query(query)
```

#### 17.4.3 超时控制

```python
import asyncio

async def query_with_timeout(query: str, timeout_seconds: int = 30):
    """带超时的查询"""
    try:
        result = await asyncio.wait_for(
            client.query(query),
            timeout=timeout_seconds
        )
        return result
    except asyncio.TimeoutError:
        raise QueryTimeoutError(f"Query timed out after {timeout_seconds}s")
```

---

## 十八、故障排查指南

### 18.1 常见问题诊断流程

```
┌─────────────────────────────────────────────────────────────┐
│                      问题报告                                │
└─────────────────────────┬───────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 1: 检查服务状态                                         │
│                                                              │
│ • 检查 API 服务是否正常响应                                  │
│ • 检查日志中是否有错误信息                                   │
│ • 检查资源使用情况（CPU、内存、磁盘）                        │
└─────────────────────────┬───────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 2: 检查依赖服务                                         │
│                                                              │
│ • ClickHouse 连接是否正常                                    │
│ • Qdrant 服务是否正常                                        │
│ • Redis 缓存是否正常                                         │
│ • LLM 服务是否可用                                           │
└─────────────────────────┬───────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 3: 分析具体错误                                         │
│                                                              │
│ • 查看错误码和错误信息                                       │
│ • 检查请求参数是否正确                                       │
│ • 检查配置是否正确                                           │
└─────────────────────────┬───────────────────────────────────┘
                          ↓
┌─────────────────────────────────────────────────────────────┐
│ Step 4: 定位问题根因                                         │
│                                                              │
│ • 网络问题 → 检查网络连接                                    │
│ • 配置问题 → 检查配置文件                                    │
│ • 数据问题 → 检查数据源                                      │
│ • 代码问题 → 检查日志和代码                                  │
└─────────────────────────────────────────────────────────────┘
```

### 18.2 常见错误及解决方案

#### 18.2.1 ClickHouse 连接问题

| 错误信息 | 可能原因 | 解决方案 |
|---------|---------|---------|
| `Connection refused` | 服务未启动或端口错误 | 检查 ClickHouse 服务状态，确认端口配置 |
| `Authentication failed` | 用户名或密码错误 | 检查用户名密码配置，确认权限 |
| `Timeout` | 查询超时或网络延迟 | 优化查询，增加超时时间，检查网络 |
| `Too many connections` | 连接数超限 | 增加最大连接数，检查连接泄漏 |

**诊断命令：**

```bash
# 检查 ClickHouse 服务状态
curl http://localhost:8123/ping

# 检查连接数
curl "http://localhost:8123/?query=SELECT%20count()%20FROM%20system.processes"

# 检查正在执行的查询
curl "http://localhost:8123/?query=SELECT%20*%20FROM%20system.processes"
```

#### 18.2.2 Qdrant 向量库问题

| 错误信息 | 可能原因 | 解决方案 |
|---------|---------|---------|
| `Collection not found` | Collection 未创建 | 创建对应的 Collection |
| `Vector dimension mismatch` | 向量维度不匹配 | 检查 Embedding 模型配置 |
| `Index out of memory` | 内存不足 | 增加内存或优化索引配置 |
| `Search timeout` | 查询超时 | 减少查询数量，优化索引 |

**诊断命令：**

```bash
# 检查 Qdrant 服务状态
curl http://localhost:6333/collections

# 检查 Collection 信息
curl http://localhost:6333/collections/oncall_tickets

# 检查索引状态
curl http://localhost:6333/collections/oncall_tickets/index
```

#### 18.2.3 LLM 服务问题

| 错误信息 | 可能原因 | 解决方案 |
|---------|---------|---------|
| `Rate limit exceeded` | 请求频率过高 | 降低请求频率，实现重试机制 |
| `Invalid API key` | API Key 无效 | 检查 API Key 配置 |
| `Model not found` | 模型名称错误 | 检查模型名称配置 |
| `Context length exceeded` | 输入过长 | 减少输入长度，分段处理 |

### 18.3 日志分析

#### 18.3.1 日志级别说明

| 级别 | 说明 | 示例场景 |
|------|------|---------|
| DEBUG | 调试信息 | 详细的执行流程 |
| INFO | 正常信息 | 请求开始/结束 |
| WARNING | 警告信息 | 可恢复的异常 |
| ERROR | 错误信息 | 需要关注的错误 |
| CRITICAL | 严重错误 | 服务不可用 |

#### 18.3.2 关键日志关键字

| 关键字 | 含义 | 处理建议 |
|--------|------|---------|
| `ConnectionError` | 连接错误 | 检查网络和服务状态 |
| `TimeoutError` | 超时错误 | 增加超时时间或优化查询 |
| `RateLimited` | 限流 | 降低请求频率 |
| `CircuitOpen` | 熔断开启 | 检查下游服务状态 |
| `AuthenticationFailed` | 认证失败 | 检查凭证配置 |

#### 18.3.3 日志查询示例

```bash
# 查询最近 1 小时的错误日志
grep -E "ERROR|CRITICAL" /var/log/app.log | tail -100

# 查询特定请求的日志
grep "session_id=diag-20250115-001" /var/log/app.log

# 实时监控日志
tail -f /var/log/app.log | grep --line-buffered "ERROR"
```

### 18.4 性能问题排查

#### 18.4.1 查询慢问题

**排查步骤：**

1. 确认查询的 SQL 语句
2. 使用 EXPLAIN 分析查询计划
3. 检查是否有合适的索引
4. 分析数据量和分区情况

```sql
-- 分析查询计划
EXPLAIN PLAN FOR
SELECT avg_latency_ms, p99_latency_ms
FROM network_latency
WHERE region = 'Singapore-Central'
  AND timestamp BETWEEN '2025-01-15 00:00:00' AND '2025-01-15 01:00:00'

-- 检查分区信息
SELECT partition, name, rows, bytes_on_disk
FROM system.parts
WHERE table = 'network_latency'
  AND active
ORDER BY partition DESC
LIMIT 10
```

#### 18.4.2 内存使用问题

**排查命令：**

```bash
# 检查进程内存使用
ps aux --sort=-%mem | head -20

# 检查 Python 内存使用
python -c "
import tracemalloc
tracemalloc.start()
# ... 运行代码 ...
snapshot = tracemalloc.take_snapshot()
for stat in snapshot.statistics('lineno')[:10]:
    print(stat)
"
```

---

## 十九、安全设计

### 19.1 认证机制

#### 19.1.1 API 认证

```python
from fastapi import Security, HTTPException
from fastapi.security import APIKeyHeader

api_key_header = APIKeyHeader(name="X-API-Key")

async def verify_api_key(api_key: str = Security(api_key_header)):
    """验证 API Key"""
    if not is_valid_api_key(api_key):
        raise HTTPException(status_code=401, detail="Invalid API Key")
    return api_key

# 使用认证
@app.post("/api/v1/diagnosis/start", dependencies=[Security(verify_api_key)])
async def start_diagnosis(request: DiagnosisRequest):
    # ...
```

#### 19.1.2 JWT 认证

```python
from datetime import datetime, timedelta
import jwt

class JWTAuth:
    """JWT 认证"""
    
    def __init__(self, secret_key: str, expires_hours: int = 24):
        self.secret_key = secret_key
        self.expires_hours = expires_hours
    
    def create_token(self, user_id: str, roles: List[str]) -> str:
        """创建 Token"""
        payload = {
            "sub": user_id,
            "roles": roles,
            "exp": datetime.utcnow() + timedelta(hours=self.expires_hours),
            "iat": datetime.utcnow()
        }
        return jwt.encode(payload, self.secret_key, algorithm="HS256")
    
    def verify_token(self, token: str) -> dict:
        """验证 Token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=["HS256"])
            return payload
        except jwt.ExpiredSignatureError:
            raise AuthenticationError("Token expired")
        except jwt.InvalidTokenError:
            raise AuthenticationError("Invalid token")
```

### 19.2 授权机制

#### 19.2.1 RBAC 权限模型

```python
from enum import Enum
from typing import Set

class Permission(str, Enum):
    """权限枚举"""
    READ = "read"
    WRITE = "write"
    DELETE = "delete"
    ADMIN = "admin"

class Role:
    """角色"""
    
    def __init__(self, name: str, permissions: Set[Permission]):
        self.name = name
        self.permissions = permissions

# 预定义角色
ROLES = {
    "viewer": Role("viewer", {Permission.READ}),
    "editor": Role("editor", {Permission.READ, Permission.WRITE}),
    "admin": Role("admin", {Permission.READ, Permission.WRITE, Permission.DELETE, Permission.ADMIN})
}

def check_permission(user_role: str, required_permission: Permission) -> bool:
    """检查权限"""
    role = ROLES.get(user_role)
    if not role:
        return False
    return required_permission in role.permissions
```

### 19.3 数据安全

#### 19.3.1 敏感数据脱敏

```python
import re

class DataMasker:
    """数据脱敏"""
    
    @staticmethod
    def mask_ip(ip: str) -> str:
        """IP 地址脱敏"""
        parts = ip.split(".")
        if len(parts) == 4:
            return f"{parts[0]}.{parts[1]}.***.{parts[3]}"
        return "***"
    
    @staticmethod
    def mask_email(email: str) -> str:
        """邮箱脱敏"""
        if "@" in email:
            name, domain = email.split("@")
            masked_name = name[:2] + "*" * (len(name) - 2)
            return f"{masked_name}@{domain}"
        return "***"
    
    @staticmethod
    def mask_api_key(key: str) -> str:
        """API Key 脱敏"""
        if len(key) > 8:
            return key[:4] + "*" * (len(key) - 8) + key[-4:]
        return "****"
```

#### 19.3.2 数据加密

```python
from cryptography.fernet import Fernet
import base64
import os

class Encryptor:
    """数据加密"""
    
    def __init__(self, key: bytes = None):
        self.key = key or Fernet.generate_key()
        self.cipher = Fernet(self.key)
    
    def encrypt(self, data: str) -> str:
        """加密"""
        return self.cipher.encrypt(data.encode()).decode()
    
    def decrypt(self, encrypted_data: str) -> str:
        """解密"""
        return self.cipher.decrypt(encrypted_data.encode()).decode()
```

### 19.4 网络安全

#### 19.4.1 HTTPS 配置

```yaml
# config/server.yaml
server:
  http:
    host: "0.0.0.0"
    port: 8000
  
  https:
    enabled: true
    host: "0.0.0.0"
    port: 8443
    cert_file: "/etc/ssl/certs/server.crt"
    key_file: "/etc/ssl/private/server.key"
```

#### 19.4.2 CORS 配置

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://app.example.com"],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    max_age=3600
)
```

### 19.5 审计日志

```python
from datetime import datetime
from typing import Optional
import json

class AuditLogger:
    """审计日志"""
    
    def __init__(self, log_file: str = "/var/log/audit.log"):
        self.log_file = log_file
    
    def log(
        self,
        action: str,
        user: str,
        resource: str,
        status: str,
        details: Optional[dict] = None
    ):
        """记录审计日志"""
        entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "action": action,
            "user": user,
            "resource": resource,
            "status": status,
            "details": details or {}
        }
        
        with open(self.log_file, "a") as f:
            f.write(json.dumps(entry) + "\n")

# 使用示例
audit = AuditLogger()
audit.log(
    action="diagnosis.start",
    user="user@example.com",
    resource="alert:ALT-12345",
    status="success",
    details={"region": "Singapore-Central"}
)
```

---

## 二十、可观测性

### 20.1 指标监控

#### 20.1.1 Prometheus 指标定义

```python
from prometheus_client import Counter, Histogram, Gauge

# 请求计数器
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

# 请求延迟直方图
REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
)

# 活跃会话数
ACTIVE_SESSIONS = Gauge(
    'active_diagnosis_sessions',
    'Number of active diagnosis sessions'
)

# ClickHouse 查询延迟
CLICKHOUSE_QUERY_LATENCY = Histogram(
    'clickhouse_query_duration_seconds',
    'ClickHouse query latency',
    ['query_type'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 2.0, 5.0]
)
```

#### 20.1.2 中间件集成

```python
from fastapi import Request
import time

@app.middleware("http")
async def prometheus_middleware(request: Request, call_next):
    """Prometheus 指标收集中间件"""
    start_time = time.time()
    
    response = await call_next(request)
    
    # 记录指标
    REQUEST_COUNT.labels(
        method=request.method,
        endpoint=request.url.path,
        status=response.status_code
    ).inc()
    
    REQUEST_LATENCY.labels(
        method=request.method,
        endpoint=request.url.path
    ).observe(time.time() - start_time)
    
    return response
```

### 20.2 日志管理

#### 20.2.1 结构化日志

```python
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """JSON 格式日志"""
    
    def format(self, record):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno
        }
        
        if hasattr(record, 'extra'):
            log_entry.update(record.extra)
        
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_entry)

# 配置日志
handler = logging.StreamHandler()
handler.setFormatter(JSONFormatter())
logging.root.addHandler(handler)
logging.root.setLevel(logging.INFO)
```

#### 20.2.2 日志级别动态调整

```python
from fastapi import HTTPException

@app.post("/api/v1/admin/log-level")
async def set_log_level(level: str):
    """动态调整日志级别"""
    valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
    if level not in valid_levels:
        raise HTTPException(status_code=400, detail=f"Invalid log level: {level}")
    
    logging.root.setLevel(level)
    return {"status": "success", "level": level}
```

### 20.3 链路追踪

#### 20.3.1 分布式追踪集成

```python
from opentelemetry import trace
from opentelemetry.exporter.jaeger import JaegerExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

# 配置 Jaeger 导出
jaeger_exporter = JaegerExporter(
    agent_host_name="localhost",
    agent_port=6831
)

# 配置追踪提供者
provider = TracerProvider()
processor = BatchSpanProcessor(jaeger_exporter)
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)

# 获取 tracer
tracer = trace.get_tracer(__name__)

# 使用追踪
@app.post("/api/v1/diagnosis/start")
async def start_diagnosis(request: DiagnosisRequest):
    with tracer.start_as_current_span("diagnosis.start") as span:
        span.set_attribute("alert_id", request.alert_id)
        span.set_attribute("region", request.region)
        
        # 执行诊断
        result = await run_diagnosis(request)
        
        span.set_attribute("result.confidence", result.confidence)
        return result
```

#### 20.3.2 Span 注解

```python
from opentelemetry import trace

async def query_clickhouse(sql: str):
    """带追踪的 ClickHouse 查询"""
    tracer = trace.get_tracer(__name__)
    
    with tracer.start_as_current_span("clickhouse.query") as span:
        span.set_attribute("db.system", "clickhouse")
        span.set_attribute("db.statement", sql[:500])  # 限制长度
        
        try:
            result = await client.query(sql)
            span.set_attribute("db.rows_affected", len(result))
            span.set_status(Status(StatusCode.OK))
            return result
        except Exception as e:
            span.set_status(Status(StatusCode.ERROR, str(e)))
            span.record_exception(e)
            raise
```

### 20.4 健康检查

#### 20.4.1 健康检查端点

```python
from fastapi import HTTPException

@app.get("/health")
async def health_check():
    """健康检查"""
    checks = {
        "api": True,
        "clickhouse": await check_clickhouse(),
        "qdrant": await check_qdrant(),
        "redis": await check_redis()
    }
    
    all_healthy = all(checks.values())
    
    if not all_healthy:
        raise HTTPException(
            status_code=503,
            detail={"status": "unhealthy", "checks": checks}
        )
    
    return {"status": "healthy", "checks": checks}

@app.get("/health/ready")
async def readiness_check():
    """就绪检查"""
    # 检查服务是否准备好接收请求
    return {"status": "ready"}

@app.get("/health/live")
async def liveness_check():
    """存活检查"""
    # 检查服务是否存活
    return {"status": "alive"}
```

#### 20.4.2 依赖健康检查

```python
async def check_clickhouse() -> bool:
    """检查 ClickHouse 连接"""
    try:
        result = await client.query("SELECT 1")
        return result[0][0] == 1
    except Exception:
        return False

async def check_qdrant() -> bool:
    """检查 Qdrant 连接"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:6333/collections")
            return response.status_code == 200
    except Exception:
        return False

async def check_redis() -> bool:
    """检查 Redis 连接"""
    try:
        await redis_client.ping()
        return True
    except Exception:
        return False
```

### 20.5 告警规则

#### 20.5.1 Prometheus 告警规则

```yaml
# prometheus/alerts.yml
groups:
  - name: app_alerts
    rules:
      - alert: HighErrorRate
        expr: |
          sum(rate(http_requests_total{status=~"5.."}[5m])) 
          / sum(rate(http_requests_total[5m])) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "High error rate detected"
          description: "Error rate is {{ $value | humanizePercentage }}"
      
      - alert: HighLatency
        expr: |
          histogram_quantile(0.99, 
            sum(rate(http_request_duration_seconds_bucket[5m])) by (le)
          ) > 2
        for: 5m
        labels:
          severity: warning
        annotations:
          summary: "High latency detected"
          description: "P99 latency is {{ $value }}s"
      
      - alert: ClickHouseDown
        expr: up{job="clickhouse"} == 0
        for: 1m
        labels:
          severity: critical
        annotations:
          summary: "ClickHouse is down"
```

---

## 二十一、扩展开发指南

### 21.1 添加新的 Skill

#### 21.1.1 Skill 模板

```python
# src/skills/custom_skill/SKILL.md
---
name: custom-skill
description: 自定义 Skill 描述
version: 1.0.0
author: Your Name
tags: [tag1, tag2]
---

# Custom Skill

## 功能描述
[详细描述 Skill 的功能]

## Actions
- action1: 功能1描述
- action2: 功能2描述

## 使用示例
[使用示例]
```

#### 21.1.2 Skill 实现模板

```python
# src/skills/custom_skill/skill.py
from typing import Dict, Any, Optional
from src.skills.base import BaseSkill, SkillMetadata, SkillResult

class CustomSkill(BaseSkill):
    """自定义 Skill 实现"""
    
    @property
    def metadata(self) -> SkillMetadata:
        return SkillMetadata(
            name="custom-skill",
            description="自定义 Skill 描述",
            version="1.0.0",
            actions={
                "action1": {
                    "description": "Action 1 描述",
                    "parameters": {
                        "param1": {"type": "string", "required": True},
                        "param2": {"type": "integer", "required": False, "default": 10}
                    },
                    "returns": {"type": "object"}
                }
            }
        )
    
    async def execute(self, action: str, params: Dict[str, Any]) -> SkillResult:
        """执行 Action"""
        if action == "action1":
            return await self._action1(params)
        else:
            return SkillResult(
                success=False,
                error=f"Unknown action: {action}"
            )
    
    async def _action1(self, params: Dict[str, Any]) -> SkillResult:
        """Action 1 实现"""
        try:
            # 验证参数
            param1 = params.get("param1")
            if not param1:
                return SkillResult(success=False, error="param1 is required")
            
            # 执行逻辑
            result = await self._do_something(param1)
            
            return SkillResult(
                success=True,
                data=result
            )
        except Exception as e:
            return SkillResult(success=False, error=str(e))
    
    async def _do_something(self, param: str) -> Dict[str, Any]:
        """具体业务逻辑"""
        # 实现你的逻辑
        return {"result": param}
```

#### 21.1.3 注册 Skill

```python
# src/skills/__init__.py
from src.skills.custom_skill.skill import CustomSkill

def register_skills(registry):
    """注册所有 Skills"""
    registry.register(CustomSkill())
    # ... 其他 Skills
```

### 21.2 添加新的 Tool

#### 21.2.1 Tool 实现模板

```python
# src/tools/plugins/custom_tool.py
from typing import Dict, Any, Optional
from src.tools.base import BaseTool, ToolMetadata, ToolResult, ToolCategory

class CustomTool(BaseTool):
    """自定义 Tool 实现"""
    
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="custom_tool",
            description="自定义 Tool 描述",
            category=ToolCategory.UTILITY,
            parameters={
                "type": "object",
                "properties": {
                    "param1": {
                        "type": "string",
                        "description": "参数1描述"
                    },
                    "param2": {
                        "type": "integer",
                        "description": "参数2描述",
                        "default": 10
                    }
                },
                "required": ["param1"]
            },
            returns={
                "type": "object",
                "description": "返回结果描述"
            }
        )
    
    async def execute(self, **params) -> ToolResult:
        """执行 Tool"""
        try:
            param1 = params.get("param1")
            
            # 执行逻辑
            result = await self._execute_internal(param1, params.get("param2", 10))
            
            return ToolResult(
                success=True,
                data=result
            )
        except Exception as e:
            return ToolResult(
                success=False,
                error=str(e)
            )
    
    async def _execute_internal(self, param1: str, param2: int) -> Dict[str, Any]:
        """内部执行逻辑"""
        return {"result": f"{param1}: {param2}"}

# 注册函数
def register_custom_tool(registry):
    """注册自定义 Tool"""
    registry.register(CustomTool())
```

### 21.3 添加新的 Agent

#### 21.3.1 Agent 实现模板

```python
# src/agents/custom_agent.py
from typing import Dict, Any, Optional
from src.agents.base import BaseAgent, AgentMetadata

class CustomAgent(BaseAgent):
    """自定义 Agent 实现"""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(config)
        self.name = "custom_agent"
    
    @property
    def metadata(self) -> AgentMetadata:
        return AgentMetadata(
            name="custom_agent",
            description="自定义 Agent 描述",
            capabilities=["capability1", "capability2"],
            dependencies=["dependency1"]
        )
    
    async def process(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理请求"""
        # 1. 解析输入
        input_data = self._parse_input(context)
        
        # 2. 执行处理
        result = await self._do_process(input_data)
        
        # 3. 格式化输出
        return self._format_output(result)
    
    def _parse_input(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """解析输入"""
        return {
            "field1": context.get("field1"),
            "field2": context.get("field2")
        }
    
    async def _do_process(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """执行处理逻辑"""
        # 实现你的逻辑
        return {"processed": True}
    
    def _format_output(self, result: Dict[str, Any]) -> Dict[str, Any]:
        """格式化输出"""
        return {
            "agent": self.name,
            "result": result,
            "timestamp": datetime.utcnow().isoformat()
        }
```

### 21.4 插件系统

#### 21.4.1 插件接口定义

```python
# src/plugins/base.py
from abc import ABC, abstractmethod
from typing import Dict, Any

class BasePlugin(ABC):
    """插件基类"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """插件名称"""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """插件版本"""
        pass
    
    @abstractmethod
    async def initialize(self, config: Dict[str, Any]):
        """初始化插件"""
        pass
    
    @abstractmethod
    async def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行插件"""
        pass
    
    @abstractmethod
    async def cleanup(self):
        """清理资源"""
        pass
```

#### 21.4.2 插件管理器

```python
# src/plugins/manager.py
from typing import Dict, Type, Optional
import importlib

class PluginManager:
    """插件管理器"""
    
    def __init__(self):
        self.plugins: Dict[str, BasePlugin] = {}
        self.configs: Dict[str, Dict[str, Any]] = {}
    
    def register(self, plugin_class: Type[BasePlugin], config: Optional[Dict[str, Any]] = None):
        """注册插件"""
        plugin = plugin_class()
        self.plugins[plugin.name] = plugin
        self.configs[plugin.name] = config or {}
    
    async def initialize_all(self):
        """初始化所有插件"""
        for name, plugin in self.plugins.items():
            await plugin.initialize(self.configs.get(name, {}))
    
    async def execute(self, name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """执行指定插件"""
        if name not in self.plugins:
            raise ValueError(f"Plugin not found: {name}")
        return await self.plugins[name].execute(context)
    
    async def cleanup_all(self):
        """清理所有插件"""
        for plugin in self.plugins.values():
            await plugin.cleanup()
    
    def load_from_config(self, config_path: str):
        """从配置文件加载插件"""
        import yaml
        with open(config_path) as f:
            config = yaml.safe_load(f)
        
        for plugin_config in config.get("plugins", []):
            module = importlib.import_module(plugin_config["module"])
            plugin_class = getattr(module, plugin_config["class"])
            self.register(plugin_class, plugin_config.get("config"))
```

---

## 二十二、常见问题解答

### 22.1 安装与配置

**Q: 如何安装项目依赖？**

```bash
# 安装 Python 依赖
pip install -r requirements.txt

# 安装开发依赖
pip install -r requirements-dev.txt

# 安装 pre-commit hooks
pre-commit install
```

**Q: 如何配置环境变量？**

```bash
# 复制示例配置
cp .env.example .env

# 编辑配置文件
vim .env

# 必要的环境变量
export CLICKHOUSE_HOST=localhost
export CLICKHOUSE_PORT=8123
export QDRANT_URL=http://localhost:6333
export OPENAI_API_KEY=sk-xxx
```

**Q: 如何启动服务？**

```bash
# 开发模式
python main.py --reload

# 生产模式
gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker

# Docker 启动
docker-compose up -d
```

### 22.2 功能使用

**Q: 如何触发诊断？**

```bash
# API 调用
curl -X POST http://localhost:8000/api/v1/diagnosis/start \
  -H "Content-Type: application/json" \
  -d '{
    "alert_id": "ALT-001",
    "title": "网络延迟突增",
    "region": "Singapore-Central",
    "severity": "critical"
  }'
```

**Q: 如何查询历史诊断结果？**

```bash
# 查询诊断结果
curl http://localhost:8000/api/v1/diagnosis/diag-20250115-001
```

**Q: 如何添加新的知识库文档？**

```python
from src.knowledge import KnowledgeImporter

importer = KnowledgeImporter()
await importer.import_from_file(
    file_path="./data/tickets/TK-12345.json",
    collection="oncall_tickets"
)
```

### 22.3 性能优化

**Q: 如何提高查询性能？**

1. 使用合适的时间范围，避免全量扫描
2. 利用缓存机制，减少重复查询
3. 优化 SQL 查询，添加必要的索引
4. 使用异步并发查询

**Q: 如何处理大数据量查询？**

```python
# 使用分页查询
result = await tool.execute(
    query_type="ping_stats",
    region="UKRAINE",
    limit=1000,
    offset=0
)

# 使用流式查询
async for batch in tool.stream_execute(
    query_type="ping_trend",
    region="UKRAINE",
    batch_size=1000
):
    process_batch(batch)
```

### 22.4 故障排查

**Q: ClickHouse 连接超时怎么办？**

1. 检查 ClickHouse 服务状态
2. 检查网络连接
3. 增加超时时间
4. 检查连接池配置

```python
# 增加超时时间
client = ClickHouseClient(
    host="localhost",
    timeout_seconds=60
)
```

**Q: LLM 服务限流怎么办？**

1. 降低请求频率
2. 实现重试机制
3. 使用多个 API Key 轮换
4. 升级 API 套餐

```python
# 重试机制
from tenacity import retry, wait_exponential

@retry(wait=wait_exponential(multiplier=1, min=4, max=60))
async def call_llm(prompt: str):
    return await llm.generate(prompt)
```

### 22.5 开发相关

**Q: 如何运行测试？**

```bash
# 运行所有测试
pytest

# 运行特定测试
pytest tests/test_diagnosis.py

# 运行集成测试
pytest -m integration

# 生成覆盖率报告
pytest --cov=src --cov-report=html
```

**Q: 如何添加新的 API 端点？**

```python
# src/api/router/custom.py
from fastapi import APIRouter

router = APIRouter(prefix="/api/v1/custom", tags=["custom"])

@router.post("/action")
async def custom_action(request: CustomRequest):
    # 实现逻辑
    return {"status": "success"}

# 在 main.py 中注册
from src.api.router.custom import router as custom_router
app.include_router(custom_router)
```

---

## 二十三、实战案例

### 23.1 案例 1：网络延迟突增诊断

#### 23.1.1 问题描述

某日 00:30 收到告警：新加坡区域 P99 延迟从 45ms 突增到 180ms，持续时间 15 分钟。

#### 23.1.2 诊断过程

```python
# Step 1: 发起诊断请求
alert = {
    "alert_id": "ALT-20250115-001",
    "title": "新加坡区域网络延迟突增",
    "description": "P99 延迟从 45ms 上升到 180ms，持续时间 15 分钟",
    "severity": "critical",
    "region": "Singapore-Central",
    "triggered_at": "2025-01-15T00:30:00Z",
    "metric_name": "p99_latency_ms",
    "metric_value": 180.5,
    "threshold": 100.0
}

result = await diagnosis_skill.execute(
    action="diagnose_alert",
    params=alert
)
```

#### 23.1.3 诊断结果

```json
{
  "session_id": "diag-20250115-001",
  "root_cause": {
    "category": "network",
    "subcategory": "latency",
    "description": "新加坡出口链路拥塞导致延迟突增",
    "confidence": 0.88
  },
  "evidence": [
    {
      "source": "network_telemetry",
      "type": "latency_anomaly",
      "details": {
        "avg_latency_ms": 150.5,
        "baseline_ms": 45.2,
        "deviation_ratio": 3.3
      }
    },
    {
      "source": "knowledge_base",
      "type": "similar_case",
      "details": {
        "doc_id": "TK-12345",
        "title": "新加坡区域网络延迟异常",
        "similarity": 0.92
      }
    }
  ],
  "recommendations": [
    "1. 检查新加坡出口链路状态",
    "2. 参考历史案例 TK-12345 的处理方案",
    "3. 考虑流量切换到备用链路"
  ]
}
```

#### 23.1.4 处理结果

根据诊断建议，执行流量切换后，延迟在 5 分钟内恢复到正常水平。

### 23.2 案例 2：跨区域链路问题排查

#### 23.2.1 问题描述

用户反馈从欧洲访问亚洲服务延迟高，时断时续。

#### 23.2.2 分析过程

```python
# Step 1: 查询链路质量
link_quality = await telemetry.query_link_quality(
    link_id="EU-West-Asia-East",
    start_time="2025-01-15T00:00:00Z",
    end_time="2025-01-15T01:00:00Z"
)

# Step 2: 查询异常事件
anomalies = await telemetry.query_anomalies(
    time_range_minutes=60,
    region="EU-West",
    event_type="latency_spike"
)

# Step 3: 分析 Traceroute 数据
path_analysis = await viz_tool.execute(
    action="trace_path_analysis",
    region="EU-West"
)
```

#### 23.2.3 分析结果

```
链路质量分析:
- 健康分数: 45/100 (unhealthy)
- 平均延迟: 180ms (基线 80ms)
- 丢包率: 3.2%
- 路径切换次数: 5 次/小时

异常事件:
- 00:15 延迟突增 (280ms)
- 00:28 延迟突增 (320ms)
- 00:42 延迟突增 (250ms)

路径分析:
- 主要路径: AS1239 → AS20485 → AS31133 (60%)
- 备用路径: AS1239 → AS3216 → AS31133 (40%)
- 路径不稳定，频繁切换
```

#### 23.2.4 解决方案

1. 联系上游 ISP 检查 AS20485 链路
2. 调整路由策略，优先使用 AS3216 路径
3. 增加监控告警阈值

### 23.3 案例 3：丢包问题定位

#### 23.3.1 问题描述

某地区用户报告服务访问不稳定，部分请求超时。

#### 23.3.2 诊断过程

```python
# Step 1: 查询丢包数据
packet_loss = await telemetry.query_latency(
    start_time="2025-01-15T00:00:00Z",
    end_time="2025-01-15T01:00:00Z",
    region="Region-A"
)

# Step 2: 末端节点分析
terminal_analysis = await viz_tool.execute(
    action="trace_terminal_analysis",
    region="Region-A"
)

# Step 3: 按 ASN 分析
asn_analysis = await viz_tool.execute(
    action="ping_by_asn",
    region="Region-A"
)
```

#### 23.3.3 诊断结果

```json
{
  "packet_loss_rate": 0.053,
  "problematic_terminals": [
    {
      "ip": "10.0.1.100",
      "asn": 12345,
      "loss_rate": 0.15,
      "avg_latency_ms": 250
    },
    {
      "ip": "10.0.1.101",
      "asn": 12345,
      "loss_rate": 0.12,
      "avg_latency_ms": 180
    }
  ],
  "root_cause": "AS12345 网络设备故障导致丢包"
}
```

#### 23.3.4 处理措施

1. 联系 AS12345 运营商处理设备故障
2. 临时将流量切换到其他 ASN
3. 增加监控告警

---

## 附录

### A. 术语表

| 术语 | 说明 |
|------|------|
| Agent | 智能代理，负责特定任务的 AI 组件 |
| Skill | 技能模块，封装特定领域的能力 |
| RAG | 检索增强生成，结合检索和生成的技术 |
| SOP | 标准操作流程 |
| MTTR | 平均修复时间 |
| P99 | 99% 分位值 |
| RTT | 往返时延 |

### B. 参考资料

- [ClickHouse 文档](https://clickhouse.com/docs)
- [Qdrant 文档](https://qdrant.tech/documentation)
- [BGE-M3 Embedding 模型](https://huggingface.co/BAAI/bge-m3)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
