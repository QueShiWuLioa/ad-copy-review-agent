"""OpenAI-compatible model adapter with strict output validation."""

from __future__ import annotations

import json
import re
from typing import Any

import requests


class ModelReviewError(RuntimeError):
    pass


SYSTEM_PROMPT = """你是谨慎的中文广告文案审核助手。你只能基于用户提供的文案、目标人群和转化目标分析，不得虚构平台政策、产品效果或投放数据。
请返回严格 JSON 对象，不要使用 Markdown。结构必须为：
{
  "score": 0到100的整数,
  "summary": "不超过60字的总体判断",
  "confidence": 0到1的小数,
  "items": [{"code":"英文短代码","category":"合规风险/价值表达/目标匹配/人群表达/可读性之一","severity":"高/中/低","evidence":"必须引用原文或明确指出缺失信息","suggestion":"可执行且不虚构事实的建议"}],
  "variants": [{"name":"版本名称","copy":"改写文案","hypothesis":"需要通过A/B测试验证的假设"}]
}
要求：variants 恰好2个；高风险只用于明显绝对化承诺、虚假保证或强监管风险；信息不足时明确说需要人工核验；生成版本不得添加未经提供的数字、资质、优惠或效果承诺。"""


def _extract_json(content: str) -> dict[str, Any]:
    content = content.strip()
    fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", content, flags=re.S | re.I)
    if fenced:
        content = fenced.group(1)
    try:
        value = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ModelReviewError("模型未返回有效 JSON") from exc
    if not isinstance(value, dict):
        raise ModelReviewError("模型结果必须是 JSON 对象")
    return value


def validate_model_result(value: dict[str, Any]) -> dict[str, Any]:
    try:
        score = int(value["score"])
        confidence = float(value["confidence"])
        summary = str(value["summary"]).strip()
        items = value["items"]
        variants = value["variants"]
    except (KeyError, TypeError, ValueError) as exc:
        raise ModelReviewError("模型结果缺少必要字段") from exc
    if not 0 <= score <= 100 or not 0 <= confidence <= 1:
        raise ModelReviewError("模型评分或置信度超出范围")
    if not summary or len(summary) > 100 or not isinstance(items, list) or not isinstance(variants, list):
        raise ModelReviewError("模型结果字段格式错误")
    if len(items) > 12 or len(variants) != 2:
        raise ModelReviewError("模型返回的问题或版本数量不符合要求")

    clean_items = []
    allowed_categories = {"合规风险", "价值表达", "目标匹配", "人群表达", "可读性"}
    for item in items:
        if not isinstance(item, dict) or item.get("severity") not in {"高", "中", "低"} or item.get("category") not in allowed_categories:
            raise ModelReviewError("模型问题项格式错误")
        clean_items.append({key: str(item.get(key, "")).strip() for key in ("code", "category", "severity", "evidence", "suggestion")})
        if not all(clean_items[-1].values()):
            raise ModelReviewError("模型问题项存在空字段")

    clean_variants = []
    for variant in variants:
        if not isinstance(variant, dict):
            raise ModelReviewError("模型版本格式错误")
        clean = {key: str(variant.get(key, "")).strip() for key in ("name", "copy", "hypothesis")}
        if not all(clean.values()) or len(clean["copy"]) > 500:
            raise ModelReviewError("模型版本内容不完整或过长")
        clean_variants.append(clean)

    return {
        "score": score,
        "summary": summary,
        "confidence": confidence,
        "items": clean_items,
        "variants": clean_variants,
        "risk_count": sum(item["severity"] == "高" for item in clean_items),
    }


def _extract_responses_content(value: dict[str, Any]) -> str:
    if isinstance(value.get("output_text"), str):
        return value["output_text"]
    for output in value.get("output", []):
        if not isinstance(output, dict):
            continue
        for content in output.get("content", []):
            if isinstance(content, dict) and content.get("type") == "output_text" and isinstance(content.get("text"), str):
                return content["text"]
    raise ModelReviewError("Responses API返回内容中没有 output_text")


def review_with_model(
    text: str,
    audience: str,
    goal: str,
    api_key: str,
    base_url: str,
    model: str,
    wire_api: str = "chat_completions",
    reasoning_effort: str = "",
) -> dict[str, Any]:
    if not api_key:
        raise ModelReviewError("未配置模型 API 密钥")
    user_content = json.dumps({"广告文案": text, "目标人群": audience, "转化目标": goal}, ensure_ascii=False)
    if wire_api == "responses":
        endpoint = f"{base_url.rstrip('/')}/responses"
        payload = {"model": model, "instructions": SYSTEM_PROMPT, "input": user_content, "store": False}
        if reasoning_effort:
            payload["reasoning"] = {"effort": reasoning_effort}
    elif wire_api == "chat_completions":
        endpoint = f"{base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
        }
    else:
        raise ModelReviewError("不支持的接口类型")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    try:
        response = requests.post(endpoint, headers=headers, json=payload, timeout=45)
        if response.status_code == 400 and wire_api == "chat_completions":
            fallback_payload = dict(payload)
            fallback_payload.pop("response_format", None)
            response = requests.post(endpoint, headers=headers, json=fallback_payload, timeout=45)
    except requests.Timeout as exc:
        raise ModelReviewError("模型服务响应超时，请稍后重试") from exc
    except requests.ConnectionError as exc:
        raise ModelReviewError("无法连接模型服务，请检查接口地址和网络") from exc
    except requests.RequestException as exc:
        raise ModelReviewError("模型请求发送失败，请稍后重试") from exc

    status_messages = {
        400: "请求参数不被模型服务支持，请检查模型名称",
        401: "API密钥无效或已失效",
        402: "模型账户余额不足或未开通计费",
        403: "API密钥没有调用该模型的权限",
        404: "接口地址或模型名称不存在",
        408: "模型服务请求超时",
        429: "调用过于频繁或额度已用完，请稍后重试",
    }
    if response.status_code >= 400:
        message = status_messages.get(response.status_code, f"模型服务返回错误（HTTP {response.status_code}）")
        raise ModelReviewError(message)
    try:
        response_value = response.json()
        content = _extract_responses_content(response_value) if wire_api == "responses" else response_value["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, ValueError) as exc:
        raise ModelReviewError("模型服务返回格式不兼容，请确认使用 Chat Completions 接口") from exc
    return validate_model_result(_extract_json(content))
