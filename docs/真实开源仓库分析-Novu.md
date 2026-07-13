# 真实开源仓库分析：Novu

## 仓库选择

本次选择的真实开源仓库：

```text
https://github.com/novuhq/novu
```

选择理由：

- Novu 是开源通知基础设施项目，业务场景真实。
- 仓库是 monorepo，包含 API、Worker、WebSocket、Dashboard、SDK、共享库等模块。
- 同时包含前端和后端，符合企业级全栈项目特征。
- 代码规模足够大，可以验证代码仓库 Agent 是否能处理复杂仓库。

本地克隆路径：

```text
external-repos/novu
```

该目录已加入 `.gitignore`，不会把第三方源码提交到当前项目。

## 分析方式

使用本项目新增的代码仓库 Agent 能力分析：

- `RepositoryScanner`
- `CodeSearcher`
- `CodebaseQuestionAnswerer`
- `CodeImpactReport`

运行对象：

```text
external-repos/novu
```

## 仓库概览结果

扫描结果：

| 指标 | 结果 |
|---|---|
| 总文件数 | 9478 |
| 可分析文件数 | 7967 |
| 估算代码行数 | 964761 |
| 主要语言 | TypeScript、JSON、Markdown、Python、CSS、JavaScript、YAML |
| 前端信号 | `dashboard`、`package.json` |
| 后端信号 | `api`、`apps`、`worker`、`workers` |

顶层目录包括：

```text
apps
libs
packages
enterprise
docs
docker
playground
scripts
```

关键文件包括：

```text
package.json
pnpm-lock.yaml
README.md
packages/framework/package.json
packages/js/package.json
packages/react/package.json
packages/shared/package.json
```

## 代码搜索样例

### Controller

搜索 `Controller` 命中后端 API 代码：

```text
apps/api/src/app.module.ts
apps/api/src/app/activity/activity.controller.ts
apps/api/src/app/activity/activity.module.ts
```

说明 Novu 后端 API 使用 NestJS 风格的 Controller / Module 组织方式。

### workflow

搜索 `workflow` 命中：

```text
apps/api/e2e/retry.e2e.ts
apps/api/e2e/test-bridge-server.ts
apps/api/.spectral.yaml
README.md
```

说明 workflow 是 Novu 的核心业务概念之一，出现在 API 测试、OpenAPI 规则和项目介绍中。

### notification

搜索 `notification` 命中：

```text
apps/api/admin/remove-organization.ts
apps/api/e2e/enterprise/inbound-webhook/process-inbound-webhook.e2e.ts
README.md
```

说明通知模板、消息、订阅者和组织清理逻辑都与 notification 相关。

### tenant

搜索 `tenant` 命中：

```text
apps/api/src/app.module.ts
apps/api/src/app/agents/channels/whatsapp/configure-whatsapp-webhook/configure-whatsapp-webhook.usecase.ts
apps/api/src/app/agents/channels/whatsapp/send-whatsapp-test-template/send-whatsapp-test-template.usecase.ts
```

其中 WhatsApp 相关 usecase 的注释明确提到同一 tenant 内的集成隔离，说明该项目有多租户/环境隔离需求。

## 代码问答样例

### 问题：tenant environment service implementation

Agent 返回的证据包括：

```text
apps/api/src/app.module.ts:55-63
apps/api/src/app.module.ts:150-158
apps/api/src/app/agents/channels/whatsapp/configure-whatsapp-webhook/configure-whatsapp-webhook.usecase.ts:93-101
apps/api/src/app/agents/channels/whatsapp/send-whatsapp-test-template/send-whatsapp-test-template.usecase.ts:87-95
```

可得结论：

- `TenantModule` 在 `apps/api/src/app.module.ts` 中被导入并注册。
- WhatsApp agent 相关 usecase 中存在 tenant 级隔离校验。
- 修改 tenant/environment 相关逻辑时，需要重点检查 API 模块、agent channel usecase 和 e2e 测试。

### 问题：notification workflow implementation

Agent 返回的证据包括：

```text
apps/api/admin/remove-organization.ts
apps/api/e2e/enterprise/inbound-webhook/process-inbound-webhook.e2e.ts
```

可得结论：

- notification、message、template、workflow 都是清理组织数据时需要处理的核心实体。
- workflow 在存储层表现为 `NotificationTemplateRepository` 对应的 `workflows` 数据。
- inbound webhook e2e 测试涉及 `NotificationTemplateEntity` 和消息处理链路。

## 影响分析样例

目标文件：

```text
package.json
```

Agent 找到的引用包括：

```text
apps/api/src/app.module.ts
apps/api/src/app/health/health.controller.ts
apps/api/src/app/shared/framework/swagger/swagger.controller.ts
apps/api/src/instrument.ts
apps/worker/src/app.module.ts
apps/worker/src/app/health/health.controller.ts
apps/ws/src/app.module.ts
apps/ws/src/health/health.controller.ts
```

可得结论：

- `package.json` 中的 name/version 会被 API、Worker、Webhook、WS 等服务读取。
- 修改 package 信息可能影响健康检查、Swagger、OpenTelemetry instrumentation 和多服务启动信息。
- 建议运行 API、Worker、WS 相关测试，并检查部署和监控上报信息。

## 企业级价值验证

这次分析证明当前项目不是固定文档 Demo，而是可以处理真实大型开源仓库：

- 能扫描复杂 monorepo。
- 能识别前端和后端信号。
- 能搜索真实业务代码。
- 能返回文件路径和行号。
- 能给出影响分析和测试建议。
- 能跳过 `.agents`、`.cursor`、`.github` 等非业务目录，减少噪声。

## 当前局限

- 仍是关键词检索，不是向量语义检索。
- TypeScript 还没有 AST 级符号解析。
- 影响分析是静态启发式，不是完整调用图。
- 代码问答的自然语言总结还可以进一步接入真实模型增强。

## 后续增强

- 引入 Tree-sitter 解析 TypeScript/NestJS/React。
- 引入 embedding 和向量数据库，提升语义检索能力。
- 接入 GitHub PR，自动分析变更并生成 Review 评论。
- 将影响分析结果写入会话记忆和评测报告。
