import html as html_mod
import os
import sys
import tempfile
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

st.set_page_config(
    page_title="実績レポートBot",
    page_icon="📊",
    layout="centered",
)

REPORT_BOT_DIR = Path.home() / "report-bot"
load_dotenv(REPORT_BOT_DIR / ".env", override=True)

if "OPENAI_API_KEY" in st.secrets:
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]

sys.path.insert(0, str(REPORT_BOT_DIR))
from analyze import extract_data_from_image, generate_report, post_to_google_chat

STORE_CONFIGS = {
    "古河店": {
        "webhook_key": "FURUKAWA_WEBHOOK",
    },
}

CATEGORY_ICONS = {
    "モバイル": "📱",
    "LD系": "⚡",
    "BBC": "🌐",
}


def inject_global_css():
    st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=Noto+Sans+JP:wght@400;500;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Inter', 'Noto Sans JP', sans-serif;
}

.stApp {
    background-color: #0F1117;
}

.block-container {
    max-width: 960px !important;
    padding-top: 2rem !important;
}

.step-indicator {
    display: flex;
    align-items: center;
    margin-bottom: 2rem;
    padding: 1rem 1.5rem;
    background: #1C2333;
    border-radius: 12px;
    border: 1px solid #2D3748;
}
.step-item {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    flex: 1;
}
.step-number {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.85rem;
    font-weight: 700;
    flex-shrink: 0;
}
.step-number.active { background: #00C2FF; color: #0F1117; }
.step-number.inactive { background: #2D3748; color: #8896AE; }
.step-label { font-size: 0.875rem; font-weight: 500; letter-spacing: 0.04em; }
.step-label.active { color: #E8EDF5; }
.step-label.inactive { color: #8896AE; }
.step-connector { width: 40px; height: 2px; background: #2D3748; margin: 0 0.75rem; }

.page-title {
    font-size: 1.75rem;
    font-weight: 700;
    color: #E8EDF5;
    letter-spacing: -0.02em;
    vertical-align: middle;
}
.page-subtitle { font-size: 0.9rem; color: #8896AE; margin: 0.25rem 0 2rem 0; }
.title-accent {
    display: inline-block;
    width: 4px;
    height: 1.6rem;
    background: linear-gradient(180deg, #00C2FF, #0080FF);
    border-radius: 2px;
    margin-right: 0.75rem;
    vertical-align: middle;
}

.section-card {
    background: #1C2333;
    border: 1px solid #2D3748;
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1.25rem;
}
.section-card-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: #00C2FF;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin-bottom: 0.75rem;
}

.data-card {
    background: #1C2333;
    border: 1px solid #2D3748;
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1.25rem;
    overflow-x: auto;
}
.data-card-header {
    display: flex;
    align-items: center;
    gap: 0.6rem;
    margin-bottom: 1.25rem;
    padding-bottom: 0.75rem;
    border-bottom: 1px solid #2D3748;
}
.data-card-icon { font-size: 1.2rem; }
.data-card-title { font-size: 1rem; font-weight: 700; color: #E8EDF5; letter-spacing: 0.04em; }

.metrics-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.metrics-table thead tr { background: #0F1117; }
.metrics-table th {
    padding: 0.6rem 0.75rem;
    color: #8896AE;
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    text-align: right;
    border-bottom: 2px solid #2D3748;
}
.metrics-table th.col-item { text-align: left; }
.metrics-table td {
    padding: 0.75rem 0.75rem;
    color: #8896AE;
    text-align: right;
    vertical-align: middle;
}
.metrics-table td.col-item { text-align: left; color: #E8EDF5; font-weight: 500; }
.metrics-table td.col-jisseki { color: #E8EDF5; font-weight: 600; }
.col-num { min-width: 60px; }
.col-pct { min-width: 90px; }
.metrics-table tbody tr { border-bottom: 1px solid #2D3748; }
.metrics-table tbody tr:last-child { border-bottom: none; }
.metrics-table tbody tr:hover { background: rgba(0, 194, 255, 0.04); transition: background 0.15s ease; }

div[data-testid="stSelectbox"] label,
div[data-testid="stTextInput"] label,
div[data-testid="stFileUploader"] label {
    font-size: 0.8rem !important;
    font-weight: 600 !important;
    color: #8896AE !important;
    letter-spacing: 0.06em !important;
    text-transform: uppercase !important;
}

div[data-testid="stFileUploader"] > section {
    background: #0F1117 !important;
    border: 2px dashed #2D3748 !important;
    border-radius: 10px !important;
    transition: border-color 0.2s ease;
}
div[data-testid="stFileUploader"] > section:hover {
    border-color: #00C2FF !important;
}

div[data-testid="stButton"] > button[kind="primary"] {
    background: linear-gradient(135deg, #00C2FF 0%, #0080FF 100%) !important;
    color: #0F1117 !important;
    font-weight: 700 !important;
    font-size: 0.95rem !important;
    letter-spacing: 0.04em !important;
    border: none !important;
    border-radius: 8px !important;
    padding: 0.65rem 2rem !important;
    transition: opacity 0.2s ease, transform 0.1s ease;
}
div[data-testid="stButton"] > button[kind="primary"]:hover {
    opacity: 0.9 !important;
    transform: translateY(-1px) !important;
}
div[data-testid="stButton"] > button:not([kind="primary"]) {
    background: transparent !important;
    color: #8896AE !important;
    border: 1px solid #2D3748 !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
}
div[data-testid="stButton"] > button:not([kind="primary"]):hover {
    border-color: #8896AE !important;
    color: #E8EDF5 !important;
}

div[data-testid="stAlert"] {
    border-radius: 8px !important;
}
</style>
""", unsafe_allow_html=True)


def get_achievement_tier(achievement_str: str, standard_str: str) -> dict:
    try:
        ach = float(str(achievement_str).replace("%", "").strip())
        std = float(str(standard_str).replace("%", "").strip())
        if ach >= 100:
            return {"color": "#00C896", "bg": "rgba(0,200,150,0.15)", "icon": "✓ "}
        elif ach >= std:
            return {"color": "#00C896", "bg": "rgba(0,200,150,0.10)", "icon": ""}
        else:
            return {"color": "#FF4B6E", "bg": "rgba(255,75,110,0.12)", "icon": ""}
    except (ValueError, AttributeError):
        return {"color": "#8896AE", "bg": "rgba(136,150,174,0.08)", "icon": ""}


def render_step_indicator(current_stage: str):
    s1 = "active" if current_stage == "upload" else "inactive"
    s2 = "active" if current_stage == "confirm" else "inactive"
    st.markdown(f"""
<div class="step-indicator">
  <div class="step-item">
    <div class="step-number {s1}">1</div>
    <span class="step-label {s1}">データアップロード</span>
  </div>
  <div class="step-connector"></div>
  <div class="step-item">
    <div class="step-number {s2}">2</div>
    <span class="step-label {s2}">確認 &amp; 投稿</span>
  </div>
</div>
""", unsafe_allow_html=True)


def render_category_card(category: str, items: dict):
    icon = CATEGORY_ICONS.get(category, "📊")
    safe_cat = html_mod.escape(category)

    rows_html = ""
    for item_name, metrics in items.items():
        ach_val = metrics.get("達成率", "-")
        std_val = metrics.get("標準進捗", "-")
        tier = get_achievement_tier(ach_val, std_val)

        badge = (
            f'<span style="display:inline-block;padding:0.2rem 0.6rem;border-radius:20px;'
            f'background:{tier["bg"]};color:{tier["color"]};font-weight:700;font-size:0.85rem;'
            f'font-variant-numeric:tabular-nums;border:1px solid {tier["color"]}40;">'
            f'{tier["icon"]}{html_mod.escape(str(ach_val))}</span>'
        )

        def td(v):
            return f'<span style="color:#E8EDF5;font-variant-numeric:tabular-nums;">{html_mod.escape(str(v))}</span>'

        rows_html += f"""
<tr>
  <td class="col-item">{html_mod.escape(str(item_name))}</td>
  <td class="col-num">{td(metrics.get("目標", "-"))}</td>
  <td class="col-num col-jisseki">{td(metrics.get("実績", "-"))}</td>
  <td class="col-pct">{badge}</td>
  <td class="col-pct">{td(metrics.get("標準進捗", "-"))}</td>
  <td class="col-pct">{td(metrics.get("全国平均", "-"))}</td>
</tr>"""

    st.markdown(f"""
<div class="data-card">
  <div class="data-card-header">
    <span class="data-card-icon">{icon}</span>
    <span class="data-card-title">{safe_cat}</span>
  </div>
  <table class="metrics-table">
    <thead>
      <tr>
        <th class="col-item">項目</th>
        <th class="col-num">目標</th>
        <th class="col-num">実績</th>
        <th class="col-pct">達成率</th>
        <th class="col-pct">標準進捗</th>
        <th class="col-pct">全国平均</th>
      </tr>
    </thead>
    <tbody>{rows_html}</tbody>
  </table>
</div>
""", unsafe_allow_html=True)


def render_upload_stage():
    render_step_indicator("upload")

    st.markdown("""
<span class="title-accent"></span><span class="page-title">実績レポートBot</span>
<p class="page-subtitle">画像をアップロードしてAIが自動でデータを抽出・レポートを生成します</p>
""", unsafe_allow_html=True)

    st.markdown('<div class="section-card"><div class="section-card-label">基本情報</div>', unsafe_allow_html=True)
    col_store, col_period = st.columns([1, 1])
    with col_store:
        store_name = st.selectbox("店舗", list(STORE_CONFIGS.keys()))
    with col_period:
        period = st.text_input("対象期間", placeholder="例：2026年4月")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="section-card"><div class="section-card-label">実績データ画像</div>', unsafe_allow_html=True)
    uploaded_file = st.file_uploader(
        "PNG / JPG ファイルをドラッグ＆ドロップ、またはクリックして選択",
        type=["png", "jpg", "jpeg"],
    )
    st.markdown('</div>', unsafe_allow_html=True)

    if uploaded_file and period:
        if st.button("データ抽出を開始 →", type="primary", use_container_width=True):
            tmp_dir = Path(tempfile.mkdtemp())
            save_path = tmp_dir / uploaded_file.name
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            with st.spinner("GPT-4oが画像からデータを読み取り中..."):
                data = extract_data_from_image(save_path)
            st.session_state.data = data
            st.session_state.period = period
            st.session_state.store_name = store_name
            st.session_state.image_path = str(save_path)
            st.session_state.posted = False
            st.session_state.stage = "confirm"
            st.rerun()


def render_confirm_stage():
    store_name = st.session_state.store_name
    period = st.session_state.period

    render_step_indicator("confirm")

    safe_store = html_mod.escape(store_name)
    safe_period = html_mod.escape(period)
    st.markdown(f"""
<span class="title-accent"></span><span class="page-title">抽出データの確認</span>
<p class="page-subtitle">{safe_store} &nbsp;/&nbsp; {safe_period}</p>
""", unsafe_allow_html=True)

    for category, items in st.session_state.data.items():
        render_category_card(category, items)

    st.markdown('<div style="height:1rem;"></div>', unsafe_allow_html=True)

    if not st.session_state.get("posted"):
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.button("Google Chatに投稿する →", type="primary", use_container_width=True):
                with st.spinner("レポートを生成・投稿中..."):
                    report = generate_report(
                        st.session_state.data,
                        st.session_state.period,
                        store_name,
                    )
                    webhook_key = STORE_CONFIGS[store_name]["webhook_key"]
                    webhook_url = (
                        st.secrets.get(webhook_key)
                        or os.environ.get(webhook_key)
                        or os.environ.get("GOOGLE_CHAT_WEBHOOK")
                    )
                    post_to_google_chat(report, webhook_url)
                st.session_state.report = report
                st.session_state.posted = True
                st.rerun()
        with col2:
            if st.button("やり直す", use_container_width=True):
                st.session_state.stage = "upload"
                st.rerun()

    if st.session_state.get("posted"):
        st.success(f"{store_name} の Google Chat に投稿しました")

        with st.expander("生成されたレポートを確認", expanded=True):
            safe_report = html_mod.escape(st.session_state.report)
            st.markdown(f"""
<div class="section-card">
  <div class="section-card-label">投稿済みレポート</div>
  <pre style="background:#0F1117;color:#E8EDF5;font-family:'Noto Sans JP',sans-serif;
    font-size:0.875rem;line-height:1.8;padding:1rem;border-radius:8px;
    border:1px solid #2D3748;white-space:pre-wrap;margin:0;">{safe_report}</pre>
</div>
""", unsafe_allow_html=True)

        if st.button("新しい画像を処理する →", type="primary"):
            for key in ["data", "period", "store_name", "image_path", "report", "posted"]:
                st.session_state.pop(key, None)
            st.session_state.stage = "upload"
            st.rerun()


# --- メイン ---
inject_global_css()

if "stage" not in st.session_state:
    st.session_state.stage = "upload"

if st.session_state.stage == "upload":
    render_upload_stage()
elif st.session_state.stage == "confirm":
    render_confirm_stage()
