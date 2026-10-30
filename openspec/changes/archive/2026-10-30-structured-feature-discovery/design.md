## Context

现有版本 3 提取器提供 capabilities、flows、gates、documents、coverage、manifest 和 snapshot_id。已有报告及引用检查器处理证据边界。见 proposal.md 的动机。本次新增多阶段分析数据契约，需要协调指令、检查与报告。

## Goals / Non-Goals

Goals：让扫描候选均有可检查的处置记录，让功能总结、补查与最终清单可追溯。

Non-goals：自动发现所有功能、生成模型推理的正确性证明、独立多 agent 分析、执行被审计代码或建设通用语义引擎。

## Decisions

1. 保留 01-scan.json 为原有版本 3 输出。新增 02-features.json、03-supplement.json、04-reconciliation.json 使用 discovery_version: 1、stage、snapshot_id。文件名称是默认约定，检查器接收显式路径。拒绝额外包装扫描输出，减少迁移。
2. 模型按扫描线索总结功能，再补查盲区；不是两份独立清单交叉验证。用户任务功能与代码入口分开，通过多对多 ID 关联。结构化业务字段使用 status（known/unknown/not-applicable）、value 和 reason；未知不得靠空字符串冒充确认。
3. 功能记录复用 evidence.json 的引用 ID，不复制源码。补查中的新增功能复用相同结构，修正通过目标功能 ID 与理由表达。最终功能保留 source_feature_ids，合并或拆分记录 source/target IDs、类型和依据；阶段内不可重用 ID，跨模型阶段功能 ID 全局唯一。显式记录未解决冲突。
4. 补查类别采用有限枚举，范围不适用需说明理由。扫描 coverage 每项按扫描列表索引关联影响记录，因为现有 coverage 并非都有 ID；不修改原提取格式。每个缺口与补查未完成项均在最终 scope_impacts 留下依据和影响。
5. 用一个标准库脚本 check_discovery.py 校验四文件和 evidence.json，复用现有引用核验，不复制路径安全规则。证据检查器从报告与 discovery 记录收集使用的引用 ID，保留原报告-only 兼容入口；新功能检查不以引用标记充当语义证明。诊断明确区分结构/关联/引用与未验证语义。
6. 最终 JSON 是后续审计功能范围的依据，报告引用最终功能 ID。由模型按既有模板整理报告，程序核对报告引用的 ID 有效；不强制建设自动 Markdown 渲染器，也不尝试比较任意自然语言的等价性。

## Risks / Trade-offs

- 结构增加模型填表负担 → 只用四份文件与现有证据文件，不复制事实或源码。
- 扫描先行会限制模型视野 → 固定补查类别，保留未解决缺口及影响。
- 自动处置检查可能鼓励草率排除 → 必填理由与证据/缺失说明，语义仍由模型复核，不能把处置率当覆盖率。
- 分析期间代码变化 → 使用现有快照和摘要校验，更新相关产物后重新核对。

## Migration Plan

先固定契约与小型示例，随后实现结构与关联检查并接入引用核验，再更新 Skill 和报告流程。旧提取器版本不变；旧格式检查入口继续可用但不能代表新流程完成。运行原有回归及新对照检查。回退时撤销新流程要求并重新生成报告，不将不完整模型 JSON 视为已完成。
