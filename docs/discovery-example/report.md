# Discovery example

## 范围与完成状态
完成限定范围；未运行目标；语义由本次模型阅读判断，不代表完整覆盖。
## 公开功能清单
无
## 主要发现
无
## 非门禁问题
无
## 待人工复核
无
## 合理门禁摘要
无
## 门禁清单
无

功能：show 返回格式化字符串 [feature:f:show]；count 返回长度 [feature:f:count]。export 仅文档声明，实现未确认 [feature:f:export]。证据 [evidence:code] [evidence:doc]。
[scope:inspection:dynamic-registration] extension capabilities remain unknown
[scope:inspection:unmapped-paths] extension capabilities remain unknown
[scope:conflict:0] export 声明与实现存在未解决差异。

模型评价：已阅读 fixture 源码和文档，发现 show/count 共享入口，format_result 为内部辅助函数；register 动态导入未知模块，不将其认定为一个已知用户功能。初始 tool/display 经拆分合并得到最终清单。export 保留 unknown，不能报告为已实现或不存在。静态覆盖缺口保留；未执行被审计代码。
