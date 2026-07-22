"""Transparent baseline for Chinese advertising copy review."""

from dataclasses import asdict, dataclass
import re


RISK_TERMS = {
    "absolute_claim": ["最便宜", "全网第一", "百分百", "100%", "绝对有效", "永久有效"],
    "urgency_pressure": ["最后一天", "仅限今天", "错过不再", "立即抢购"],
}
CTA_TERMS = ["了解详情", "立即咨询", "免费试用", "领取", "预约", "查看方案", "立即购买"]
BENEFIT_TERMS = ["提升", "降低", "节省", "帮助", "解决", "获得", "减少", "效率"]


@dataclass(frozen=True)
class ReviewItem:
    code: str
    category: str
    severity: str
    evidence: str
    suggestion: str


def review_copy(text: str) -> dict:
    text = text.strip()
    if not text:
        raise ValueError("广告文案不能为空")
    items: list[ReviewItem] = []
    for code, terms in RISK_TERMS.items():
        hits = [term for term in terms if term.lower() in text.lower()]
        if hits:
            items.append(ReviewItem(code, "合规风险", "高", f"包含：{'、'.join(hits)}", "改为可验证、有条件限定的客观表述。"))
    if not any(term in text for term in CTA_TERMS):
        items.append(ReviewItem("missing_cta", "转化表达", "中", "未发现明确行动指令", "补充与转化目标一致的行动指令。"))
    if not any(term in text for term in BENEFIT_TERMS) and not re.search(r"\d+[%％]?", text):
        items.append(ReviewItem("missing_benefit", "价值表达", "中", "缺少明确利益点或量化结果", "说明用户能获得的具体收益，并避免虚构数据。"))
    if len(text) > 80:
        items.append(ReviewItem("too_long", "可读性", "低", f"当前长度为 {len(text)} 字", "保留一个核心卖点，将文案压缩至80字以内。"))
    if text.count("!") + text.count("！") >= 3:
        items.append(ReviewItem("excessive_punctuation", "可读性", "低", "连续使用多个感叹号", "减少情绪化标点，提升专业感。"))
    penalty = sum({"高": 22, "中": 12, "低": 6}[item.severity] for item in items)
    return {"score": max(0, 100 - penalty), "items": [asdict(item) for item in items], "risk_count": sum(item.severity == "高" for item in items)}


def generate_variants(text: str, audience: str, goal: str) -> list[dict]:
    clean = text
    for terms in RISK_TERMS.values():
        for term in terms:
            clean = clean.replace(term, "值得信赖")
    clean = clean.rstrip("！!")
    cta = {"获取线索": "立即咨询", "促进购买": "查看详情", "产品试用": "免费试用"}.get(goal, "了解详情")
    return [
        {"name": "利益点版本", "copy": f"面向{audience}，{clean}。{cta}，获取适合你的方案。", "hypothesis": "突出适用人群和具体收益可提升点击意愿。"},
        {"name": "问题导向版本", "copy": f"还在为相关问题投入大量时间？{clean}。{cta}。", "hypothesis": "先唤起问题感知，再承接行动指令。"},
    ]
