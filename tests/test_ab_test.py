import unittest

from src.ab_test import analyze_ab_test


class ABTestTests(unittest.TestCase):
    def test_ctr_uplift_and_significance(self):
        result = analyze_ab_test(10000, 500, 25, 10000, 650, 30, "CTR")
        self.assertAlmostEqual(result["rate_a"], 0.05)
        self.assertAlmostEqual(result["rate_b"], 0.065)
        self.assertAlmostEqual(result["uplift"], 0.30)
        self.assertTrue(result["significant"])
        self.assertEqual(result["winner"], "B")

    def test_cvr_uses_clicks_as_denominator(self):
        result = analyze_ab_test(10000, 500, 25, 10000, 500, 35, "CVR")
        self.assertAlmostEqual(result["rate_a"], 0.05)
        self.assertAlmostEqual(result["rate_b"], 0.07)

    def test_invalid_funnel_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "点击量不能大于曝光量"):
            analyze_ab_test(10, 20, 1, 10, 2, 1, "CTR")

    def test_small_sample_is_flagged(self):
        result = analyze_ab_test(20, 1, 0, 20, 2, 1, "CTR")
        self.assertFalse(result["sample_sufficient"])
        self.assertFalse(result["significant"])


if __name__ == "__main__":
    unittest.main()
