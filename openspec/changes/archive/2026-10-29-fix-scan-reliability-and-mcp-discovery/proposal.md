## Why

真实项目扫描暴露了孤立代理字符导致输出失败、依赖缓存混入扫描和输出峰值内存过高的问题。测试事实缺少来源区分，MCP 声明式工具又被遗漏，影响结果的可消费性与功能清单的可信度。

## What Changes

- 安全转义 JSON，序列化完成后分块输出，统一处理提取、序列化和写出失败；避免复制完整输出字符串。
- 遍历前剪枝虚拟环境和明确缓存，逐目录记录排除依据与读取失败。
- 保留测试事实并标注路径来源，让产品分析与测试证据可区分。
- 识别静态 MCP Tool 声明、输入 Schema 和调用分派器；不能确认的实现关系显式记为覆盖缺口。
- 更新 Skill 消费说明和最小回归检查，保持只读、标准库依赖及现有 JSON 字段兼容。

## Capabilities

### New Capabilities

无；新增行为属于现有事实提取能力。

### Modified Capabilities

- `python-fact-extraction`: 输出可靠性、目录排除、测试来源及 MCP 声明与实现边界。

## Impact

主要影响 extract_facts.py、其回归检查、README、SKILL.md 和审计方法。新增可选事实元数据与 coverage 类型，保留 schema_version 2；输出转为 ASCII 转义但解析后的内容保持不变。不会修改目标项目、默认截断事实、引入第三方依赖、实现通用 gitignore 规则或增加非 Python 解析器。扫描事实仍驻留内存，不承诺任意规模扫描成功。
