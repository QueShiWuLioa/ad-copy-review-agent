import unittest
from src.review import review_copy,generate_variants
class ReviewTests(unittest.TestCase):
    def test_absolute_claim(self): self.assertIn("absolute_claim",{x["code"] for x in review_copy("百分百有效，立即购买")["items"]})
    def test_good_copy(self): self.assertEqual(review_copy("帮助销售团队提升效率，立即咨询")["items"],[])
    def test_variants(self): self.assertEqual(len(generate_variants("帮助团队提升效率","销售团队","获取线索")),2)
if __name__=="__main__": unittest.main()
