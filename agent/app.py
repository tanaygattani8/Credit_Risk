import os
import joblib
import pandas as pd
from google.cloud import bigquery
from dotenv import load_dotenv
import streamlit as st
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
 
load_dotenv()
 
PROJECT_ID    = os.environ.get("GCP_PROJECT_ID")
GEMINI_API_KEY = os.environ.get("GOOGLE_AI_API_KEY")
BQ_CLIENT     = bigquery.Client(project=PROJECT_ID)

SYSTEM_PROMPT = """You are a fraud investigation analyst for a payments company.
You have access to a fraud detection pipeline built on BigQuery with 590,540 payment transactions.
 
Your tools:
- query_bigquery: run SQL against the fraud database
- get_shap_explanation: explain WHY a specific transaction was flagged
- get_fraud_summary: get fraud rates grouped by a dimension
 
The fraud model is XGBoost with AUPRC=0.5253, AUROC=0.8926.
Fraud rate in the dataset is 3.50% (20,663 fraud out of 590,540 transactions).
 
Top fraud signals from SHAP: c13, c1, c14, email_domains_match, c6, transaction_amt.
Velocity features (card_txn_count_1h, card_txn_count_24h) were engineered in DBT.
 
When answering:
- Be concise and analytical
- Always cite specific numbers
- Explain findings in plain English a business stakeholder can understand
- If asked about a specific transaction, use get_shap_explanation first then query_bigquery for details
"""

@st.cache_resource
def load_artifacts():
    metadata = joblib.load("model_metadata.pkl")
    shap_df  = pd.read_csv("shap_values_sample.csv")
    return metadata, shap_df

# TOOLS
@tool
def query_bigquery(sql: str) -> str:
    """Run a SELECT SQL query against BigQuery and return results.
    Use fully qualified table names like:
    finance-497101.staging_mart.mart_fraud_features,
    finance-497101.staging_mart.mart_fraud_predictions,
    finance-497101.staging_mart.mart_fraud_summary.
    Limit results to 20 rows. Only SELECT queries allowed.
    """
    try:
        sql_clean = sql.strip().rstrip(";")
        if not sql_clean.upper().startswith("SELECT"):
            return "Error: only SELECT queries are allowed."
        df = BQ_CLIENT.query(sql_clean).to_dataframe()
        if df.empty:
            return "Query returned no results."
        return df.head(20).to_string(index=False)
    except Exception as e:
        return f"Query error: {str(e)}"


@tool
def get_shap_explanation(transaction_id: str) -> str:
    """Get SHAP feature importance for a specific transaction ID.
    Returns top features that drove the fraud prediction,
    and whether each pushed the score toward fraud or legit.
    Use this when asked WHY a transaction was flagged.
    """
    try:
        _, shap_df = load_artifacts()
        row = shap_df[shap_df['transaction_id'] == int(transaction_id)]
        if row.empty:
            return f"No SHAP data for transaction {transaction_id} — may not be in the sampled set."
        feature_cols = [c for c in shap_df.columns if c != 'transaction_id']
        shap_vals    = row[feature_cols].iloc[0]
        top_features = shap_vals.abs().sort_values(ascending=False).head(8)
        lines = [f"SHAP explanation for transaction {transaction_id}:\n"]
        for feat in top_features.index:
            val       = shap_vals[feat]
            direction = "↑ toward FRAUD" if val > 0 else "↓ toward LEGIT"
            lines.append(f"  {feat:<35} SHAP={val:+.4f}  {direction}")
        return "\n".join(lines)
    except Exception as e:
        return f"SHAP error: {str(e)}"


@tool
def get_fraud_summary(group_by: str = "product_cd") -> str:
    """Get fraud rate summary grouped by a dimension.
    Valid group_by values: product_cd, card4_type, card6_category,
    device_type, is_mobile, is_night_transaction, is_weekend, is_free_email.
    """
    valid = ['product_cd', 'card4_type', 'card6_category', 'device_type',
             'is_mobile', 'is_night_transaction', 'is_weekend', 'is_free_email']
    if group_by not in valid:
        return f"Invalid group_by. Choose from: {', '.join(valid)}"
    sql = f"""
        SELECT
            {group_by},
            COUNT(*) as total_transactions,
            SUM(is_fraud) as fraud_count,
            ROUND(AVG(is_fraud) * 100, 3) as fraud_rate_pct,
            ROUND(AVG(transaction_amt), 2) as avg_amount
        FROM `{PROJECT_ID}.staging_mart.mart_fraud_features`
        GROUP BY {group_by}
        ORDER BY fraud_rate_pct DESC
        LIMIT 15
    """
    try:
        df = BQ_CLIENT.query(sql).to_dataframe()
        return df.to_string(index=False)
    except Exception as e:
        return f"Error: {str(e)}"


# LANGGRAPH
@st.cache_resource
def build_agent():
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",
        google_api_key=GEMINI_API_KEY,
        temperature=0.1
    )
    tools = [query_bigquery, get_shap_explanation, get_fraud_summary]
    return create_react_agent(llm, tools)


# STREAMLIT
st.set_page_config(
    page_title="Fraud Investigation Agent",
    page_icon="🔍",
    layout="wide"
)
 
st.title("🔍 Fraud Investigation Agent")
st.caption("Powered by Gemini Flash + LangGraph | 590k payment transactions | AUROC 0.89")
 
with st.sidebar:
    st.markdown("### 💡 Example questions")
    examples = [
        "What is the overall fraud rate and total fraud amount?",
        "Which product category has the highest fraud rate?",
        "Is mobile fraud higher than desktop fraud?",
        "Show me the top 10 highest fraud score transactions",
        "What percentage of night transactions are fraudulent?",
        "How does fraud rate vary by card type?",
    ]
    for ex in examples:
        if st.button(ex, use_container_width=True):
            st.session_state.prefill = ex
 
    st.markdown("---")
    st.markdown("### 🔎 Explain a transaction")
    txn_input = st.text_input("Transaction ID", placeholder="e.g. 2987004")
    if st.button("Explain this transaction", use_container_width=True):
        st.session_state.prefill = f"Why was transaction {txn_input} flagged? Explain the key risk factors."
 
    st.markdown("---")
    st.markdown("**Model metrics**")
    st.metric("AUPRC", "0.5253")
    st.metric("AUROC", "0.8926")
    st.metric("Fraud rate", "3.50%")
 
if "messages" not in st.session_state:
    st.session_state.messages = []
if "prefill" not in st.session_state:
    st.session_state.prefill = ""
 
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
 
if st.session_state.prefill:
    prompt = st.session_state.prefill
    st.session_state.prefill = ""
else:
    prompt = st.chat_input("Ask anything about the fraud data...")
 
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)
 
    with st.chat_message("assistant"):
        with st.spinner("Investigating..."):
            try:
                agent = build_agent()
 
                # Build message history for LangGraph
                lc_messages = [SystemMessage(content=SYSTEM_PROMPT)]
                for m in st.session_state.messages:
                    if m["role"] == "user":
                        lc_messages.append(HumanMessage(content=m["content"]))
                    else:
                        lc_messages.append(AIMessage(content=m["content"]))
 
                result   = agent.invoke({"messages": lc_messages})
                last_message = result["messages"][-1].content
                if isinstance(last_message, list):
                    response = " ".join(
                        block["text"] for block in last_message
                        if isinstance(block, dict) and block.get("type") == "text"
                    )
                else:
                    response = last_message
            except Exception as e:
                response = f"Error: {str(e)}"
 
        st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})