## Why

事实提取器扫描自身仓库时因集合字面量无法序列化而崩溃，且遗漏普通装饰器与 assert。链式比较还会产生重复 ID，导致关联阶段丢失事实。这些问题直接损害审计输入的完整性。

## What Changes

- 保证支持的 Python 字面量可以安全输出为完整 JSON，保留不可直接表示值的类型和来源表达式，避免 default=str 隐藏信息。
- 提取函数（含异步、私有和嵌套函数）及类的装饰器候选事实，不凭名称认定门禁语义。
- 提取 assert 的条件、消息及所属函数，不判断其合理性。
- 修复链式比较的 ID 冲突和逐段左操作数。
- 添加最小可运行回归检查及本仓库端到端扫描检查。

## Capabilities

### New Capabilities
- `python-fact-extraction`: 规定 JSON 输出、装饰器/assert 提取和比较关联的可靠性要求；当前没有既有主规范。

### Modified Capabilities
无。

## Impact

主要涉及 gate-audit/scripts/extract_facts.py 和最小回归检查；必要时更新事实字段说明。无需新增依赖，不引入评分、自动修复、规则 ID、语料库或新的门禁合理性判据。return 尾部识别、切片 step 和遍历优化留待独立变更。
