import os
import sys
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

# ローカル開発用：.envを読み込む
REPORT_BOT_DIR = Path.home() / "report-bot"
load_dotenv(REPORT_BOT_DIR / ".env", override=True)

# Streamlit Cloud用：Secretsがあれば環境変数に設定する
if "OPENAI_API_KEY" in st.secrets:
    os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"]

sys.path.insert(0, str(REPORT_BOT_DIR))
from analyze import extract_data_from_image, generate_report, post_to_google_chat

# --- 店舗設定（店舗追加時はここに追記するだけ） ---
STORE_CONFIGS = {
    "古河店": {
        "webhook_key": "FURUKAWA_WEBHOOK",
    },
    # 今後の追加例：
    # "〇〇店": {
    #     "webhook_key": "STOREB_WEBHOOK",
    # },
}

st.title("実績レポートBot")

if "stage" not in st.session_state:
    st.session_state.stage = "upload"

# --- Stage 1: アップロード ---
if st.session_state.stage == "upload":
    st.header("実績データの画像をアップロード")

    store_name = st.selectbox("店舗を選択", list(STORE_CONFIGS.keys()))
    period = st.text_input("対象期間（例：2026年4月）", placeholder="2026年4月")
    uploaded_file = st.file_uploader("画像を選択（png / jpg）", type=["png", "jpg", "jpeg"])

    if uploaded_file and period:
        if st.button("データ抽出を開始", type="primary"):
            save_path = REPORT_BOT_DIR / uploaded_file.name
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            with st.spinner("GPT-4oが画像からデータを読み取り中..."):
                data = extract_data_from_image(save_path)

            st.session_state.data = data
            st.session_state.period = period
            st.session_state.store_name = store_name
            st.session_state.image_path = str(save_path)
            st.session_state.stage = "confirm"
            st.rerun()

# --- Stage 2: データ確認・レポート生成・投稿 ---
elif st.session_state.stage == "confirm":
    store_name = st.session_state.store_name
    st.header(f"抽出されたデータを確認（{store_name}）")

    data = st.session_state.data

    for category, items in data.items():
        st.subheader(category)
        rows = []
        for item_name, metrics in items.items():
            row = {"項目": item_name}
            row.update(metrics)
            rows.append(row)
        st.table(rows)

    st.divider()

    col1, col2 = st.columns(2)

    with col1:
        if st.button("レポートを生成してGoogle Chatに投稿", type="primary"):
            with st.spinner("レポートを生成中..."):
                report = generate_report(st.session_state.data, st.session_state.period, store_name)

            webhook_key = STORE_CONFIGS[store_name]["webhook_key"]
            webhook_url = (
                st.secrets.get(webhook_key)
                or os.environ.get(webhook_key)
                or os.environ.get("GOOGLE_CHAT_WEBHOOK")
            )
            post_to_google_chat(report, webhook_url)

            st.success(f"{store_name}のGoogle Chatに投稿しました！")
            st.subheader("生成されたレポート")
            st.text(report)

            if st.button("新しい画像を処理する"):
                st.session_state.stage = "upload"
                st.rerun()

    with col2:
        if st.button("やり直す"):
            st.session_state.stage = "upload"
            st.rerun()
