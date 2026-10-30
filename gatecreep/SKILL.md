---
name: gatecreep
description: Use when auditing Python Agent, CLI, or Skill projects for blocked valid tasks, excessive gates, overly strict validation, hard-coded limits, silent truncation, or when reviewing a gatecreep report.
---

# Gatecreep

## Overview

以公开功能和合法任务为单位审计门禁。静态脚本提供代码事实，模型提供语义判断，人确认结论后才进入修改；没有充分证据时宁可列入待复核，也不形成主要发现。

## When to Use

用于 Python Agent、CLI、Skill 的只读门禁审计。不用于通用代码审查、安全漏洞扫描、性能审查、动态复现或自动修复。

## Inputs

- 必填：目标项目路径；可选：功能或文件范围。
- 可选：报告输出位置，必须位于目标项目之外。
- 仅用户明确请求时启用 `include_overdesign`，默认 `false`。

## Required Procedure

先阅读 [审计方法](references/audit-method.md) 和 [报告格式](references/report-format.md)，再按顺序完成：

1. **范围与事实**：确认路径和范围。运行辅助脚本并保存 stdout，非零退出或部分失败必须记为覆盖缺口。
2. **四阶段功能发现**：脚本保存 01-scan.json；模型据此阅读仓库保存 02-features.json，再补查盲区保存 03-supplement.json，最后核对候选处置与最终功能保存 04-reconciliation.json。遵循 references/discovery-format.md，复用 evidence.json；运行 check_discovery.py，结构、关联与引用通过后再进入任务分析。
3. **任务分析**：逐项先写合法任务与成功标准，再生成有契约依据的失败场景。
4. **因果与评估**：建立静态因果链，分别分类失败来源和表现；只对门禁应用证据分档。
5. **人工报告**：严格按模板输出范围、功能、发现、反证、不确定性和待复核项；写入报告文件后运行格式检查，修正所有错误再交付。

辅助脚本（将 `<skill-dir>` 换为本 Skill 所在目录）：

```bash
python -I <skill-dir>/scripts/extract_facts.py <target>
python -I <skill-dir>/scripts/check_report.py <report>
```

脚本只解析文本和 AST。不得导入或执行目标代码，不得在目标项目中创建缓存、报告、配置或修复。

## Completion Gates

- 四阶段 JSON、候选逐项处置、最终功能证据和全部覆盖影响均存在且检查通过，才能开始门禁任务分析；未知项保留并说明影响。
- 合法任务与成功标准明确，才能生成失败场景。
- 因果链和反证检查完整，才能形成主要发现。
- 报告完成即停止；修改目标项目是用户确认后的独立任务。

## Common Mistakes

| 偏离 | 正确行为 |
|---|---|
| 从常量、异常或名称直接报问题 | 回到功能、合法任务和影响证据链 |
| 文档没写就推定门禁多余 | 检查其他依据；无法排除保护目的时列入待复核 |
| 为完成任务建议移除认证、授权或安全边界 | 保留并说明权限或安全限制 |
| 把动态调用当作确认路径 | 标为模型推断并降低结论等级 |
| 扫描无发现就宣称无问题 | 同时报告分析覆盖和未完成部分 |
| 顺手审查无关实现质量 | 仅记录与任务失败因果链有关的非门禁原因 |


### Facts schema version 3

提取输出使用 `schema_version: 3`。JSON 原生标量、列表和字符串键字典保持原有形态。
非 JSON 字面量用 `literal_type`、`expression`（所属字面量表达式）以及 `items` 或 `representation` 表示：
set/frozenset/tuple 的 items 是列表，集合按规范 JSON 文本排序；非字符串键字典的 items 是键值对列表；
bytes/complex/Ellipsis/非有限浮点值使用 Python repr 文本。消费者应按版本解释这些字段，不能将类型记录当作普通业务字典。

`decorator` 事实保留完整 expression、owner 和 source；status 确认语法存在，action=candidate、gate_semantics=inferred 表示门禁语义未证实。
函数装饰器通过 function 关联定义；类装饰器 function 为空，无法关联时继续产生 coverage 缺口。
`assert` 事实包含条件 expression 和可选 message；它不代表过度门禁结论。
链式比较每段使用独立 ID 后缀及相邻 left/right；嵌套函数 ID 不重复模块前缀。
脚本先完成严格 JSON 序列化再输出；序列化失败非零退出并写 stderr，不留下 JSON 前缀。

JSON 以 ASCII 转义写入目标目录之外的临时文件，序列化成功后分块写出并刷新 stdout。提取、序列化、临时存储或输出的已知异常以 exit 2 和阶段诊断报告；写出阶段可能已有部分 stdout，任何非零退出都必须丢弃 stdout 并保留 stderr。临时目录不可位于目标项目内。事实和关联仍驻留内存，不能保证任意规模扫描成功，不默认截断。

扫描在进入既有排除目录、`.uv-cache` 和含 `pyvenv.cfg` 的虚拟环境前剪枝；每个排除目录产生一条 `excluded-directory`，含路径与原因。目录链接和 Windows junction 不跟随，指向目标之外的文件链接跳过；枚举失败记为 `unreadable-directory`。这些条目说明范围，不代表目标项目存在缺陷；不解析 `.gitignore`。

capabilities、gates、flows 的 `source_role` 为路径启发式：目录段 `test` / `tests` 或文件名 `test_*.py` / `*_test.py` 标为 `test`，其余为 `unknown`。测试事实不删除；建立产品功能清单时区分测试候选，测试可用作契约与反证，unknown 不能当成已确认产品代码。

静态 `mcp.types.Tool` 声明（含导入别名）使用 `declaration_kind: mcp-tool`，保留 description 和 input_schema；仅解析字面量或直接赋值的字面量 Schema，不跟踪变异或通用数据流。动态名称、未知 Schema 和逐工具实现未确认分别记录覆盖缺口；`implementation_status: unknown` 不产生虚构实现链接。属性装饰器 `call_tool` / `list_tools` 仅按语法标为 `mcp_role: dispatcher` / `listing`，角色状态为 inferred，不能据此确认注册方身份或将其算成一个具名工具。

回归检查：`python -I <skill-dir>/tests/check_extract_facts.py`，含本仓库 CLI 扫描、严格 JSON 解析和 ID 唯一性检查。
另运行 `tests/check_audit_regressions.py` 和 `tests/check_scan_reliability.py`，检查 CLI 参数、多行报告、目录边界、输出失败和 MCP 声明。

### 快照与证据交付

新版事实附 manifest（path/status/sha256/line_count）和 snapshot_id。摘要标识实际读取字节，Git 版本不是替代。版本 2 无快照，必须重新提取才能核验引用。

每份新报告同时保存 evidence.json，遵循 references/report-format.md 的证据契约。运行：
`python -I <skill-dir>/scripts/check_report.py <report> --facts <facts.json> --evidence <evidence.json> --target <target>`。
核验失败必须修正；内容变化需重新分析相关结论。所有输出在目标外。旧版无参数调用仅检查格式，不满足新交付要求。

### 功能发现交付

阅读 references/discovery-format.md。模型总结依赖脚本线索，不是独立交叉验证。补查文档、配置、动态注册、多动作、非 Python 与未解析路径，不能把未检查写成无新增。最终报告使用 [feature:ID] 与 [scope:来源]，以核对后的最终清单为功能范围。快照变化后重新提取并更新受影响分析，不能只替换 snapshot_id。

进入门禁分析前运行 check_discovery.py 的四文件/证据/目标参数；报告完成时加 --report 再检查。文件全部在目标外。结构和引用有效不等于语义正确或功能覆盖完整；报告-only 旧命令不满足新流程。
