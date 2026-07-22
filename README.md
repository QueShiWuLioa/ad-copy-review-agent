# 广告文案智能评审与 A/B 测试 Agent

面向广告运营和中小广告主的投放前评审原型。输入文案、目标人群与转化目标，系统检查绝对化承诺、过度催促、行动指令、利益点、长度和标点问题，并给出带证据建议及两个 A/B 版本。

> 当前版本是透明规则基线，不声称已经训练大模型。合成测试集仅用于验证评测流程，不代表真实平台审核结论。

## 运行
```powershell
python -m pip install -r requirements.txt
python src/generate_data.py
python src/evaluate.py
streamlit run app.py
```

## 实测结果

12条多标签样本：精确率81.25%，召回率86.67%，F1为83.87%，完全匹配率58.33%。失败案例保留在界面和 `data/evaluation_results.csv` 中。

## 下一步

由两名广告从业者独立标注真实匿名文案；对比“大模型直接评审”和“规则提供证据后评审”；增加人工评分一致率、无依据结论率、成本及延迟指标。
