# Skill 管理开源方案

## 一、主流开源方案对比

| 项目 | Stars | 特点 | 适用场景 |
|------|-------|------|---------|
| **LangChain Tools** | 100k+ | 工具链丰富、生态好 | LLM 应用开发 |
| **CrewAI** | 44k+ | 多 Agent 协作 | Agent 编排 |
| **Semantic Kernel** | 22k+ | 微软出品、技能管理 | 企业级应用 |
| **AutoGPT Plugins** | 170k+ | 插件系统 | 自主 Agent |
| **OpenAI Functions** | - | 函数调用标准 | LLM 工具调用 |

## 二、推荐方案：LangChain Tools + 自定义注册

### 架构设计

```
┌─────────────────────────────────────────────────────────┐
│                    Skill Manager                          │
├─────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐      │
│  │   Registry  │  │   Loader    │  │   Executor  │      │
│  │   (注册)    │  │   (加载)    │  │   (执行)    │      │
│  └─────────────┘  └─────────────┘  └─────────────┘      │
│         │                │                │              │
│         ▼                ▼                ▼              │
│  ┌─────────────────────────────────────────────────┐    │
│  │              Skill Store (存储)                  │    │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐   │    │
│  │  │监控    │ │日志    │ │数据库  │ │自定义  │   │    │
│  │  │Skills  │ │Skills  │ │Skills  │ │Skills  │   │    │
│  │  └────────┘ └────────┘ └────────┘ └────────┘   │    │
│  └─────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────┘
```

### 核心实现

```python
# skills/manager.py
from typing import Dict, List, Callable, Any
from dataclasses import dataclass
from pathlib import Path
import yaml
import importlib

@dataclass
class Skill:
    name: str
    description: str
    category: str
    version: str
    executor: Callable
    schema: Dict[str, Any]
    enabled: bool = True

class SkillManager:
    """
    技能管理器

    功能：
    1. 动态注册技能
    2. 从文件加载技能
    3. 执行技能
    4. 版本管理
    """

    def __init__(self, skills_dir: str = "./skills"):
        self.skills_dir = Path(skills_dir)
        self._skills: Dict[str, Skill] = {}

    def register(self, skill: Skill) -> None:
        """注册技能"""
        self._skills[skill.name] = skill

    def register_function(
        self,
        name: str,
        description: str,
        category: str = "general",
    ):
        """装饰器：注册函数为技能"""
        def decorator(func: Callable):
            skill = Skill(
                name=name,
                description=description,
                category=category,
                version="1.0.0",
                executor=func,
                schema=self._infer_schema(func),
            )
            self.register(skill)
            return func
        return decorator

    def load_from_directory(self) -> int:
        """从目录加载技能"""
        count = 0
        for skill_file in self.skills_dir.glob("**/skill.yaml"):
            skill = self._load_skill(skill_file)
            if skill:
                self.register(skill)
                count += 1
        return count

    def _load_skill(self, config_path: Path) -> Skill:
        """加载单个技能"""
        with open(config_path) as f:
            config = yaml.safe_load(f)

        # 动态加载执行器
        module_path = config.get("module")
        executor_name = config.get("executor")

        try:
            module = importlib.import_module(module_path)
            executor = getattr(module, executor_name)
        except Exception:
            return None

        return Skill(
            name=config["name"],
            description=config["description"],
            category=config.get("category", "general"),
            version=config.get("version", "1.0.0"),
            executor=executor,
            schema=config.get("schema", {}),
        )

    def execute(self, name: str, **params) -> Any:
        """执行技能"""
        if name not in self._skills:
            raise ValueError(f"Skill '{name}' not found")

        skill = self._skills[name]
        if not skill.enabled:
            raise ValueError(f"Skill '{name}' is disabled")

        return skill.executor(**params)

    def list_skills(self, category: str = None) -> List[Skill]:
        """列出技能"""
        skills = list(self._skills.values())
        if category:
            skills = [s for s in skills if s.category == category]
        return skills

    def _infer_schema(self, func: Callable) -> Dict:
        """推断函数参数 schema"""
        import inspect
        sig = inspect.signature(func)
        schema = {"type": "object", "properties": {}}
        for name, param in sig.parameters.items():
            schema["properties"][name] = {"type": "string"}
        return schema


# 全局实例
manager = SkillManager()
```

### 技能配置格式

```yaml
# skills/prometheus/skill.yaml
name: prometheus-query
description: 查询 Prometheus 监控指标
category: monitoring
version: 1.0.0
module: skills.prometheus.executor
executor: query_metrics
schema:
  type: object
  properties:
    query:
      type: string
      description: PromQL 查询语句
    time_range:
      type: string
      description: 时间范围
  required:
    - query
```

```python
# skills/prometheus/executor.py
import requests

def query_metrics(query: str, time_range: str = "1h") -> dict:
    """查询 Prometheus 指标"""
    prometheus_url = "http://localhost:9090"
    response = requests.get(
        f"{prometheus_url}/api/v1/query",
        params={"query": query}
    )
    return response.json()
```

### 使用示例

```python
from skills.manager import manager

# 方式1：装饰器注册
@manager.register_function(
    name="query-logs",
    description="查询应用日志",
    category="logging",
)
def query_logs(service: str, keyword: str) -> list:
    # 实现日志查询
    return []

# 方式2：从目录加载
manager.load_from_directory()

# 执行技能
result = manager.execute("prometheus-query", query="up")

# 列出所有监控类技能
monitoring_skills = manager.list_skills(category="monitoring")
```

## 三、推荐的开源 Skills 仓库

### 1. LangChain Tools

```python
from langchain.tools import Tool

# 使用 LangChain 内置工具
tools = [
    Tool(
        name="Database Query",
        func=db_query,
        description="查询数据库"
    )
]
```

### 2. CrewAI Tools

```python
from crewai_tools import tool

@tool("查询 Prometheus 指标")
def prometheus_query(query: str) -> str:
    """使用 PromQL 查询监控指标"""
    # 实现
    return result
```

### 3. Semantic Kernel Skills

```csharp
// C# 示例
[SKFunction("查询数据库")]
public async Task<string> QueryDatabase(string sql) {
    // 实现
}
```

## 四、技能包管理

### 推荐结构

```
skills/
├── core/                      # 核心技能包
│   ├── prometheus/           # Prometheus 监控
│   │   ├── skill.yaml
│   │   └── executor.py
│   ├── loki/                 # Loki 日志
│   └── redis/                # Redis 查询
│
├── ops/                       # 运维技能包
│   ├── mysql/                # MySQL 查询
│   ├── jaeger/               # 链路追踪
│   └── consul/               # 配置查询
│
└── custom/                    # 自定义技能包
    └── oncall-diagnosis/     # 故障诊断
```

### 技能包格式 (skillpack.yaml)

```yaml
name: oncall-ops-skills
version: 1.0.0
description: 运维技能包
author: your-name
skills:
  - name: prometheus-query
    category: monitoring
  - name: loki-query
    category: logging
  - name: mysql-query
    category: database
dependencies:
  - requests>=2.28.0
  - prometheus-client>=0.16.0
```

## 五、版本管理和发布

### 使用 Git Submodule

```bash
# 添加技能包作为 submodule
git submodule add https://github.com/xxx/prometheus-skill skills/prometheus
```

### 使用 pip 安装

```bash
# 安装技能包
pip install oncall-prometheus-skill

# Python 中使用
from oncall_prometheus_skill import PrometheusQuerySkill
```

## 六、推荐技能包列表

| 技能包 | 功能 | 开源地址 |
|--------|------|---------|
| prometheus-skill | Prometheus 查询 | 自己实现 |
| loki-skill | Loki 日志查询 | 自己实现 |
| jaeger-skill | Jaeger 链路追踪 | 自己实现 |
| redis-skill | Redis 操作 | 自己实现 |
| mysql-skill | MySQL 查询 | 自己实现 |

## 七、与现有项目集成

```python
# 在 Go 项目中通过 HTTP 调用 Python Skills

# Python 服务 (skills_server.py)
from fastapi import FastAPI
from skills.manager import manager

app = FastAPI()

@app.post("/skills/{name}/execute")
async def execute_skill(name: str, params: dict):
    return manager.execute(name, **params)

# Go 调用
// handler/skill_handler.go
func ExecuteSkill(name string, params map[string]interface{}) (interface{}, error) {
    resp, err := http.Post(
        "http://localhost:8000/skills/"+name+"/execute",
        "application/json",
        bytes.NewReader(jsonData),
    )
    // ...
}
```
