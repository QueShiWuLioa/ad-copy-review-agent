from pathlib import Path
import os
import pandas as pd
import streamlit as st
from src.review import generate_variants, review_copy
from src.evaluate import evaluate
from src.llm_review import ModelReviewError, review_with_model

ROOT=Path(__file__).parent

def config_value(name, default=""):
    if os.getenv(name):
        return os.environ[name]
    try:
        return st.secrets.get(name, default)
    except FileNotFoundError:
        return default

api_key=config_value("LLM_API_KEY")
base_url=config_value("LLM_BASE_URL","https://api.deepseek.com/v1")
model_name=config_value("LLM_MODEL","deepseek-chat")
model_ready=bool(api_key and base_url and model_name)

st.set_page_config(page_title="广告文案智能评审",page_icon="✍️",layout="wide")
st.markdown("""<style>.stApp{background:#f5f7f8}.block-container{max-width:1280px;padding-top:2rem}h1{font-size:1.75rem!important;letter-spacing:0!important}[data-testid=stMetric]{background:white;border:1px solid #dfe4e8;border-top:3px solid #087e6b;border-radius:6px;padding:.8rem 1rem}[data-testid=stVerticalBlockBorderWrapper]{background:white;border-left:4px solid #c47a16!important;border-radius:6px!important}.stButton>button{border-radius:5px;background:#087e6b;color:white;border:0}@media(max-width:760px){.block-container{padding:3.75rem .75rem 2rem}}</style>""",unsafe_allow_html=True)
st.title("广告文案智能评审工作台")
st.caption("规则基线保证确定性检查，配置模型后可增加语义审核与智能改写。")

with st.sidebar:
    st.header("审核模式")
    use_model=st.toggle("启用大模型增强",value=False,disabled=not model_ready)
    if model_ready:
        st.success(f"模型已连接：{model_name}")
        st.caption("仅点击“运行智能审核”时调用模型。")
    else:
        st.info("当前使用规则基线。部署者配置 API密钥后可启用模型。")

left,right=st.columns([1,1])
with left:
    text=st.text_area("广告文案",value="全网第一的企业服务工具，百分百提升销售效率！",height=150,max_chars=300)
    audience=st.text_input("目标人群",value="中小企业销售负责人")
    goal=st.selectbox("转化目标",["获取线索","促进购买","产品试用"])
    run_model=st.button("运行智能审核",use_container_width=True,disabled=not use_model)
    st.caption("规则结果自动更新；模型审核需要主动运行，避免重复产生费用。")

rule_result=review_copy(text,audience,goal)
signature=(text,audience,goal,model_name)
if run_model:
    try:
        with st.spinner("模型正在审核文案..."):
            st.session_state["model_review_result"]=review_with_model(text,audience,goal,api_key,base_url,model_name)
            st.session_state["model_review_signature"]=signature
    except ModelReviewError as exc:
        st.error(f"{exc}，已保留规则审核结果。")

model_result=st.session_state.get("model_review_result") if st.session_state.get("model_review_signature")==signature else None
result=model_result if use_model and model_result else rule_result
review_source="大模型增强" if use_model and model_result else "规则基线"

with right:
    cols=st.columns(3); cols[0].metric("综合评分",result["score"]); cols[1].metric("问题数",len(result["items"])); cols[2].metric("高风险",result["risk_count"])
    st.caption(f"当前结果来源：{review_source}")
    if use_model and not model_result:
        st.info("尚未运行当前输入的模型审核，暂时显示规则结果。")
    if model_result:
        st.write(f"**总体判断：** {model_result['summary']}")
        st.caption(f"模型自评置信度：{model_result['confidence']:.0%}；仍需人工复核。")
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
    variants=model_result["variants"] if use_model and model_result else generate_variants(text,audience,goal)
    for variant in variants:
        with st.container(border=True): st.subheader(variant["name"]); st.write(variant["copy"]); st.caption(f"实验假设：{variant['hypothesis']}")
with evaluation_tab:
    report,details=evaluate(pd.read_csv(ROOT/"data"/"evaluation_cases.csv")); c=st.columns(4)
    for col,(name,value) in zip(c,report.items()): col.metric(name,f"{value:.1%}" if name!="样本数" else value)
    st.dataframe(details[~details["完全匹配"]],use_container_width=True,hide_index=True)
with method_tab:
    st.markdown("- 规则基线负责确定性风险、CTA和格式检查。\n- 模型增强负责语义审核与改写，输出经过结构校验，失败时自动降级。\n- 当前评测指标只针对规则基线，不冒充模型评测结果。\n- A/B版本为实验候选，需人工审核并通过真实投放验证。\n- API密钥仅从环境变量或 Streamlit Secrets读取，不进入代码仓库。")
