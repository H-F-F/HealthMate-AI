# AI 评测说明

## 目标

这个评测脚本主要验证三件事：

- 高风险症状是否会优先走规则分流
- 常见健康问题的风险等级是否基本合理
- 工具型问题是否触发了预期工具

## 数据集

- 路径：`data/evals/health_eval_cases.json`
- 覆盖内容：
  - BMI 计算
  - 饮水建议
  - 步数建议
  - 减脂建议
  - 睡眠问题
  - 高风险症状分流

## 运行方式

只跑规则分流：

```powershell
python scripts/evaluate_assistant.py --mode triage
```

调用真实模型和工具：

```powershell
python scripts/evaluate_assistant.py --mode live
```

限制评测样本数：

```powershell
python scripts/evaluate_assistant.py --mode live --max-cases 3
```

## 输出指标

- `Overall pass rate`：整体通过率
- `Risk match rate`：风险等级匹配率
- `Tool match rate`：工具命中率
- `Route match rate`：路由是否符合预期
- `Average latency`：平均耗时，仅 `live` 模式输出
- `Average tokens`：平均 token 消耗，仅 `live` 模式输出

## 使用建议

- `triage` 模式适合本地快速回归，不依赖模型服务
- `live` 模式适合看真实链路效果，需要配置 `DASHSCOPE_API_KEY`
- 若新增工具、规则或输出字段，记得同步更新评测集
