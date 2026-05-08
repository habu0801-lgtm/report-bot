#!/usr/bin/env python3
"""GPT-4oで実績画像を解析し、レポートを生成してGoogle Chatへ投稿する。"""

import base64
import json
import os
import urllib.error
import urllib.request
from pathlib import Path

from openai import OpenAI, APIError, APIConnectionError, RateLimitError


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

    try:
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
                                "url": f"data:{'image/jpeg' if Path(image_path).suffix.lower() in ('.jpg', '.jpeg') else 'image/png'};base64,{base64_image}"
                            },
                        },
                    ],
                }
            ],
            response_format={"type": "json_object"},
        )
    except RateLimitError:
        raise RuntimeError("OpenAI APIのレート制限に達しました。しばらく待ってから再試行してください。")
    except APIConnectionError:
        raise RuntimeError("OpenAI APIへの接続に失敗しました。ネットワークを確認してください。")
    except APIError as e:
        raise RuntimeError(f"OpenAI APIエラーが発生しました: {e}")

    return json.loads(response.choices[0].message.content)


def _compute_daily_targets(data: dict, remaining_days: int) -> dict:
    """数値項目に残り件数と日割り目標を付与する。%単位の項目はスキップ。"""
    result = {}
    for category, items in data.items():
        result[category] = {}
        for item_name, metrics in items.items():
            m = dict(metrics)
            target = metrics.get("目標", "-")
            actual = metrics.get("実績", "-")
            t_str = str(target)
            a_str = str(actual)
            if not t_str.endswith("%") and t_str not in ("-", "") and a_str not in ("-", ""):
                try:
                    t = float(t_str)
                    a = float(a_str)
                    remaining = max(0.0, t - a)
                    m["残り件数"] = int(remaining)
                    m["日割り目標"] = f"{remaining / remaining_days:.1f}"
                except (ValueError, ZeroDivisionError):
                    pass
            result[category][item_name] = m
    return result


def generate_report(
    data: dict,
    period: str,
    store_name: str = "古河店",
    report_date: str = "",
    remaining_days: int = 0,
    period_end: str = "",
) -> str:
    """GPT-4oで実績データを分析してレポートを生成する。"""
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    enriched = _compute_daily_targets(data, remaining_days) if remaining_days > 0 else data
    sep = "-" * 80

    prompt = f"""あなたは通信代理店の優秀なマネージャーです。
以下の実績データを分析して、Google Chat向けの実績レポートを作成してください。

# 入力情報
店舗名：{store_name}
対象期間：{period}
報告日：{report_date}
残り日数：{remaining_days}日（本日含む）
月末日：{period_end}

# 実績データ（残り件数・日割り目標は計算済み）
{json.dumps(enriched, ensure_ascii=False, indent=2)}

# 出力フォーマット（以下を厳密に守ること）

1行目: 【実績報告】{report_date}時点 良い点・改善点総評
2行目: （空行）
3行目以降: ▼総評 [2〜4文の総評。全体状況、良い点と課題を具体的に。改行なし]
（空行）
{sep}
✅ 良い点（順調・達成圏内） ※標準進捗および全国平均を上回っている項目です。
[達成率 >= 標準進捗 の項目を以下の形式で。達成率の高い順に列挙。項目間に空行を入れる]

[項目名]目標：[目標]件 / 実績：[実績]件
（達成率：[達成率] / 標準進捗 [標準進捗]）
[任意：特に優秀な場合や特記事項があれば1〜2文のコメント]

{sep}
⚠️ 改善点・リカバリー目標（残り{remaining_days}日） ※標準進捗に対して未達の項目です。（ ）内は
本日含む残り期間（{report_date}～{period_end}の{remaining_days}日間）での1日あたり必達獲得数です。

[達成率 < 標準進捗 の項目を【モバイル系】【金融・LD系】【BBC】でグループ化]
[各カテゴリ見出し行に任意でカテゴリ全体の一言コメントを追加可]
[項目名]目標：[目標]件 / 実績：[実績]件
（達成率：[達成率] / 標準進捗 [標準進捗]）日割り目標：[日割り目標]件 / 日（残り[残り件数]件）
[任意：1〜2文のコメント]

# ルール
- プレーンテキストのみ。#, *, **, `, -, _ などのMarkdown記法は絶対に使わない
- セパレーターは「{sep}」をそのまま使う（ハイフン80文字）
- 数値は実績データの値をそのまま使用。日割り目標も「日割り目標」フィールドの値をそのまま転記
- %単位の項目（au+1総販付帯率など）は「件」を「%」に変え、日割り目標は省略
- 良い点・改善点に該当する項目がない場合は「該当項目なし」と記載
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
        )
    except RateLimitError:
        raise RuntimeError("OpenAI APIのレート制限に達しました。しばらく待ってから再試行してください。")
    except APIConnectionError:
        raise RuntimeError("OpenAI APIへの接続に失敗しました。ネットワークを確認してください。")
    except APIError as e:
        raise RuntimeError(f"OpenAI APIエラーが発生しました: {e}")

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
        with urllib.request.urlopen(req, timeout=10) as response:
            if not (200 <= response.getcode() < 300):
                raise RuntimeError(f"Google Chat投稿に失敗しました: HTTP {response.getcode()}")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Google Chat投稿に失敗しました: HTTP {exc.code} {detail}")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Google Chatへの接続に失敗しました: {exc.reason}")
