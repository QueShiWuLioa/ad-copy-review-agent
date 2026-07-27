from pathlib import Path
import os
import inspect
import json
import pandas as pd
import requests
import streamlit as st
from src.review import generate_variants, review_copy
from src.evaluate import evaluate
from src.llm_review import ModelReviewError, review_with_model
from src.ab_test import analyze_ab_test

ROOT=Path(__file__).parent

def review_with_compatible_adapter(text,audience,goal,api_key,base_url,model_name,wire_api,reasoning_effort,timeout_seconds):
    """Use the new adapter when present; keep XNova working with an old deployed module."""
    adapter_parameters=inspect.signature(review_with_model).parameters
    if "timeout_seconds" in adapter_parameters:
        return review_with_model(text,audience,goal,api_key,base_url,model_name,wire_api,reasoning_effort,timeout_seconds)
    if wire_api!="responses" and "wire_api" in adapter_parameters:
        return review_with_model(text,audience,goal,api_key,base_url,model_name,wire_api,reasoning_effort)
    if wire_api!="responses":
        return review_with_model(text,audience,goal,api_key,base_url,model_name)

    from src.llm_review import SYSTEM_PROMPT, validate_model_result, _extract_json
    endpoint=f"{base_url.rstrip('/')}/responses"
    payload={
        "model":model_name,
        "instructions":SYSTEM_PROMPT,
        "input":json.dumps({"广告文案":text,"目标人群":audience,"转化目标":goal},ensure_ascii=False),
        "store":False,
    }
    if reasoning_effort:
        payload["reasoning"]={"effort":reasoning_effort}
    try:
        response=requests.post(endpoint,headers={"Authorization":f"Bearer {api_key}","Content-Type":"application/json"},json=payload,timeout=timeout_seconds)
    except requests.Timeout as exc:
        raise ModelReviewError("模型服务响应超时，请稍后重试") from exc
    except requests.RequestException as exc:
        raise ModelReviewError("无法连接XNova，请检查网络和接口地址") from exc
    errors={400:"请求参数不受支持，请检查模型名称",401:"XNova API密钥无效",402:"XNova账户余额不足",403:"密钥没有模型权限",404:"XNova接口或模型不存在",429:"调用过频或额度已用完"}
    if response.status_code>=400:
        raise ModelReviewError(errors.get(response.status_code,f"XNova返回错误（HTTP {response.status_code}）"))
    try:
        value=response.json()
        content=value.get("output_text")
        if not content:
            for output in value.get("output",[]):
                for part in output.get("content",[]):
                    if part.get("type")=="output_text": content=part.get("text"); break
                if content: break
        if not content: raise ValueError("missing output_text")
        return validate_model_result(_extract_json(content))
    except (ValueError,TypeError,KeyError) as exc:
        raise ModelReviewError("XNova返回格式不兼容或模型未按要求返回JSON") from exc

def config_value(name, default=""):
    if os.getenv(name):
        return os.environ[name]
    try:
        return st.secrets.get(name, default)
    except FileNotFoundError:
        return default

deployed_api_key=config_value("LLM_API_KEY")
default_base_url=config_value("LLM_BASE_URL","https://api.xnova.online")
default_model_name=config_value("LLM_MODEL","gpt-5.5")
default_wire_api=config_value("LLM_WIRE_API","responses")
default_reasoning_effort=config_value("LLM_REASONING_EFFORT","medium")

st.set_page_config(page_title="广告文案智能评审",page_icon="✍️",layout="wide")
st.markdown("""<style>.stApp{background:#f5f7f8}.block-container{max-width:1280px;padding-top:2rem}h1{font-size:1.75rem!important;letter-spacing:0!important}[data-testid=stMetric]{background:white;border:1px solid #dfe4e8;border-top:3px solid #087e6b;border-radius:6px;padding:.8rem 1rem}[data-testid=stVerticalBlockBorderWrapper]{background:white;border-left:4px solid #c47a16!important;border-radius:6px!important}.stButton>button{border-radius:5px;background:#087e6b;color:white;border:0}@media(max-width:760px){.block-container{padding:3.75rem .75rem 2rem}}</style>""",unsafe_allow_html=True)
st.title("广告文案智能评审工作台")
st.caption("规则基线保证确定性检查，配置模型后可增加语义审核与智能改写。")

with st.sidebar:
    st.header("审核模式")
    with st.expander("API 接入配置",expanded=not bool(deployed_api_key)):
        session_api_key=st.text_input("API 密钥",value="",type="password",help="仅用于当前浏览器会话，不写入代码和结果文件。")
        base_url=st.text_input("接口地址",value=default_base_url)
        model_name=st.text_input("模型名称",value=default_model_name)
        wire_label=st.selectbox("接口类型",["Responses API","Chat Completions"],index=0 if default_wire_api=="responses" else 1)
        wire_api="responses" if wire_label=="Responses API" else "chat_completions"
        reasoning_effort=st.selectbox("推理强度",["none","low","medium","high","xhigh"],index=["none","low","medium","high","xhigh"].index(default_reasoning_effort) if default_reasoning_effort in ["none","low","medium","high","xhigh"] else 0,disabled=wire_api!="responses")
        timeout_seconds=st.number_input("超时时间（秒）",min_value=30,max_value=300,value=180,step=30)
        st.caption("文案审核建议使用 medium；xhigh通常更慢且费用更高。超时后不会自动重试，以免重复计费。")
        st.caption("XNova使用 Responses API。公共网站中填写的密钥会发送到本应用服务器，请仅在你信任的部署中使用。")
    api_key=session_api_key or deployed_api_key
    model_ready=bool(api_key and base_url and model_name)
    use_model=st.toggle("启用大模型增强",value=False,disabled=not model_ready)
    if model_ready:
        st.success(f"配置已就绪：{model_name} · {wire_label}")
        st.caption("仅点击“运行智能审核”时调用模型。")
    else:
        st.info("当前使用规则基线。可在上方填写 API配置，或由部署者在 Secrets中配置。")

left,right=st.columns([1,1])
with left:
    text=st.text_area("广告文案",value="全网第一的企业服务工具，百分百提升销售效率！",height=150,max_chars=300)
    audience=st.text_input("目标人群",value="中小企业销售负责人")
    goal=st.selectbox("转化目标",["获取线索","促进购买","产品试用"])
    run_model=st.button("运行智能审核",use_container_width=True,disabled=not use_model)
    st.caption("规则结果自动更新；模型审核需要主动运行，避免重复产生费用。")

rule_result=review_copy(text,audience,goal)
signature=(text,audience,goal,base_url,model_name,wire_api,reasoning_effort,timeout_seconds)
if run_model:
    try:
        with st.spinner("模型正在审核文案..."):
            st.session_state["model_review_result"]=review_with_compatible_adapter(text,audience,goal,api_key,base_url,model_name,wire_api,reasoning_effort if reasoning_effort!="none" else "",timeout_seconds)
            st.session_state["model_review_signature"]=signature
    except ModelReviewError as exc:
        st.error(f"{exc}，已保留规则审核结果。")
    except TypeError:
        st.error("智能审核返回了不兼容的数据类型，已保留规则审核结果。请查看应用日志定位具体字段。")
    except Exception:
        st.error("智能审核发生未预期错误，已保留规则审核结果。请查看应用日志定位问题。")

model_result=st.session_state.get("model_review_result") if st.session_state.get("model_review_signature")==signature else None
result=model_result if use_model and model_result else rule_result
review_source="大模型增强" if use_model and model_result else "规则基线"

with right:
    cols=st.columns(3); cols[0].metric("综合评分",result["score"]); cols[1].metric("问题数",len(result["items"])); cols[2].metric("高风险",result["risk_count"])
    st.caption(f"当前结果来源：{review_source}")
    with st.expander("综合评分如何计算"):
        if review_source=="规则基线":
            severity_counts={level:sum(item["severity"]==level for item in result["items"]) for level in ("高","中","低")}
            deduction=severity_counts["高"]*22+severity_counts["中"]*12+severity_counts["低"]*6
            st.write(f"规则基线从100分开始：高风险每项扣22分，中风险每项扣12分，低风险每项扣6分。当前为 100 - {deduction} = {result['score']} 分。")
            st.caption("该分数用于同一套规则下比较文案，不代表平台审核通过率或真实转化率。")
        else:
            st.write("模型依据合规、价值表达、目标匹配、人群表达和可读性给出0-100分，并返回理由与自评置信度。")
            st.caption("模型评分未经真实业务校准，不能与规则分数直接横向比较，最终结论需人工复核。")
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

review_tab,variant_tab,experiment_tab,evaluation_tab,method_tab=st.tabs(["评审结果","A/B文案","A/B实验","评测结果","方法说明"])
with review_tab:
    st.dataframe(pd.DataFrame(result["items"])[["category","severity","evidence","suggestion"]].rename(columns={"category":"类别","severity":"风险","evidence":"证据","suggestion":"建议"}) if result["items"] else pd.DataFrame(),use_container_width=True,hide_index=True)
with variant_tab:
    st.info("这里生成的是两个待测试文案，不代表已经完成 A/B实验。请在“A/B实验”中录入真实投放结果。")
    variants=model_result["variants"] if use_model and model_result else generate_variants(text,audience,goal)
    for variant in variants:
        with st.container(border=True): st.subheader(variant["name"]); st.write(variant["copy"]); st.caption(f"实验假设：{variant['hypothesis']}")
with experiment_tab:
    st.subheader("录入真实实验数据")
    metric=st.segmented_control("主指标",["CTR","CVR"],default="CTR",help="CTR=点击/曝光；CVR=转化/点击。实验前应先确定唯一主指标。")
    a_col,b_col=st.columns(2)
    with a_col:
        st.markdown("**版本 A（对照组）**")
        imp_a=st.number_input("A 曝光量",min_value=0,value=10000,step=100,key="imp_a")
        clk_a=st.number_input("A 点击量",min_value=0,value=500,step=10,key="clk_a")
        conv_a=st.number_input("A 转化量",min_value=0,value=25,step=1,key="conv_a")
    with b_col:
        st.markdown("**版本 B（实验组）**")
        imp_b=st.number_input("B 曝光量",min_value=0,value=10000,step=100,key="imp_b")
        clk_b=st.number_input("B 点击量",min_value=0,value=575,step=10,key="clk_b")
        conv_b=st.number_input("B 转化量",min_value=0,value=35,step=1,key="conv_b")
    try:
        ab=analyze_ab_test(imp_a,clk_a,conv_a,imp_b,clk_b,conv_b,metric)
        ab_cols=st.columns(4)
        ab_cols[0].metric(f"A {metric}",f"{ab['rate_a']:.2%}")
        ab_cols[1].metric(f"B {metric}",f"{ab['rate_b']:.2%}")
        ab_cols[2].metric("相对提升",f"{ab['uplift']:.2%}" if ab["uplift"] is not None else "无法计算")
        ab_cols[3].metric("p值",f"{ab['p_value']:.4f}")
        if not ab["sample_sufficient"]:
            st.warning("样本中的成功或失败数量小于5，正态近似不可靠，请继续收集数据。")
        elif ab["significant"]:
            st.success(f"在显著性水平0.05下差异具有统计显著性，当前主指标较高的是版本{ab['winner']}。仍需检查随机分流、实验周期和其他变量。")
        else:
            st.info("当前差异未达到统计显著，不能仅凭数值高低宣布胜出。建议继续收集样本或复查实验设计。")
        st.caption("p值表示在两个版本真实效果相同的前提下，观察到当前或更极端差异的概率；它不表示B胜出的概率。")
    except ValueError as exc:
        st.error(str(exc))
with evaluation_tab:
    evaluation_cases=pd.read_csv(ROOT/"data"/"evaluation_cases.csv")
    report,details=evaluate(evaluation_cases)
    st.info("样本来自项目作者为验证规则流程而人工构造的12条合成文案，不是真实广告平台数据。每条样本预先标注 expected_codes 和转化目标，审核函数看不到标准答案。")
    c=st.columns(4)
    c[0].metric("样本数",report["样本数"])
    c[1].metric("精确率",f"{report['精确率']:.1%}")
    c[2].metric("召回率",f"{report['召回率']:.1%}")
    c[3].metric("F1",f"{report['F1']:.1%}")
    with st.expander("这些指标从哪里来",expanded=True):
        st.write(f"本次逐标签比较得到：真阳性 TP={report['真阳性标签']}，假阳性 FP={report['假阳性标签']}，假阴性 FN={report['假阴性标签']}，正常样本={report['正常样本数']}条。")
        st.markdown(f"""
- **精确率 = TP / (TP + FP) = {report['精确率']:.1%}**：系统报出的问题中，有多少与标准标签一致。精确率低表示误报多。
- **召回率 = TP / (TP + FN) = {report['召回率']:.1%}**：标准答案中的问题，有多少被系统发现。召回率低表示漏报多。
- **F1 = 2 × 精确率 × 召回率 / (精确率 + 召回率) = {report['F1']:.1%}**：综合平衡精确率和召回率，只有二者都较高时F1才高。
""")
        st.caption("这些结果只说明当前规则在这12条合成样本上的表现，不能代表真实广告审核准确率，也不能作为模型效果数据。")
    st.dataframe(details[~details["完全匹配"]],use_container_width=True,hide_index=True)
with method_tab:
    st.markdown("- 规则基线负责确定性风险、CTA和格式检查。\n- 模型增强负责语义审核与改写，输出经过结构校验，失败时自动降级。\n- 当前评测指标只针对规则基线，不冒充模型评测结果。\n- A/B文案只是实验候选；A/B实验页使用双样本比例检验分析真实数据。\n- API密钥可由用户在当前会话输入，或从环境变量、Streamlit Secrets读取，不写入代码仓库。")
