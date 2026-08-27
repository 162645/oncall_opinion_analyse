# Skill 管理优化方案

## 一、目录结构优化

```
.claude/skills/
├── README.md                    # Skills 总索引
│
├── core/                        # 核心 Skills (本项目必须)
│   ├── argos-alarm/            # 告警管理
│   ├── metrics/                # 指标查询
│   ├── argos-query/            # 日志查询
│   ├── trace-query/            # 链路追踪
│   ├── redis/                  # Redis 查询
│   └── rds/                    # 数据库查询
│
├── ops/                         # 运维辅助 Skills
│   ├── tcc-query/              # 配置查询
│   ├── neptune-stability/      # 超时配置
│   └── diag/                   # 诊断工具
│
├── dev/                         # 开发 Skills (按需)
│   ├── scm/                    # 代码管理
│   ├── bits-devops/            # 研发效能
│   └── api-test/               # API 测试
│
└── archived/                    # 不常用 Skills
    └── ...                     # 其他 60+ 个
```

## 二、Skills 清单文件

在项目根目录创建 `SKILLS.md`：

```markdown
# 本项目使用的 Skills

## 核心 (Core)
| Skill | 版本 | 状态 | 维护者 |
|-------|------|------|--------|
| argos-alarm | v1.0 | ✅ 稳定 | Argos 团队 |
| metrics | v1.0 | ✅ 稳定 | Metrics 团队 |
| ... | ... | ... | ... |

## 辅助 (Ops)
| Skill | 版本 | 状态 |
|-------|------|------|
| tcc-query | v1.0 | ✅ 稳定 |
| ... | ... | ... |

## 不使用
- kitex-knowledge (开发框架)
- hertz-knowledge (开发框架)
- ...
```

## 三、Skill 状态标记

在每个 SKILL.md 的 frontmatter 中添加：

```yaml
---
name: argos-alarm
description: 管理告警规则
status: stable          # stable/beta/deprecated
priority: core          # core/ops/optional
maintainer: argos-team
last-updated: 2025-05-20
---
```

## 四、快速查找机制

创建 `.claude/skills/INDEX.json`：

```json
{
  "core": ["argos-alarm", "metrics", "argos-query", "trace-query", "redis", "rds"],
  "ops": ["tcc-query", "neptune-stability", "diag"],
  "dev": ["scm", "bits-devops"],
  "total": 84,
  "last-indexed": "2025-05-20"
}
```

## 五、调用简化

在项目配置中添加别名：

```yaml
# .claude/settings.json
{
  "skillAliases": {
    "alarm": "argos-alarm",
    "log": "argos-query",
    "trace": "trace-query",
    "metric": "metrics"
  }
}
```

使用：
```bash
# 原来
gdpa-cli run argos-alarm --action list

# 简化后
gdpa-cli run alarm --action list
```

## 六、版本锁定

在 `SKILLS.lock` 中锁定版本：

```
argos-alarm=v1.0.3
metrics=v2.1.0
argos-query=v1.2.1
...
```

防止 Skills 更新导致兼容性问题。
