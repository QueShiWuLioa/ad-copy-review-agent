"""Transparent baseline for Chinese advertising copy review."""

from dataclasses import asdict, dataclass
import re


RISK_TERMS = {
    "absolute_claim": ["最便宜", "全网第一", "百分百", "100%", "绝对有效", "永久有效"],
    "urgency_pressure": ["最后一天", "仅限今天", "错过不再", "立即抢购"],
}
LEGAL_RULES = {
    "medical_guarantee": {"industries": {"医疗健康"}, "terms": ["根治", "治愈率", "药到病除", "无副作用", "包治"], "suggestion": "删除无法证实的疗效保证，并由具备资质的人员核验医疗广告要求。"},
    "financial_guarantee": {"industries": {"金融服务"}, "terms": ["保本", "稳赚", "零风险", "保证收益", "稳赚不赔"], "suggestion": "删除保本或收益保证，补充必要风险提示并核验金融广告资质。"},
    "education_guarantee": {"industries": {"教育培训"}, "terms": ["保过", "包就业", "保证提分", "必上岸", "不过退款"], "suggestion": "删除结果保证，改为可验证的课程内容或服务说明。"},
    "privacy_violation": {"industries": {"通用", "电商零售", "医疗健康", "金融服务", "教育培训"}, "terms": ["无需授权获取手机号", "自动读取通讯录", "无需同意收集"], "suggestion": "删除未经同意收集个人信息的表述，并核验隐私授权流程。"},
    "fake_engagement": {"industries": {"通用", "电商零售"}, "terms": ["刷单", "返现好评", "虚假评价"], "suggestion": "删除诱导虚假交易或评价的内容，并核验平台规则。"},
}
REGULATED_INDUSTRIES = {"医疗健康", "金融服务", "教育培训"}
GOAL_CTAS = {
    "获取线索": ["立即咨询", "预约", "领取", "获取方案", "提交信息", "查看方案"],
    "促进购买": ["立即购买", "马上购买", "加入购物车", "领取优惠", "查看详情"],
    "产品试用": ["免费试用", "申请试用", "开始体验", "立即体验"],
}
CTA_TERMS = sorted({term for terms in GOAL_CTAS.values() for term in terms} | {"了解详情"})
BENEFIT_TERMS = ["提升", "降低", "节省", "帮助", "解决", "获得", "减少", "效率"]


@dataclass(frozen=True)
class ReviewItem:
    code: str
    category: str
    severity: str
    evidence: str
    suggestion: str


def review_copy(text: str, audience: str = "", goal: str = "获取线索", industry: str = "通用") -> dict:
    text = text.strip()
    if not text:
        raise ValueError("广告文案不能为空")
    items: list[ReviewItem] = []
    for code, terms in RISK_TERMS.items():
        hits = [term for term in terms if term.lower() in text.lower()]
        if hits:
            items.append(ReviewItem(code, "合规风险", "高", f"包含：{'、'.join(hits)}", "改为可验证、有条件限定的客观表述。"))
    for code, rule in LEGAL_RULES.items():
        hits = [term for term in rule["terms"] if term in text]
        if hits and (industry in rule["industries"] or code in {"privacy_violation"}):
            items.append(ReviewItem(code, "合法性风险", "高", f"包含：{'、'.join(hits)}", rule["suggestion"]))
    if industry in REGULATED_INDUSTRIES:
        items.append(ReviewItem("qualification_review", "资质核验", "低", f"当前选择的行业为“{industry}”", "上线前核对广告主主体资质、产品许可、证明材料及投放平台最新规则。"))
    if not any(term in text for term in CTA_TERMS):
        items.append(ReviewItem("missing_cta", "转化表达", "中", "未发现明确行动指令", f"补充适合“{goal}”的行动指令，例如“{GOAL_CTAS[goal][0]}”。"))
    elif not any(term in text for term in GOAL_CTAS[goal]):
        found = [term for term in CTA_TERMS if term in text]
        items.append(ReviewItem("goal_mismatch", "目标匹配", "中", f"当前行动指令“{'、'.join(found)}”与“{goal}”不完全匹配", f"改用“{GOAL_CTAS[goal][0]}”等目标一致的表达。"))
    if not any(term in text for term in BENEFIT_TERMS) and not re.search(r"\d+[%％]?", text):
        items.append(ReviewItem("missing_benefit", "价值表达", "中", "缺少明确利益点或量化结果", "说明用户能获得的具体收益，并避免虚构数据。"))
    if len(text) > 80:
        items.append(ReviewItem("too_long", "可读性", "低", f"当前长度为 {len(text)} 字", "保留一个核心卖点，将文案压缩至80字以内。"))
    if text.count("!") + text.count("！") >= 3:
        items.append(ReviewItem("excessive_punctuation", "可读性", "低", "连续使用多个感叹号", "减少情绪化标点，提升专业感。"))
    penalty = sum({"高": 22, "中": 12, "低": 6}[item.severity] for item in items)
    if audience.strip() and not any(part in text for part in re.findall(r"[\u4e00-\u9fff]{2,}", audience)):
        items.append(ReviewItem("audience_missing", "人群表达", "低", f"文案未明确体现目标人群“{audience}”", "补充目标人群或其典型场景，避免泛化表达。"))
        penalty += 6
    return {"score": max(0, 100 - penalty), "items": [asdict(item) for item in items], "risk_count": sum(item.severity == "高" for item in items), "goal": goal, "industry": industry}


def generate_variants(text: str, audience: str, goal: str) -> list[dict]:
    clean = text.rstrip("！!")
    replacements = {"全网第一":"专业", "最便宜":"更具性价比", "百分百":"有望", "100%":"有望", "绝对有效":"帮助改善", "永久有效":"持续可用", "最后一天":"限时", "错过不再":"欢迎了解", "立即抢购":"查看详情"}
    for old,new in replacements.items(): clean=clean.replace(old,new)
    for term in CTA_TERMS: clean=clean.replace(term,"")
    clean = clean.strip("，。；; ")
    cta = GOAL_CTAS[goal][0]
    endings={"获取线索":"获取适合你的方案","促进购买":"查看产品与优惠详情","产品试用":"体验核心功能"}
    return [
        {"name": f"{goal}·利益点版本", "copy": f"面向{audience}，{clean}。{cta}，{endings[goal]}。", "hypothesis": f"以明确利益点承接“{goal}”，降低决策成本。"},
        {"name": f"{goal}·场景版本", "copy": f"{audience}还在为相关问题投入大量时间？{clean}。{cta}，{endings[goal]}。", "hypothesis": "先唤起人群场景，再用目标一致的行动指令完成承接。"},
    ]
