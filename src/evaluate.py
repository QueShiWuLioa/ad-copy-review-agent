import json
from pathlib import Path
import pandas as pd
try:
    from .review import review_copy
except ImportError:
    from review import review_copy

ROOT = Path(__file__).resolve().parents[1]

def evaluate(df):
    rows=[]; tp=fp=fn=0
    for _, row in df.iterrows():
        expected=set() if row.expected_codes=="normal" else set(row.expected_codes.split("|"))
        predicted={item["code"] for item in review_copy(row["copy"])["items"]}
        tp+=len(expected & predicted); fp+=len(predicted-expected); fn+=len(expected-predicted)
        rows.append({"文案":row["copy"],"标准答案":"、".join(sorted(expected)) or "正常","评审结果":"、".join(sorted(predicted)) or "正常","完全匹配":expected==predicted})
    precision=tp/(tp+fp) if tp+fp else 0; recall=tp/(tp+fn) if tp+fn else 0
    report={"样本数":len(df),"精确率":round(precision,4),"召回率":round(recall,4),"F1":round(2*precision*recall/(precision+recall),4) if precision+recall else 0,"完全匹配率":round(sum(x["完全匹配"] for x in rows)/len(rows),4)}
    return report,pd.DataFrame(rows)

if __name__=="__main__":
    report,details=evaluate(pd.read_csv(ROOT/"data"/"evaluation_cases.csv"))
    details.to_csv(ROOT/"data"/"evaluation_results.csv",index=False,encoding="utf-8-sig")
    (ROOT/"data"/"evaluation_report.json").write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(json.dumps(report,ensure_ascii=False,indent=2))
