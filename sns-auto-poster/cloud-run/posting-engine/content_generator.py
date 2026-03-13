"""
Vertex AI / Gemini を使ったコンテンツ生成
"""

import os
import vertexai
from vertexai.generative_models import GenerativeModel, Part
import re


GCP_PROJECT = os.environ.get("GCP_PROJECT")
GCP_LOCATION = os.environ.get("GCP_LOCATION", "asia-northeast1")

vertexai.init(project=GCP_PROJECT, location=GCP_LOCATION)
model = GenerativeModel("gemini-1.5-pro")


PLATFORM_RULES = {
    "twitter": {
        "max_chars": 140,
        "style": "簡潔でインパクトのある文章。ハッシュタグを2〜3個含める。",
    },
    "instagram": {
        "max_chars": 2200,
        "style": "親しみやすく感情に訴える文章。ハッシュタグを5〜10個含める。絵文字を適度に使用。",
    },
    "facebook": {
        "max_chars": 63206,
        "style": "詳しく丁寧な文章。読み応えのある内容にする。ハッシュタグは2〜3個。",
    },
    "tiktok": {
        "max_chars": 2200,
        "style": "若者向けのトレンド感ある文章。ハッシュタグを5〜10個含める。絵文字を多めに使用。",
    },
}


def generate_from_wordpress(post_title: str, post_content: str, post_url: str, platform: str) -> str:
    """WordPress記事からSNS投稿文を生成する"""
    rules = PLATFORM_RULES.get(platform, PLATFORM_RULES["twitter"])

    prompt = f"""
以下のWordPress記事をもとに、{platform}用のSNS投稿文を日本語で作成してください。

【記事タイトル】
{post_title}

【記事内容】
{post_content[:2000]}

【URL】
{post_url}

【ルール】
- 文字数: {rules["max_chars"]}文字以内
- スタイル: {rules["style"]}
- 投稿文のみ出力してください（説明文は不要）
- URLを末尾に含めてください
"""
    response = model.generate_content(prompt)
    return response.text.strip()


def generate_from_material(material_text: str, platform: str, topic: str = "") -> str:
    """提供素材からSNS投稿文を生成する"""
    rules = PLATFORM_RULES.get(platform, PLATFORM_RULES["twitter"])

    prompt = f"""
以下の素材をもとに、{platform}用のSNS投稿文を日本語で作成してください。

【素材】
{material_text[:3000]}

【テーマ・補足】
{topic}

【ルール】
- 文字数: {rules["max_chars"]}文字以内
- スタイル: {rules["style"]}
- 投稿文のみ出力してください（説明文は不要）
"""
    response = model.generate_content(prompt)
    return response.text.strip()


def generate_image_prompt(post_title: str, platform: str) -> str:
    """画像生成用のプロンプトを作成する"""
    prompt = f"""
以下のタイトルに合う{platform}用SNS画像の説明を英語で作成してください。
Imagen3での画像生成に使用します。

【タイトル】
{post_title}

【条件】
- プロフェッショナルでモダンなデザイン
- 日本のビジネスシーン向け
- テキストは含めない
- 1文で説明してください
"""
    response = model.generate_content(prompt)
    return response.text.strip()
