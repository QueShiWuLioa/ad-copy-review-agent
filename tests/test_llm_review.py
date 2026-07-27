import unittest
from unittest.mock import Mock, patch

from src.llm_review import ModelReviewError, _extract_json, review_with_model, validate_model_result


def valid_result():
    return {
        "score": 72,
        "summary": "存在目标匹配问题，建议人工复核。",
        "confidence": 0.8,
        "items": [{"code": "goal_mismatch", "category": "目标匹配", "severity": "中", "evidence": "原文使用立即购买", "suggestion": "获取线索场景改用立即咨询"}],
        "variants": [
            {"name": "版本A", "copy": "面向销售团队，立即咨询了解方案。", "hypothesis": "目标一致的CTA可能提升线索率。"},
            {"name": "版本B", "copy": "减少重复录入，立即咨询。", "hypothesis": "突出利益点可能提升点击率。"},
        ],
    }


class ModelValidationTests(unittest.TestCase):
    def test_valid_result_is_normalized(self):
        result = validate_model_result(valid_result())
        self.assertEqual(result["risk_count"], 0)
        self.assertEqual(len(result["variants"]), 2)

    def test_json_fence_is_supported(self):
        self.assertEqual(_extract_json('```json\n{"score": 1}\n```')["score"], 1)

    def test_invalid_score_is_rejected(self):
        value = valid_result(); value["score"] = 120
        with self.assertRaises(ModelReviewError):
            validate_model_result(value)

    def test_invalid_severity_is_rejected(self):
        value = valid_result(); value["items"][0]["severity"] = "严重"
        with self.assertRaises(ModelReviewError):
            validate_model_result(value)

    def test_wrong_variant_count_is_rejected(self):
        value = valid_result(); value["variants"] = value["variants"][:1]
        with self.assertRaises(ModelReviewError):
            validate_model_result(value)

    @patch("src.llm_review.requests.post")
    def test_model_call_uses_compatible_endpoint(self, post):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"choices": [{"message": {"content": __import__("json").dumps(valid_result(), ensure_ascii=False)}}]}
        post.return_value = response
        result = review_with_model("帮助团队提升效率，立即咨询", "销售团队", "获取线索", "secret", "https://example.com/v1", "demo-model")
        self.assertEqual(result["score"], 72)
        args, kwargs = post.call_args
        self.assertEqual(args[0], "https://example.com/v1/chat/completions")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer secret")


if __name__ == "__main__":
    unittest.main()
