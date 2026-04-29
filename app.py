import os
import sys
from pathlib import Path

import time

import streamlit as st
from dotenv import load_dotenv

# .envを読み込む
REPORT_BOT_DIR = Path.home() / "report-bot"
load_dotenv(REPORT_BOT_DIR / ".env", override=True)

sys.path.insert(0, str(REPORT_BOT_DIR))
from analyze import extract_data_from_image, generate_report, post_to_google_chat

st.title("実績レポートBot")

if "stage" not in st.session_state:
    st.session_state.stage = "upload"

# --- Stage 1: アップロード ---
if st.session_state.stage == "upload":
    st.header("実績データの画像をアップロード")
    period = st.text_input("対象期間（例：2026年4月）", placeholder="2026年4月")
    uploaded_file = st.file_uploader("画像を選択（png / jpg）", type=["png", "jpg", "jpeg"])

    if uploaded_file and period:
        if st.button("データ抽出を開始", type="primary"):
            save_path = REPORT_BOT_DIR / uploaded_file.name
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())

            with st.spinner("Geminiが画像からデータを読み取り中..."):
                data = extract_data_from_image(save_path)

            st.session_state.data = data
            st.session_state.period = period
            st.session_state.image_path = str(save_path)
            st.session_state.stage = "confirm"
            st.rerun()

# --- Stage 2: データ確認・レポート生成・投稿 ---
elif st.session_state.stage == "confirm":
    st.header("抽出されたデータを確認")

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
                report = generate_report(st.session_state.data, st.session_state.period)

            webhook_url = os.environ.get("GOOGLE_CHAT_WEBHOOK")
            post_to_google_chat(report, webhook_url)

            st.success("Google Chatに投稿しました！")
            st.subheader("生成されたレポート")
            st.text(report)

            if st.button("新しい画像を処理する"):
                st.session_state.stage = "upload"
                st.rerun()

    with col2:
        if st.button("やり直す"):
            st.session_state.stage = "upload"
            st.rerun()
