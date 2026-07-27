import unittest
from unittest.mock import Mock, patch

from src.llm_review import ModelReviewError, _extract_json, _extract_responses_content, review_with_model, validate_model_result


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
        response.status_code = 200
        response.raise_for_status.return_value = None
        response.json.return_value = {"choices": [{"message": {"content": __import__("json").dumps(valid_result(), ensure_ascii=False)}}]}
        post.return_value = response
        result = review_with_model("帮助团队提升效率，立即咨询", "销售团队", "获取线索", "secret", "https://example.com/v1", "demo-model")
        self.assertEqual(result["score"], 72)
        args, kwargs = post.call_args
        self.assertEqual(args[0], "https://example.com/v1/chat/completions")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer secret")

    @patch("src.llm_review.requests.post")
    def test_invalid_key_has_clear_message(self, post):
        response = Mock(); response.status_code = 401
        post.return_value = response
        with self.assertRaisesRegex(ModelReviewError, "API密钥无效"):
            review_with_model("测试文案", "销售团队", "获取线索", "bad-key", "https://example.com/v1", "demo-model")

    @patch("src.llm_review.requests.post")
    def test_unsupported_json_mode_retries_without_response_format(self, post):
        rejected = Mock(); rejected.status_code = 400
        accepted = Mock(); accepted.status_code = 200
        accepted.json.return_value = {"choices": [{"message": {"content": __import__("json").dumps(valid_result(), ensure_ascii=False)}}]}
        post.side_effect = [rejected, accepted]
        result = review_with_model("测试文案", "销售团队", "获取线索", "secret", "https://example.com/v1", "demo-model")
        self.assertEqual(result["score"], 72)
        self.assertNotIn("response_format", post.call_args_list[1].kwargs["json"])

    @patch("src.llm_review.requests.post")
    def test_xnova_responses_api_request(self, post):
        response = Mock(); response.status_code = 200
        response.json.return_value = {"output_text": __import__("json").dumps(valid_result(), ensure_ascii=False)}
        post.return_value = response
        result = review_with_model("测试文案", "销售团队", "获取线索", "secret", "https://api.xnova.online", "gpt-5.5", "responses", "xhigh")
        self.assertEqual(result["score"], 72)
        args, kwargs = post.call_args
        self.assertEqual(args[0], "https://api.xnova.online/responses")
        self.assertEqual(kwargs["json"]["reasoning"], {"effort": "xhigh"})
        self.assertFalse(kwargs["json"]["store"])

    def test_nested_responses_output_is_supported(self):
        value = {"output": [{"type": "message", "content": [{"type": "output_text", "text": "result"}]}]}
        self.assertEqual(_extract_responses_content(value), "result")


if __name__ == "__main__":
    unittest.main()
