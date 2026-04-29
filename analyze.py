#!/usr/bin/env python3
"""GPT-4oで実績画像を解析し、レポートを生成してGoogle Chatへ投稿する。"""

import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from openai import OpenAI


def encode_image(image_path: Path) -> str:
    """画像をbase64エンコードする。"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def extract_data_from_image(image_path: Path) -> dict:
    """GPT-4oで画像から実績データを抽出する。"""
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    base64_image = encode_image(image_path)

    prompt = """
この実績データの画像から、以下の項目のデータを正確に読み取ってください。

抽出する項目：
- モバイル：新規合計、MNP合計、機変合計、UQ→au、総販合計
- LD系：auでんき、auPayカード、auPayゴールドカード、auじぶん銀行、au+1総販付帯率
- BBC：auひかり+BL光、auひかり、BL光

各項目について、以下の5つの数値を読み取ってください：
- 目標（分母の数値）
- 実績（分子の数値）
- 達成率（必ず%で表示）
- 標準進捗（必ず%で表示）
- 全国平均（必ず%で表示）

注意：au+1総販付帯率の目標・実績・達成率は%で表示する。
それ以外のモバイル・BBCの目標・実績は件数（数値のみ）で表示する。

必ずJSON形式のみで返してください。以下の形式で出力してください：
{
  "モバイル": {
    "新規合計": {"目標": 0, "実績": 0, "達成率": "0%", "標準進捗": "0%", "全国平均": "0%"},
    "MNP合計": {"目標": 0, "実績": 0, "達成率": "0%", "標準進捗": "0%", "全国平均": "0%"},
    "機変合計": {"目標": 0, "実績": 0, "達成率": "0%", "標準進捗": "0%", "全国平均": "0%"},
    "UQ→au": {"目標": 0, "実績": 0, "達成率": "0%", "標準進捗": "0%", "全国平均": "0%"},
    "総販合計": {"目標": 0, "実績": 0, "達成率": "0%", "標準進捗": "0%", "全国平均": "0%"}
  },
  "LD系": {
    "auでんき": {"目標": 0, "実績": 0, "達成率": "0%", "標準進捗": "0%", "全国平均": "0%"},
    "auPayカード": {"目標": 0, "実績": 0, "達成率": "0%", "標準進捗": "0%", "全国平均": "0%"},
    "auPayゴールドカード": {"目標": 0, "実績": 0, "達成率": "0%", "標準進捗": "0%", "全国平均": "0%"},
    "auじぶん銀行": {"目標": 0, "実績": 0, "達成率": "0%", "標準進捗": "0%", "全国平均": "0%"},
    "au+1総販付帯率": {"目標": "0%", "実績": "0%", "達成率": "0%", "標準進捗": "0%", "全国平均": "0%"}
  },
  "BBC": {
    "auひかり+BL光": {"目標": 0, "実績": 0, "達成率": "0%", "標準進捗": "0%", "全国平均": "0%"},
    "auひかり": {"目標": 0, "実績": 0, "達成率": "0%", "標準進捗": "0%", "全国平均": "0%"},
    "BL光": {"目標": 0, "実績": 0, "達成率": "0%", "標準進捗": "0%", "全国平均": "0%"}
  }
}
読み取れない項目は「-」と記載してください。
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{base64_image}"
                        },
                    },
                ],
            }
        ],
        response_format={"type": "json_object"},
    )

    return json.loads(response.choices[0].message.content)


def generate_report(data: dict, period: str, store_name: str = "古河店") -> str:
    """GPT-4oで実績データを分析してレポートを生成する。"""
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    prompt = f"""
あなたは通信代理店の優秀なマネージャーです。
以下の実績データを分析して、店舗向けの実績レポートを作成してください。

対象期間：{period}
実績データ：
{json.dumps(data, ensure_ascii=False, indent=2)}

レポートの要件：
1. 冒頭は「{period}ダッシュボード最新実績を配信します。」の次の行に「{store_name}の実績についてご報告いたします。」を入れる
2. 各カテゴリ（モバイル・LD系・BBC）ごとに状況をまとめる
3. 達成率が標準進捗・全国平均を上回っている項目を【良い点】として挙げる
4. 達成率が標準進捗・全国平均を下回っている項目を【課題】として挙げる
5. 全体の総評を簡潔に述べる

出力形式：
- 必ずプレーンテキストで出力する
- #、##、*、**、- などのMarkdown記法は絶対に使わない
- 【】と・を使った読みやすい形式にする
- Google Chatに投稿することを想定した簡潔な文章
"""

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
    )

    return response.choices[0].message.content.strip()


def post_to_google_chat(text: str, webhook_url: str) -> None:
    """Google Chatにテキストを投稿する。"""
    payload = {"text": text}
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json; charset=UTF-8"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as response:
            status = response.getcode()
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Google Chat投稿に失敗しました: HTTP {exc.code} {detail}")

    if status < 200 or status >= 300:
        raise RuntimeError(f"Google Chat投稿に失敗しました: HTTP {status}")
