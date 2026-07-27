"""A/B experiment calculations for click-through and conversion rates."""

from math import sqrt
from statistics import NormalDist


def analyze_ab_test(
    impressions_a: int,
    clicks_a: int,
    conversions_a: int,
    impressions_b: int,
    clicks_b: int,
    conversions_b: int,
    metric: str,
) -> dict:
    values = [impressions_a, clicks_a, conversions_a, impressions_b, clicks_b, conversions_b]
    if any(value < 0 for value in values):
        raise ValueError("实验数据不能为负数")
    if clicks_a > impressions_a or clicks_b > impressions_b:
        raise ValueError("点击量不能大于曝光量")
    if conversions_a > clicks_a or conversions_b > clicks_b:
        raise ValueError("转化量不能大于点击量")

    if metric == "CTR":
        success_a, total_a = clicks_a, impressions_a
        success_b, total_b = clicks_b, impressions_b
    elif metric == "CVR":
        success_a, total_a = conversions_a, clicks_a
        success_b, total_b = conversions_b, clicks_b
    else:
        raise ValueError("只支持 CTR 或 CVR")
    if total_a == 0 or total_b == 0:
        raise ValueError("用于计算指标的样本量必须大于0")

    rate_a = success_a / total_a
    rate_b = success_b / total_b
    pooled = (success_a + success_b) / (total_a + total_b)
    standard_error = sqrt(pooled * (1 - pooled) * (1 / total_a + 1 / total_b)) if 0 < pooled < 1 else 0
    z_score = (rate_b - rate_a) / standard_error if standard_error else 0
    p_value = 2 * (1 - NormalDist().cdf(abs(z_score))) if standard_error else 1.0
    expected_counts = [success_a, total_a - success_a, success_b, total_b - success_b]
    sample_sufficient = min(expected_counts) >= 5
    uplift = (rate_b - rate_a) / rate_a if rate_a else None
    return {
        "metric": metric,
        "rate_a": rate_a,
        "rate_b": rate_b,
        "absolute_change": rate_b - rate_a,
        "uplift": uplift,
        "z_score": z_score,
        "p_value": p_value,
        "sample_sufficient": sample_sufficient,
        "significant": sample_sufficient and p_value < 0.05,
        "winner": "B" if rate_b > rate_a else "A" if rate_a > rate_b else "持平",
    }
