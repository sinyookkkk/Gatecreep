# 四阶段 JSON 契约（discovery_version 1）

01-scan.json 原样采用 extract_facts.py 版本 3 输出。其余三个文件含 discovery_version:1、stage、snapshot_id，stage 分别为 features、supplement、reconciliation。所有分析文件位于目标外，共用实际字节快照。

02-features.json：features 列表。每项含 id/name/purpose/status/reason/candidate_ids/evidence，以及 inputs/outputs/success_criteria/preconditions/side_effects/failure_behavior。status 为 confirmed/inferred/unknown；业务字段为 {status:known|unknown|not-applicable,value:值或null,reason:说明}，未知或不适用必须 null。ID 为非空字符串，各列表唯一；功能 ID 跨阶段不复用。一个功能可关联多个候选，一个候选可关联多个功能。

03-supplement.json：features（同结构）、corrections（feature_ids 指向第二阶段，reason/evidence）、inspections。每项检查含 id/category/outcome/reason/impact/evidence/feature_ids；category 必须覆盖 documentation/configuration/dynamic-registration/multi-action/non-python/unmapped-paths。outcome 为 inspected-no-addition/discovered/not-applicable/not-inspected/unresolved。discovered 必须关联功能。证据不足的未完成或不适用检查填写 missing_evidence，不能省略检查类别。

04-reconciliation.json：features（同功能结构，增加非空 source_feature_ids）、candidate_dispositions、transformations、conflicts、scope_impacts。
- disposition：candidate_id/classification/feature_ids/reason/evidence；classification 为 public-entry/internal/test/legacy/false-positive/unresolved。每个扫描 capability 恰好处置一次，公开入口必须关联最终功能。无证据时说明 missing_evidence。
- transformation：kind 为 merge/split/retain，source_ids 关联前两阶段功能，target_ids 关联最终功能，附 reason/evidence。
- conflict：status 为 resolved/unresolved，feature_ids/reason/impact/evidence。
- scope impact：source 为 coverage:扫描缺口索引 或 inspection:检查ID，附 reason/impact；所有扫描缺口和未完成检查均须逐项记录。

所有 evidence 是现有 evidence.json 的 citation ID 列表。源码引用沿用摘要与行范围核验，程序不证明其语义充分性。报告使用 [feature:最终ID] 关联每个功能，用 [scope:coverage:0]、[scope:inspection:检查ID] 和 [scope:conflict:索引] 显示缺口与未解决冲突，并解释影响。

检查命令：python -I gatecreep/scripts/check_discovery.py --scan 01-scan.json --summary 02-features.json --supplement 03-supplement.json --final 04-reconciliation.json --evidence evidence.json --target <目标> [--report report.md]

快照冲突、无效版本、缺字段、未知引用、重复/遗漏处置、遗漏影响记录必须失败。未知路径允许保留，不为通过检查编造事实。通过只表示结构、关联及引用有效，不证明语义正确、独立交叉验证或完整覆盖。此契约覆盖规格中的四阶段、功能、多动作、补查、处置、快照、引用及验证边界；示例见 docs/discovery-example。
