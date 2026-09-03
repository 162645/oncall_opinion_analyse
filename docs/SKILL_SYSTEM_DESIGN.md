# Skill 管理系统设计

> 让用户从成功流程中提炼可复用的 Skill，解决"能力固化"问题

**状态: ✅ 已实现**

---

## 一、设计理念

### 1.1 核心问题

| 问题 | 现状 | Skill 方案 |
|------|------|-----------|
| 成功经验无法复用 | 每次都要重新描述 | 一键保存，下次直接调用 |
| 团队知识分散 | 资深经验无法传承 | 团队共享 Skill，新人快速上手 |
| 能力固定化 | 系统预设 Agent 有限 | 用户自定义，无限扩展 |

### 1.2 设计目标

1. **易创建**：成功流程自动识别，一键保存
2. **易发现**：智能推荐、分类、搜索
3. **易复用**：参数化调用，快速执行
4. **不混乱**：分层管理、生命周期、质量评分

---

## 二、Skill 定义

### 2.1 Skill 结构

```python
@dataclass
class Skill:
    """用户自定义技能"""
    
    # 基本信息
    id: str                          # 唯一标识
    name: str                        # 名称 (如 "网络延迟诊断")
    description: str                 # 描述
    tags: List[str]                  # 标签 (诊断、网络、延迟)
    category: str                    # 分类 (诊断/分析/操作)
    
    # 所有权
    owner: str                       # 创建者
    scope: str                       # personal / team / system
    team_id: Optional[str]           # 团队ID (团队共享时)
    
    # 核心内容
    trigger: SkillTrigger            # 触发条件
    workflow: List[SkillStep]        # 执行步骤
    parameters: List[SkillParam]     # 可配置参数
    
    # 元数据
    success_count: int = 0           # 成功执行次数
    rating: float = 0.0              # 用户评分
    version: str = "1.0.0"           # 版本号
    status: str = "active"           # active / deprecated / archived
    
    # 统计
    usage_count: int = 0             # 使用次数
    last_used: Optional[datetime]    # 最后使用时间
    created_at: datetime             # 创建时间
    updated_at: datetime             # 更新时间


@dataclass
class SkillTrigger:
    """触发条件"""
    keywords: List[str]              # 关键词触发
    intent: Optional[str]            # 意图触发
    entities: List[str]              # 实体触发 (如服务名、区域)
    
    # 示例: ["网络延迟", "延迟高"] + intent="diagnosis" + entities=["区域"]


@dataclass  
class SkillStep:
    """执行步骤"""
    step_type: str                   # agent / tool / retrieval
    name: str                        # 步骤名称
    config: Dict[str, Any]           # 配置
    condition: Optional[str]         # 执行条件 (可选)


@dataclass
class SkillParam:
    """可配置参数"""
    name: str                        # 参数名
    type: str                        # string / number / enum
    default: Any                     # 默认值
    required: bool                   # 是否必填
    description: str                 # 描述
    options: Optional[List[str]]     # 枚举选项
```

### 2.2 Skill 示例

```yaml
id: "skill-network-latency-diagnosis"
name: "网络延迟诊断"
description: "诊断网络延迟问题，分析根因并给出解决方案"
category: "diagnosis"
tags: ["网络", "延迟", "诊断", "网络问题"]
scope: "team"
owner: "user_001"
team_id: "team_ops"

trigger:
  keywords: ["网络延迟", "延迟高", "网络慢", "延迟突增"]
  intent: "diagnosis"
  entities: ["区域", "服务"]

workflow:
  - step_type: "retrieval"
    name: "检索网络知识"
    config:
      query_template: "网络延迟 {region} {service}"
      top_k: 5
      
  - step_type: "tool"
    name: "查询 Prometheus 指标"
    config:
      tool: "prometheus_query"
      queries:
        - "latency_p99{region='{region}'}"
        - "error_rate{region='{region}'}"
        
  - step_type: "agent"
    name: "LLM 诊断分析"
    config:
      agent: "DiagnosisLLMAgent"
      system_prompt: |
        你是网络诊断专家，分析 {region} 区域的网络延迟问题。
        已知信息：
        - 知识库：{knowledge}
        - 指标数据：{metrics}
        
        请分析可能原因并给出解决方案。

parameters:
  - name: "region"
    type: "string"
    required: true
    description: "目标区域"
    options: ["新加坡", "美国", "欧洲", "东京", "上海"]
    
  - name: "service"
    type: "string"
    required: false
    default: "all"
    description: "目标服务"

success_count: 47
rating: 4.8
usage_count: 156
```

---

## 三、创建流程

### 3.1 自动推荐机制

```
用户执行流程
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Flow Analyzer                             │
│  分析执行轨迹，识别可复用模式：                              │
│  - 执行成功率 > 80%                                          │
│  - 包含 3+ 步骤                                              │
│  - 用户反馈正面                                               │
│  - 包含有价值的检索/工具调用                                 │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Pattern Extractor                         │
│  提取关键模式：                                              │
│  - 触发关键词                                                 │
│  - 步骤序列                                                   │
│  - 可参数化变量                                               │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Skill Recommendation                      │
│  "检测到可复用的诊断流程，是否保存为 Skill？"                │
│                                                              │
│  [保存] [忽略] [查看详情]                                    │
└─────────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────────┐
│                    Skill Editor                              │
│  用户编辑/确认：                                             │
│  - 名称和描述                                                 │
│  - 触发条件                                                   │
│  - 参数定义                                                   │
│  - 共享范围                                                   │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 手动创建

```python
POST /api/skills/create

{
    "name": "服务重启检查",
    "description": "检查服务重启原因并生成报告",
    "category": "operation",
    "tags": ["服务", "重启", "检查"],
    "scope": "team",
    
    "trigger": {
        "keywords": ["重启", "服务重启", "重启原因"],
        "intent": "diagnosis"
    },
    
    "workflow": [
        {
            "step_type": "retrieval",
            "name": "检索重启相关文档",
            "config": {
                "query_template": "服务重启原因排查 {service}"
            }
        },
        {
            "step_type": "tool",
            "name": "查询重启日志",
            "config": {
                "tool": "log_search",
                "query": "restart {service}"
            }
        }
    ],
    
    "parameters": [
        {
            "name": "service",
            "type": "string",
            "required": true,
            "description": "服务名称"
        }
    ]
}
```

---

## 四、防混乱机制

### 4.1 分层管理

```
┌─────────────────────────────────────────────────────────────┐
│                      System Skills                           │
│  系统预设，不可删除，全局可用                                │
│  - 网络诊断                                                   │
│  - 服务检查                                                   │
│  - 日志分析                                                   │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                      Team Skills                             │
│  团队共享，管理员审核发布                                    │
│  - 发布流程检查                                               │
│  - 特定业务诊断                                               │
│  - 内部工具集成                                               │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Personal Skills                           │
│  个人私有，仅自己可见                                        │
│  - 个人常用流程                                               │
│  - 实验性 Skill                                               │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 生命周期管理

```
创建 → 审核(团队) → 发布 → 使用 → 评估 → 归档/废弃

状态转换:
- draft: 草稿，仅创建者可见
- pending: 待审核 (团队 Skill)
- active: 活跃，可正常使用
- deprecated: 已弃用，不推荐使用
- archived: 已归档，不可使用但保留历史
```

### 4.3 质量控制

```python
class SkillQualityScore:
    """Skill 质量评分"""
    
    @staticmethod
    def calculate(skill: Skill) -> float:
        """
        综合质量分数 = 
            0.3 * 使用频率得分 +
            0.3 * 成功率得分 +
            0.2 * 用户评分 +
            0.2 * 完整度得分
        """
        usage_score = min(skill.usage_count / 100, 1.0)
        success_rate = skill.success_count / max(skill.usage_count, 1)
        rating_score = skill.rating / 5.0
        completeness = SkillQualityScore._check_completeness(skill)
        
        return (
            0.3 * usage_score +
            0.3 * success_rate +
            0.2 * rating_score +
            0.2 * completeness
        )
    
    @staticmethod
    def _check_completeness(skill: Skill) -> float:
        """完整度检查"""
        score = 0.0
        
        if skill.description: score += 0.2
        if skill.tags: score += 0.2
        if skill.trigger.keywords: score += 0.2
        if len(skill.workflow) >= 2: score += 0.2
        if skill.parameters: score += 0.2
        
        return score
```

### 4.4 智能推荐与去重

```python
class SkillRecommender:
    """Skill 智能推荐"""
    
    def find_similar(self, new_skill: Skill) -> List[Skill]:
        """查找相似的 Skill，避免重复创建"""
        # 基于 embedding 查找相似
        new_embedding = self._embed(new_skill.name + " " + new_skill.description)
        
        similar = []
        for existing in self._all_skills():
            similarity = cosine_similarity(new_embedding, existing.embedding)
            if similarity > 0.85:
                similar.append((existing, similarity))
        
        return sorted(similar, key=lambda x: x[1], reverse=True)
    
    def recommend_for_query(self, query: str) -> List[Skill]:
        """根据用户查询推荐 Skill"""
        # 1. 关键词匹配
        keyword_matches = self._keyword_match(query)
        
        # 2. 意图匹配
        intent = self._classify_intent(query)
        intent_matches = self._intent_match(intent)
        
        # 3. 综合排序
        combined = self._merge_results(keyword_matches, intent_matches)
        
        # 4. 按质量和相关性排序
        return sorted(combined, key=lambda s: s.score, reverse=True)[:5]
```

### 4.5 分类与标签体系

```yaml
categories:
  diagnosis:
    name: "故障诊断"
    subcategories:
      - network: "网络问题"
      - service: "服务异常"
      - database: "数据库问题"
      - storage: "存储问题"
      
  analysis:
    name: "数据分析"
    subcategories:
      - performance: "性能分析"
      - capacity: "容量分析"
      - trend: "趋势分析"
      
  operation:
    name: "运维操作"
    subcategories:
      - deployment: "部署发布"
      - config: "配置管理"
      - scaling: "扩缩容"

tags:
  system_tags:       # 系统标签，不可修改
    - "官方推荐"
    - "高频使用"
    - "新手友好"
    
  user_tags:         # 用户自定义标签
    - 任意
```

---

## 五、存储设计

### 5.1 数据库 Schema

```sql
-- Skill 主表
CREATE TABLE skills (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    description TEXT,
    category VARCHAR(50),
    tags JSON,
    
    owner VARCHAR(36) NOT NULL,
    scope ENUM('personal', 'team', 'system') DEFAULT 'personal',
    team_id VARCHAR(36),
    
    trigger_config JSON,
    workflow_config JSON,
    parameters_config JSON,
    
    success_count INT DEFAULT 0,
    usage_count INT DEFAULT 0,
    rating FLOAT DEFAULT 0,
    
    status ENUM('draft', 'pending', 'active', 'deprecated', 'archived'),
    version VARCHAR(20),
    
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    INDEX idx_owner (owner),
    INDEX idx_scope (scope),
    INDEX idx_category (category),
    INDEX idx_status (status),
    FULLTEXT INDEX idx_name_desc (name, description)
);

-- Skill 使用记录
CREATE TABLE skill_executions (
    id VARCHAR(36) PRIMARY KEY,
    skill_id VARCHAR(36) NOT NULL,
    user_id VARCHAR(36) NOT NULL,
    params JSON,
    success BOOLEAN,
    duration_ms INT,
    feedback_score INT,
    feedback_comment TEXT,
    executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_skill (skill_id),
    INDEX idx_user (user_id),
    FOREIGN KEY (skill_id) REFERENCES skills(id)
);

-- Skill 版本历史
CREATE TABLE skill_versions (
    id VARCHAR(36) PRIMARY KEY,
    skill_id VARCHAR(36) NOT NULL,
    version VARCHAR(20),
    config JSON,
    change_note TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    INDEX idx_skill (skill_id),
    FOREIGN KEY (skill_id) REFERENCES skills(id)
);
```

### 5.2 向量索引 (Skill 发现)

```python
# Qdrant Collection
collection_name = "skills_embedding"

# Payload 结构
{
    "skill_id": "skill-xxx",
    "name": "网络延迟诊断",
    "description": "诊断网络延迟问题",
    "category": "diagnosis",
    "tags": ["网络", "延迟"],
    "scope": "team",
    "rating": 4.8,
    "usage_count": 156
}
```

---

## 六、API 设计

### 6.1 核心 API

```python
# 创建 Skill
POST /api/skills
{
    "name": "...",
    "workflow": [...],
    ...
}

# 获取 Skill 列表
GET /api/skills?scope=team&category=diagnosis&sort=usage

# 搜索 Skill
POST /api/skills/search
{
    "query": "网络延迟诊断",
    "filters": {
        "scope": ["team", "system"],
        "min_rating": 4.0
    }
}

# 执行 Skill
POST /api/skills/{skill_id}/execute
{
    "params": {
        "region": "新加坡",
        "service": "api-gateway"
    }
}

# 推荐 Skill (根据查询)
POST /api/skills/recommend
{
    "query": "新加坡区域网络延迟突然变高"
}

# 保存执行流程为 Skill
POST /api/skills/from-execution
{
    "execution_id": "exec-xxx",
    "name": "网络延迟诊断",
    "scope": "personal"
}

# 评分
POST /api/skills/{skill_id}/rate
{
    "score": 5,
    "comment": "很好用，快速定位了问题"
}

# 复制/克隆
POST /api/skills/{skill_id}/clone

# 版本管理
POST /api/skills/{skill_id}/versions
GET /api/skills/{skill_id}/versions
```

---

## 七、实现状态

### ✅ Phase 1: 基础框架 (已完成)

- [x] Skill 数据模型定义 (`src/skill/models.py`)
- [x] 存储 Service 实现 (`src/skill/service.py`)
- [x] CRUD API 端点 (`src/api/router/skill.py`)

### ✅ Phase 2: 工作流执行 (已完成)

- [x] Skill 执行引擎 (`src/skill/executor.py`)
- [x] 参数注入和替换

### ✅ Phase 3: 智能推荐 (已完成)

- [x] Flow 分析器 (`src/skill/analyzer.py`)
- [x] Pattern 提取器
- [x] 相似 Skill 检测

### ✅ Phase 4: 管理功能 (已完成)

- [x] 版本管理
- [x] 质量评分
- [x] 生命周期管理

### ✅ Phase 5: 前端集成 (已完成)

- [x] Skill 列表页面 (`frontend/src/pages/Skill/`)
- [x] 执行界面
- [x] 导航集成

### ✅ Phase 6: Agent 集成 (已完成)

- [x] 执行轨迹记录
- [x] 自动推荐机制
- [x] Chat API 集成

---

## 八、文件结构

```
src/skill/
├── __init__.py          # 模块导出
├── models.py            # 数据模型
├── service.py           # 存储和管理服务
├── executor.py          # 执行引擎
└── analyzer.py          # 流程分析器

src/api/router/skill.py  # API 端点

frontend/src/
├── api/skill.ts         # API 客户端
└── pages/Skill/
    ├── index.tsx        # Skill 管理页面
    └── Skill.css        # 样式
```

---

## 九、使用示例

### 9.1 查看和管理 Skill

```bash
# 获取 Skill 列表
curl http://localhost:8000/api/skills/

# 搜索 Skill
curl -X POST http://localhost:8000/api/skills/search \
  -H "Content-Type: application/json" \
  -d '{"query": "网络延迟诊断"}'
```

### 9.2 执行 Skill

```bash
# 执行网络延迟诊断 Skill
curl -X POST http://localhost:8000/api/skills/skill-network-diagnosis/execute \
  -H "Content-Type: application/json" \
  -d '{"params": {"region": "新加坡"}}'
```

### 9.3 前端访问

1. 启动后端: `cd src && uvicorn api.main:app --reload`
2. 启动前端: `cd frontend && npm run dev`
3. 访问 http://localhost:5173/skills

### 9.4 自动推荐流程

当用户在智能对话中完成一次成功的诊断后:

1. 系统自动分析执行轨迹
2. 判断是否值得保存为 Skill
3. 在 Chat 响应中返回 `skill_recommendation`
4. 前端可以显示"保存为 Skill"按钮
5. 用户确认后保存为个人 Skill
- [ ] 与现有 Agent 集成

### Phase 3: 智能推荐 (Day 5)

- [ ] Flow 分析器
- [ ] Pattern 提取器
- [ ] 相似 Skill 检测

### Phase 4: 管理功能 (Day 6)

- [ ] 版本管理
- [ ] 质量评分
- [ ] 生命周期管理

### Phase 5: 前端集成 (Day 7)

- [ ] Skill 列表页面
- [ ] Skill 编辑器
- [ ] 执行界面
