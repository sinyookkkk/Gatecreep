# gatecreep 对照 aislop / sloppylint 的评审

评审日期：2026-10-28
对照对象：`scanaislop/aislop`（707★，MIT，60+ 规则，10 语言）、`rsionnach/sloppylint`（91★，无 license，已停更 10 个月）

---

## 结论

gatecreep 的方法论**明显强于**那两个工具，不该向它们靠拢。但它们的**工程纪律**有三件事值得直接抄过来，而且现在缺了会出事——实测已经在自己的仓库上崩溃了。

一句话：**抄它们的测试和语料库，别抄它们的判据和评分。**

---

## 一、你已经做对、且强于对照工具的

这些是护城河，不要为了"像 linter"而丢掉。

| 设计 | 为什么强 |
|---|---|
| 事实与判断分离 | `extract_facts.py` 只产出 facts，`gates` 明确不含合理性结论。aislop 的规则是 pattern→severity，规则本身就在下判断 |
| 反证检查强制 | 每个发现必须有"反证检查"字段。aislop 和 sloppylint 都没有这个概念，它们不会问"这条规则会不会误伤" |
| 五档结论，且"疑似"保持疑似 | 因为没有动态验证，所以不升级为确认。aislop 的 `error` 级是硬判定，没有这种诚实 |
| coverage 缺口显式建模 | `parse-error` / `dynamic-cli-command` / `unmapped-gate` / `unreadable-file`。**aislop 完全没有 coverage 概念**，扫不到就当没有 |
| 不自动修复 | aislop 有 `fix -f` 能自动删代码。门禁审计自动删门禁是灾难，这条边界守对了 |
| 不执行目标代码 | `python -I` + 纯 AST。安全边界清楚 |
| 证据强度 E1–E5 且 E4/E5 不能独立支撑发现 | 比 severity 更细，是"证据有多硬"而不是"问题多严重" |

---

## 二、实测发现的问题（按严重度）

### P0 — `json.dump` 在含集合字面量的项目上崩溃

**复现**（本仓库自身即触发）：

```
TypeError: Object of type set is not JSON serializable
  extract_facts.py:496  json.dump(facts, sys.stdout, ...)
```

**根因**：`literal()`（:74）直接返回 `ast.literal_eval` 的结果，遇到 `ast.Set` 返回 Python `set`。`visit_Compare`（:310）把它塞进 `gate["value"]`。

**触发点在本仓库内**：`check_report.py:67` 的 `not in {"", "无", "None", "N/A"}`。

**危害**：崩溃发生在 dump 阶段，stdout 只写了一半 JSON，既不能解析也不是合法错误输出。SKILL.md 说"非零退出必须记为覆盖缺口"，但此时连 facts 都拿不到。

**修复**：`json.dump(..., default=str)` 兜底；同时让 `literal()` 对 set/frozenset/bytes/complex 做归一化（set → 排序后的 list），避免静默降级成字符串。

### P0 — 装饰器门禁完全没抓

`:134-139` 只识别 `tool` 或 `*_tool` 装饰器，其余装饰器一律丢弃。

但**认证、授权、限流、参数校验这几类最常见的门禁，在 Python 里几乎都以装饰器形式存在**：`@require_auth`、`@rate_limit`、`@validate_call`、`@login_required`、`@cache`。

这是当前最大的漏抓面，而且恰好落在方法文档最强调的"高优先级安全或权限要求"上——漏掉它们会导致审计报告完全看不到权限门禁。

**修复**：把所有装饰器记为 `kind="decorator"` 的 gate，`action` 按名字粗分类（auth / rate-limit / validate / cache / other），状态标 `inferred`（语义靠名字推断，正是 E4）。

### P1 — `assert` 未作为门禁

没有 `visit_Assert`。`assert` 是最典型的过度门禁形态：在 `-O` 下消失、拒绝合法输入、常被 AI 大量生成。

### P1 — 链式比较生成重复 gate id

`visit_Compare`（:300-311）对每个 operator 调一次 `add_gate`，但 id 由 `path:lineno:col:kind` 生成（:104），链式比较共享同一个 AST 节点的坐标。

`if a < b < c` 会产生两个 id 完全相同的 gate，`link_facts` 里 `gate_by_id`（:407）会丢一个。本仓库无链式比较所以没暴露。

**修复**：id 追加序号，或把 `zip(node.ops, node.comparators)` 的索引并入 id。

### P2 — 其余

| 位置 | 问题 |
|---|---|
| `:344-346` | `early=node is not self.function_tail`。`function_tail` 只取 `body[-1]`，若函数最后是 `if`，则所有 `return` 都误标 early |
| `:339-342` | 切片只判断 `upper or lower`，`x[::2]`（只有 step）漏掉，而 step 也可能截断 |
| `:100-114` | `gate["condition"]` 实际是**父级** if 的条件，自己的条件在 `expression`。两个字段名语义重叠且错位，极易误读。建议改名 `parent_condition` |
| `:457-462` | `rglob("*")` 全量遍历，不读 `.gitignore`，只硬编码 `SKIP_DIRS`。大项目会扫进构建产物并显著变慢 |
| 全局 | **没有任何测试**。上面 P0 那个崩溃只要有一个含 `set` 字面量的 fixture 就能抓到 |

---

## 三、可借鉴的（按优先级）

### 1. 假阳性语料库 —— 最高优先

sloppylint 的 `tests/corpus/` 里 **false_positives 9 个 > true_positives 5 个**。这个比例是对的：这类工具的主要失败模式是误报，不是漏报。

对 gatecreep 尤其重要，因为**代价不对称**：

- 漏报一个过度门禁 → 用户继续被挡，但系统仍安全
- 误报一个合理门禁为"疑似过度" → 用户可能删掉认证、事务边界、限流，造成真实损害

方法文档已经写了"合理安全或权限门禁不得因为用户希望绕过而移入主要发现"，但没有语料库来验证模型是否真的守住了这条。

**建议结构**：

```
tests/corpus/
  reasonable/     # 必须判「合理门禁」——认证、事务、限流、幂等、平台限制
  over/           # 必须判「疑似过度门禁」——合法边界被拒、静默截断、部分结果冒充完整
  ambiguous/      # 必须判「证据不足」或「待复核」——文档缺失、动态注册
  coverage-gap/   # 必须产出覆盖缺口——语法错误、动态 CLI 命令、unmapped gate
```

每个 fixture 是一份最小可解析的 Python 文件 + 一份期望结论。`check_report.py` 的思路可以复用：写一个 `check_corpus.py` 跑全部 fixture，比对结论档位。

### 2. 规则 ID 化 —— 让判据可寻址

现在所有判据都是 SKILL.md 和 audit-method.md 里的**散文**。后果：

- 报告里无法写"命中哪条判据"，只能复述因果链
- 用户无法关掉某条判据
- 无法统计哪条判据误报多

aislop 每条规则有 id（`ai-slop/swallowed-exception`）、severity、可 off、可 ignore。gatecreep 应该把 `audit-method.md` 第 4 节的六种失败场景**变成可枚举的检查项 ID**：

```yaml
- id: gate/valid-boundary-rejected
- id: gate/single-failure-escalated
- id: gate/limit-truncates-core-result
- id: gate/partial-as-complete
- id: gate/unreachable-capability
- id: gate/contract-implementation-conflict
```

报告的主要发现里加一行 `判据：gate/valid-boundary-rejected`。这样语料库、统计、用户配置都有抓手。

### 3. Rule notes —— 明确写"不判什么"

aislop 的 `python-mutable-default` 专门写了一段：不抓 FastAPI 的 `Body(default={})`，因为"包装器是否跨调用共享结果是框架语义，语法判不了"，并指向 flake8-bugbear 的 B008。

**写清楚边界比写清楚规则更难，也更有用。** gatecreep 的 Common Mistakes 是"做错了怎么办"，缺的是"这类情况我们主动不判"：

- 不判认证/授权是否过严（需要业务上下文，且误判代价最高）
- 不判限流阈值数值是否合适（需要流量数据）
- 不判纯代码风格导致的"复杂"（方法已声明代码量不是证据，但没说不判哪些具体形态）
- 不判第三方库内部的门禁（不在审计范围内，应记为 coverage 缺口而非发现）

建议单开 `references/limits.md`。

### 4. 基准测试集 —— 让结论可复现

aislop 有 research program：固定 cohort 扫开源、存 raw JSON、分类 finding、用回归测试修噪音规则、公布局限。

gatecreep 是模型判断，比规则匹配更难复现，但更需要。建议：

- 固定 5–10 个真实开源 Python agent/CLI（版本 pin 住）
- 人工标注每份的期望结论
- 每次改 SKILL.md 或 audit-method.md 后重跑，比对结论漂移
- 公布 precision/recall 和已知失败案例

这同时解决一个隐患：**方法文档改一个字，模型判断可能整体偏移**，现在没有任何手段发现。

### 5. 覆盖缺口时禁止下结论 —— 已做对，可加强

`check_report.py:69-70` 已经禁止在有缺口时说"项目没有门禁问题"，这是 aislop `unknown-directive` 的同构做法。

可以再进一步：缺口存在时，要求"主要发现"章节显式写出**该缺口可能掩盖哪类发现**。现在的规则只禁止了一句话，没要求正面交代盲区。

---

## 四、不要抄的

| 不抄 | 理由 |
|---|---|
| 0–100 评分 + `failBelow` 阈值 | 评分会诱导模型追求"把分打高"，而 audit-method 明确说"流程长度、层数和代码量本身不是证据"。一旦有分数，模型就会去数数 |
| `fix` 自动修复 | 自动删门禁是灾难。aislop 能自动删死代码，因为死代码删了不改变行为；门禁删了改变的是安全边界 |
| 纯正则判据 | sloppylint 的 `#\s*(obviously\|clearly)` 报"过度自信"就是反面教材。你的判据必须是证据链，不是模式匹配 |
| 60 条规则的大而全 | aislop 要覆盖 10 种语言所以必须摊薄。gatecreep 只做 Python agent/CLI，应该窄而深 |

---

## 五、gate 分类层建议

实测本仓库：**152 个 gate 里 117 个（77%）是控制流节点**（condition 48 + limit 42 + loop 27），真正会拒绝合法任务的只有 23 个（raise 3 + return 15 + exception-handler 5）。

宽提取是对的（先广撒网），但模型要在 152 条里逐条判断，噪音比太高。建议在 `add_gate` 里加一个 `gate_class` 字段做预分类，模型按类优先处理：

| gate_class | kind | 优先级 |
|---|---|---|
| `rejection` | raise, exit | 高——直接拒绝 |
| `truncation` | slice | 高——静默改变结果 |
| `swallow` | exception-handler | 高——吞掉失败 |
| `limit` | compare, numeric-constant, resource-argument | 中——阈值 |
| `skip` | continue, break, return(early) | 中——跳过/提前结束 |
| `flow-control` | condition, loop | 低——结构，默认不作发现 |

这不改变"事实不含判断"的原则（分类是结构性的，不是合理性判断），但能让模型先看高优先级的 23 条，再决定要不要翻剩下的 129 条。

---

## 六、建议顺序

1. **修 P0 崩溃**（`default=str` + `literal()` 归一化）—— 否则脚本在真实项目上不可用
2. **补装饰器与 assert 抓取** —— 补上最大的漏抓面
3. **建 `tests/corpus/`，先只放 reasonable 和 over 两类，各 3 个** —— 有了语料库，后面所有改动才有回归保护
4. **加 `gate_class` 预分类** —— 降低模型的噪音负担
5. **规则 ID 化 + `references/limits.md`** —— 让判据可寻址、边界可声明
6. **基准测试集** —— 最重，但也是唯一能证明"这个方法真的比规则匹配强"的东西
