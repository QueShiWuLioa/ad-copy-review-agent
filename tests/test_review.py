import unittest
from src.review import review_copy,generate_variants
class ReviewTests(unittest.TestCase):
    def test_absolute_claim(self): self.assertIn("absolute_claim",{x["code"] for x in review_copy("百分百有效，立即购买")["items"]})
    def test_good_copy(self): self.assertEqual(review_copy("帮助销售团队提升效率，立即咨询")["items"],[])
    def test_variants(self): self.assertEqual(len(generate_variants("帮助团队提升效率","销售团队","获取线索")),2)
    def test_same_copy_changes_with_goal(self):
        text="帮助销售团队提升效率，立即咨询"
        lead={x["code"] for x in review_copy(text,"销售团队","获取线索")["items"]}
        purchase={x["code"] for x in review_copy(text,"销售团队","促进购买")["items"]}
        self.assertNotIn("goal_mismatch",lead)
        self.assertIn("goal_mismatch",purchase)
    def test_variants_use_goal_specific_cta(self):
        self.assertIn("立即咨询",generate_variants("帮助提升效率","销售团队","获取线索")[0]["copy"])
        self.assertIn("立即购买",generate_variants("帮助提升效率","销售团队","促进购买")[0]["copy"])
        self.assertIn("免费试用",generate_variants("帮助提升效率","销售团队","产品试用")[0]["copy"])
if __name__=="__main__": unittest.main()
