# 广告文案智能评审与 A/B 测试 Agent

面向广告运营和中小广告主的投放前评审原型。输入文案、目标人群与转化目标，系统检查绝对化承诺、过度催促、行动指令、利益点、长度和标点问题，并给出带证据建议及两个 A/B 版本。

项目采用“规则基线 + 可选大模型增强”。规则负责确定性检查；大模型通过兼容 OpenAI格式的接口补充语义审核和智能改写。模型输出必须通过 JSON结构校验，调用失败时自动降级，不代表广告平台最终审核结论。

## 运行
```powershell
python -m pip install -r requirements.txt
python src/generate_data.py
python src/evaluate.py
streamlit run app.py
```

## 配置智能模型

本地创建 `.streamlit/secrets.toml`，或在 Streamlit Cloud 的 App settings → Secrets 中填写：

```toml
LLM_API_KEY = "你的密钥"
LLM_BASE_URL = "https://api.deepseek.com/v1"
LLM_MODEL = "deepseek-chat"
```

也可以替换为其他兼容 OpenAI Chat Completions 格式的服务。不要把 `secrets.toml` 上传到 GitHub。模型调用可能产生费用，页面只在用户主动点击“运行智能审核”时调用。

## 实测结果

12条带转化目标的多标签样本：精确率83.33%，召回率100%，F1为90.91%，完全匹配率75%。失败案例保留在界面和 `data/evaluation_results.csv` 中。

同一文案会根据“获取线索、促进购买、产品试用”分别检查行动指令是否匹配，并生成不同的 A/B 版本。目标人群未在文案中体现时，也会给出可解释提示。

## 下一步

当前公开评测指标仅针对规则基线。下一步需由两名广告从业者标注真实匿名文案，对模型版本增加人工评分一致率、无依据结论率、成本及延迟指标。
