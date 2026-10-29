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
2. **功能清单**：合并声明文档与实现入口，覆盖全部可识别公开功能；用全局门禁反向补漏。
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

- 功能清单和覆盖缺口均存在，才能开始功能分析。
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


### Facts schema version 2

提取输出使用 `schema_version: 2`。JSON 原生标量、列表和字符串键字典保持原有形态。
非 JSON 字面量用 `literal_type`、`expression`（所属字面量表达式）以及 `items` 或 `representation` 表示：
set/frozenset/tuple 的 items 是列表，集合按规范 JSON 文本排序；非字符串键字典的 items 是键值对列表；
bytes/complex/Ellipsis/非有限浮点值使用 Python repr 文本。消费者应按版本解释这些字段，不能将类型记录当作普通业务字典。

`decorator` 事实保留完整 expression、owner 和 source；status 确认语法存在，action=candidate、gate_semantics=inferred 表示门禁语义未证实。
函数装饰器通过 function 关联定义；类装饰器 function 为空，无法关联时继续产生 coverage 缺口。
`assert` 事实包含条件 expression 和可选 message；它不代表过度门禁结论。
链式比较每段使用独立 ID 后缀及相邻 left/right；嵌套函数 ID 不重复模块前缀。
脚本先完成严格 JSON 序列化再输出；序列化失败非零退出并写 stderr，不留下 JSON 前缀。

回归检查：`python -I <skill-dir>/tests/check_extract_facts.py`，含本仓库 CLI 扫描、严格 JSON 解析和 ID 唯一性检查。
