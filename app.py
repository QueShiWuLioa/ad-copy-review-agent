from pathlib import Path
import pandas as pd
import streamlit as st
from src.review import generate_variants, review_copy
from src.evaluate import evaluate

ROOT=Path(__file__).parent
st.set_page_config(page_title="广告文案智能评审",page_icon="✍️",layout="wide")
st.markdown("""<style>.stApp{background:#f5f7f8}.block-container{max-width:1280px;padding-top:2rem}h1{font-size:1.75rem!important;letter-spacing:0!important}[data-testid=stMetric]{background:white;border:1px solid #dfe4e8;border-top:3px solid #087e6b;border-radius:6px;padding:.8rem 1rem}[data-testid=stVerticalBlockBorderWrapper]{background:white;border-left:4px solid #c47a16!important;border-radius:6px!important}.stButton>button{border-radius:5px;background:#087e6b;color:white;border:0}@media(max-width:760px){.block-container{padding:3.75rem .75rem 2rem}}</style>""",unsafe_allow_html=True)
st.title("广告文案智能评审工作台")
st.caption("投放前检查合规与表达问题，所有结论均展示触发证据。")

left,right=st.columns([1,1])
with left:
    text=st.text_area("广告文案",value="全网第一的企业服务工具，百分百提升销售效率！",height=150,max_chars=300)
    audience=st.text_input("目标人群",value="中小企业销售负责人")
    goal=st.selectbox("转化目标",["获取线索","促进购买","产品试用"])
    st.caption("修改任一输入后，结果会自动更新。")
with right:
    result=review_copy(text,audience,goal)
    cols=st.columns(3); cols[0].metric("综合评分",result["score"]); cols[1].metric("问题数",len(result["items"])); cols[2].metric("高风险",result["risk_count"])
    if not result["items"]: st.success("当前基线未发现明显问题。")
    for item in result["items"]:
        with st.container(border=True):
            st.subheader(f"{item['category']} · {item['severity']}风险")
            st.write(f"**证据：** {item['evidence']}")
            st.write(f"**建议：** {item['suggestion']}")

review_tab,variant_tab,evaluation_tab,method_tab=st.tabs(["评审结果","A/B版本","评测结果","方法说明"])
with review_tab:
    st.dataframe(pd.DataFrame(result["items"])[["category","severity","evidence","suggestion"]].rename(columns={"category":"类别","severity":"风险","evidence":"证据","suggestion":"建议"}) if result["items"] else pd.DataFrame(),use_container_width=True,hide_index=True)
with variant_tab:
    for variant in generate_variants(text,audience,goal):
        with st.container(border=True): st.subheader(variant["name"]); st.write(variant["copy"]); st.caption(f"实验假设：{variant['hypothesis']}")
with evaluation_tab:
    report,details=evaluate(pd.read_csv(ROOT/"data"/"evaluation_cases.csv")); c=st.columns(4)
    for col,(name,value) in zip(c,report.items()): col.metric(name,f"{value:.1%}" if name!="样本数" else value)
    st.dataframe(details[~details["完全匹配"]],use_container_width=True,hide_index=True)
with method_tab:
    st.markdown("- 当前版本为可解释规则基线，不冒充已经训练的大模型。\n- 标签只参与评测，不进入评审函数。\n- A/B版本为实验候选，需通过真实投放验证。\n- 下一版将对比大模型直评与证据约束评审。")
