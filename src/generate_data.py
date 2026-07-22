from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
CASES = [
    ("全网第一的学习工具，百分百提升成绩！立即购买！", "absolute_claim|urgency_pressure", "高风险夸大表达"),
    ("这款软件很好用，欢迎大家看看", "missing_cta|missing_benefit", "价值与行动指令不清"),
    ("帮助销售团队减少重复录入，立即咨询获取行业方案", "normal", "表达完整"),
    ("最后一天！错过不再！立即抢购！！！", "urgency_pressure|missing_benefit|excessive_punctuation", "过度催促"),
    ("免费试用智能报表工具，帮助运营团队提升分析效率", "normal", "表达完整"),
    ("绝对有效的获客方案，永久有效", "absolute_claim|missing_cta", "绝对化承诺"),
    ("专为小微企业设计的进销存工具，节省对账时间，了解详情", "normal", "表达完整"),
    ("我们的产品功能丰富、界面清晰、操作简单、支持多端协作、数据导入、自动报表以及权限管理，能够覆盖很多业务场景，也适合不同规模的团队使用，现在就来体验我们的产品和服务吧", "too_long|missing_cta", "信息过载"),
    ("领取新人优惠，降低首次采购成本", "normal", "表达完整"),
    ("专业企业服务平台", "missing_cta|missing_benefit", "信息不足"),
    ("100%解决皮肤问题，立即购买", "absolute_claim|missing_benefit", "违规效果承诺"),
    ("查看方案，帮助门店减少库存积压", "normal", "表达完整"),
]

if __name__ == "__main__":
    pd.DataFrame(CASES, columns=["copy", "expected_codes", "note"]).to_csv(ROOT / "data" / "evaluation_cases.csv", index=False, encoding="utf-8-sig")
