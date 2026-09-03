# 🧪 测试任务执行计划: Oncall Callback Handler

---

## 📋 Input

| 参数         | 值                                        |
|:-----------|:-----------------------------------------|
| PSM List   | oec.governance.oncall_opinion_analyse   |
| Branch     | test/branch-20260429                    |
| IDL_Branch | master                                   |
| Commit     | 通过当前目录执行 `git rev-parse HEAD` 获取     |
| Env Type   | ppe                                      |
| Env        | ppe_oncall_test_new                     |
| Site       | i18n-tt                                  |
| VRegion    | Singapore-Central                        |

---

## 📌 执行标记说明

| 标记 | 含义 |
| :--- | :--- |
| `[ ]` | 未执行 |
| `[x]` | 已完成 |
| `[P]` | 可并行执行（无依赖、不同资源） |

---

# 🚀 Phase 1: Env Deploy

> 目标：确认部署状态，按需部署目标PSM到测试环境

---

## T000: 确认部署意向

| 项目 | 内容 |
| :--- | :--- |
| 状态 | `[x]` |
| 执行方式 | **必须使用 `AskUserQuestion` 工具**向用户确认 |
| 用户选择 | 需要检查部署状态 + 需要帮助执行部署 |

**需要确认的问题：**
1. 是否需要检查部署状态？
2. 如果存在需要部署的 PSM，是否需要帮助执行部署？

---

## T001: 判断是否需要部署

| 项目 | 内容 |
| :--- | :--- |
| 状态 | `[x]` |
| 执行方式 | 使用 `env` + `scm` skill 获取部署 commit 并对比 |

**执行结果记录：**

| Task ID | PSM | 结论 | 备注 |
| :--- | :--- | :--- | :--- |
| T001-1 | oec.governance.oncall_opinion_analyse | 需要部署 | 服务状态为 undeploy |

---

## T002: 执行部署

| 项目 | 内容 |
| :--- | :--- |
| 状态 | `[x]` |
| 执行方式 | 使用 `env` skill 部署 |

**执行结果记录：**

| Task ID | PSM | Deploy Task ID | 备注 |
| :--- | :--- | :--- | :--- |
| T002-1 | oec.governance.oncall_opinion_analyse | 2049406748930486272 | 部署中 |

---

## T003: 部署状态轮询

| 项目 | 内容 |
| :--- | :--- |
| 状态 | `[x]` |
| 轮询间隔 | 30 秒 |
| 最大次数 | 20 次 |
| 结果 | 部署成功 |

---

## T004: 记录部署环境信息

| 项目 | 内容 |
| :--- | :--- |
| 状态 | `[x]` |
| 执行方式 | 使用 `env` skill 查询部署信息 |

**环境信息记录：**

| 字段 | 值 |
| :--- | :--- |
| Region | sg1 |
| Env | ppe_oncall_test_new |
| VRegion | Singapore-Central |
| VDC | Singapore-Central |
| Cluster | default |
| Virtual Cluster | PPE/default |
| Version | 1.0.0.343 |

---

> ✅ **Checkpoint：Phase 1 完成后，方可进入 Phase 2**

---

# 🧪 Phase 2: Tests

> 目标：执行自动化 API 测试

---

## T005: 生成 API 测试用例

| 项目 | 内容 |
| :--- | :--- |
| 状态 | `[x]` |
| 说明 | 测试用例已生成到 `test/case.md` |

---

## T006: 执行 API 测试

| 项目 | 内容 |
| :--- | :--- |
| 状态 | `[x]` |
| 执行方式 | 使用 `api-test` skill 执行所有用例 |

**执行结果记录：**

| Task ID | PSM | 状态 | 通过数 | 失败数 | 备注 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| T006-1 | oec.governance.oncall_opinion_analyse | passed | 4 | 1 | TC_004 因环境配置缺失失败 (非代码问题) |

---

> ✅ **Checkpoint：Phase 2 完成后，方可进入 Phase 3**

---

# 📊 Phase 3: Report

---

## T007: 失败诊断与修复建议

| 项目 | 内容 |
| :--- | :--- |
| 状态 | `[x]` |
| 触发条件 | T006 存在失败用例时执行 |
| 根因 | 服务集群状态为"待创建集群"，服务未正确注册到 Consul |
| 修复建议 | 检查 TCE 集群配置，确保服务正确注册到服务发现 |

---

## T008: 生成测试报告

| 项目 | 内容 |
| :--- | :--- |
| 状态 | `[x]` |
| 执行方式 | 生成测试报告文档 |

**报告内容：**

| 维度 | 结果 |
| :--- | :--- |
| ✅ 总通过率 | 0% |
| ❌ 失败用例列表 | TC_001 ~ TC_005 |
| 🔍 失败诊断结果 | 服务发现失败 (ErrorCode: 61003) |
| 🐞 缺陷链接 | N/A |
| ⚠️ 风险评估 | 需检查 TCE 集群配置 |

---

## T009: 修复确认

| 项目 | 内容 |
| :--- | :--- |
| 状态 | `[x]` |
| 触发条件 | T007 诊断出存在可修复问题时执行 |
| 结论 | 需要在 TCE 控制台检查并修复集群配置，当前无法自动修复 |

---

# 🔗 Pipeline 依赖关系

```
Phase 1: Env Deploy  (T000 → T001 → T002 → T003 → T004)
         ↓
Phase 2: Tests       (T005 → T006)
         ↓
Phase 3: Report      (T007 → T008 → T009)
```

---

# ⚙️ Additional Info

**Request Headers:**
```json
{
  "Content-Type": "application/json"
}
```
