"""
网络测量知识库初始化 - 通过 API 添加知识
"""

import requests

API_BASE = "http://localhost:8000"

# 网络测量知识文档
NETWORK_MEASUREMENT_KNOWLEDGE = [
    {
        "title": "Ping 测量基础",
        "content": """# Ping 测量基础

## 什么是 Ping 测量？

Ping 是最基础的网络主动测量工具，通过发送 ICMP Echo Request 报文并接收 Echo Reply 来测量网络的可达性和往返时延(RTT)。

## 关键指标

### 1. RTT (Round-Trip Time) 往返时延
- 定义: 数据包从源到目的地再返回的总时间
- 单位: 毫秒(ms)
- 影响因素: 传播延迟、处理延迟、排队延迟、传输延迟

### 2. 丢包率 (Packet Loss Rate)
- 定义: 未收到响应的探测包占总发送包的比例
- 计算: 丢包率 = (发送包数 - 接收包数) / 发送包数
- 正常范围: 通常应小于 1%

### 3. 抖动 (Jitter)
- 定义: RTT 的变化程度，即连续测量值之间的差异
- 影响: 对实时应用(语音、视频)影响较大

## 分析维度

1. 时间维度: 按小时、天、周查看趋势变化
2. 空间维度: 按 AS、国家、地区分析
3. 网络维度: 按 Prefix、IP 地址分析

## 异常检测

- 3σ 原则: 超过均值±3倍标准差视为异常
- IQR 方法: 超过 Q3+1.5×IQR 视为异常
""",
    },
    {
        "title": "Traceroute 路径测量",
        "content": """# Traceroute 路径测量

## 什么是 Traceroute？

Traceroute 是网络路径探测工具，通过利用 IP 报文的 TTL(Time To Live) 字段，逐跳探测从源到目的地的网络路径。

## 关键概念

### AS 路径 (AS Path)
- 网络路径经过的自治系统(AS)序列
- 例如: AS1239 → AS3356 → AS174
- 用于分析跨域流量路径

### ASGeo 路径
- 结合 AS 和地理位置的路径表示
- 例如: AS1239_US → AS3356_DE → AS174_UK
- 更精确地描述路径地理位置

### 末端节点 (Terminal Node)
- Traceroute 探测的最终目标
- 分析末端节点分布有助于了解服务部署

## 分析方法

- 路径稳定性分析: 路径变化频率、ECMP检测
- 路径性能分析: 各跳延迟分析、瓶颈识别
- 路径拓扑分析: AS关系、上下游关系
""",
    },
    {
        "title": "网络延迟诊断方法论",
        "content": """# 网络延迟诊断方法论

## 诊断流程

### 第一步: 确认问题范围
- 单一目标还是多个目标?
- 特定时间段还是持续?
- 特定地区还是全局?

### 第二步: 数据收集
- 收集 Ping 数据: RTT、丢包率、抖动
- 收集 Traceroute 数据: 路径信息

### 第三步: 分层分析

1. 整体层 (Overall): 查看整体统计指标
2. AS 层: 分析各 AS 的延迟表现
3. 地理层: 分析各地区的延迟表现
4. 前缀层 (Prefix24): 定位到具体网段

### 第四步: 根因分析

#### 延迟高的常见原因
1. 网络拥塞: 带宽不足、流量突发
2. 路由问题: 路由绕行、路由震荡
3. 设备性能: CPU/内存负载高
4. 链路质量: 物理链路问题

#### 丢包的常见原因
1. 链路故障: 物理链路中断
2. 设备故障: 接口故障
3. 拥塞丢包: 队列溢出
4. 过滤丢包: ACL 过滤
""",
    },
    {
        "title": "RTT 百分位数分析",
        "content": """# RTT 百分位数分析

## 什么是百分位数？

百分位数表示数据集中有百分之多少的数据小于该值。

- P50(中位数): 50% 的数据小于该值
- P90: 90% 的数据小于该值
- P95: 95% 的数据小于该值
- P99: 99% 的数据小于该值

## 为什么使用百分位数？

- 不受极端值影响
- 更准确反映用户体验
- 能识别尾部延迟问题

## 分析指标

- 四分位距 (IQR): IQR = P75 - P25
- 变异系数 (CV): CV = 标准差 / 均值
- 偏度 (Skewness): 反映分布的不对称性
- 峰度 (Kurtosis): 反映分布的尖锐程度
""",
    },
    {
        "title": "AS 级网络分析",
        "content": """# AS 级网络分析

## 什么是 AS (Autonomous System)？

自治系统是在单一管理实体控制下的 IP 网络集合，每个 AS 有唯一的 ASN。

## AS 分析的重要性

1. 识别网络边界: AS 是互联网的路由单元
2. 定位问题: 特定 AS 的问题影响跨域流量
3. 优化路径: 选择最优 AS 路径

## 关键 AS 指标

- AS 覆盖率: 经过某 AS 的流量比例
- AS 性能排名: 按延迟、丢包率、稳定性排名
- AS 路径多样性: 到同一目标的不同 AS 路径数
""",
    },
    {
        "title": "网络数据可视化指南",
        "content": """# 网络数据可视化指南

## 常用图表类型

### 1. 折线图 (Line Chart)
- 用途: 展示时间趋势
- 场景: RTT 随时间变化、流量趋势

### 2. 柱状图 (Bar Chart)
- 用途: 对比不同类别的数值
- 场景: 各 AS 延迟对比、各区域延迟对比

### 3. 热力图 (Heatmap)
- 用途: 展示二维数据的分布
- 场景: 时间×地区的延迟分布

### 4. 桑基图 (Sankey Diagram)
- 用途: 展示流量路径
- 场景: AS 路径、网络流量流向

## 选择合适的图表

- 趋势 → 折线图
- 对比 → 柱状图
- 分布 → 直方图/箱线图
- 路径 → 桑基图
- 层级 → 树图
""",
    },
    {
        "title": "网络异常类型与诊断",
        "content": """# 网络异常类型与诊断

## 异常类型分类

### 1. 延迟异常
- 延迟突增: 短时间内 RTT 大幅上升
- 持续高延迟: 长期保持高延迟状态
- 延迟抖动: RTT 波动剧烈

### 2. 丢包异常
- 突发丢包: 短时间内大量丢包
- 持续丢包: 长期存在丢包
- 周期性丢包: 周期性出现丢包

### 3. 路径异常
- 路由绕行: 路径变长，延迟增加
- 路由震荡: 路径频繁变化
- 路由黑洞: 流量被丢弃

## 异常检测算法

- Z-score: 异常值 > μ + 3σ
- IQR方法: 异常值 > Q3 + 1.5 × IQR
- 百分位法: 异常值 > P99 + 阈值

## 异常处理流程

1. 检测 → 2. 确认 → 3. 定位 → 4. 诊断 → 5. 处理 → 6. 复盘
""",
    },
]


def init_knowledge_base():
    """通过 API 初始化知识库"""
    print("📚 初始化网络测量知识库...")

    for doc_data in NETWORK_MEASUREMENT_KNOWLEDGE:
        try:
            # 使用 API 上传文档
            response = requests.post(
                f"{API_BASE}/api/knowledge/upload",
                files={
                    "file": (f"{doc_data['title']}.md", doc_data["content"].encode('utf-8'))
                },
                data={
                    "title": doc_data["title"],
                },
                timeout=10
            )

            if response.status_code == 200:
                print(f"  ✅ 已添加: {doc_data['title']}")
            else:
                print(f"  ⚠️ 添加失败 {doc_data['title']}: {response.status_code}")

        except Exception as e:
            print(f"  ❌ 添加失败 {doc_data['title']}: {e}")

    # 获取统计信息
    try:
        response = requests.get(f"{API_BASE}/api/knowledge/stats", timeout=5)
        stats = response.json().get("stats", {})
        print(f"\n📊 知识库统计:")
        print(f"  - 总文档数: {stats.get('total_documents', 0)}")
        print(f"  - 总块数: {stats.get('total_chunks', 0)}")
    except Exception as e:
        print(f"获取统计失败: {e}")


if __name__ == "__main__":
    init_knowledge_base()
