"""
Vertex AI（Gemini）を使ってSNS投稿文を生成するモジュール
"""

import os
import time
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
from scraper import Article


BRAND_CONTEXT = """
【会社概要】
名称: あおぞらケアグループ（ACG）
構成: 株式会社ACG・株式会社Lichi・社会福祉法人笑楽福祉会
拠点: 鹿児島県・福岡県を中心に50以上の介護・福祉施設
規模: 年商30億円・スタッフ600名
理念: 「ご利用者様に最期まで自分らしく主体的な人生を」

【事業内容】
訪問介護・訪問看護・デイサービス・有料老人ホーム・
サービス付き高齢者向け住宅・認知症グループホーム・
障がい者グループホーム・居宅介護支援・福祉用具貸与販売

【ブランドトーン】
- 温かみのある、地域に根ざした表現
- 利用者・家族に寄り添う共感的なコミュニケーション
- 専門性とやさしさを兼ね備えたプロフェッショナルなトーン
- 過度な宣伝色は避け、情報提供・共感を優先する

【ターゲット】
- 介護・支援が必要な高齢者とその家族
- 介護職・看護師として働きたい求職者
- 地域の介護・福祉に関心がある方
"""

SNS_SPECS = {
    "x": {
        "name": "X（Twitter）",
        "target_chars": "140〜200字",
        "structure": """
【構成】
① 冒頭1行：記事の要点を端的に伝える一文（絵文字1個OK）
② 本文2〜3行：読者の関心を引く具体的な内容
③ URL：記事のURL
④ ハッシュタグ：3〜5個
   例：#介護 #あおぞらケアグループ #鹿児島介護 #福祉 #介護職

【注意】
- 140〜200字に収める
- 親しみやすい会話調で
- ハッシュタグはURL・本文の後に記載
""",
    },
    "instagram": {
        "name": "Instagram",
        "target_chars": "本文200〜300字＋ハッシュタグ10〜15個",
        "structure": """
【構成】
① 冒頭1行：記事の魅力を伝える引きの一文
② 空行
③ 本文：2〜3ブロック（各ブロック2〜3行、絵文字を各ブロック冒頭に1個）
④ 空行
⑤ 「詳しくはプロフィールのリンクから👇」
⑥ ハッシュタグ：10〜15個

【注意】
- 温かみのある表現で
- 本文200〜300字（ハッシュタグ除く）
""",
    },
    "facebook": {
        "name": "Facebook",
        "target_chars": "300〜450字",
        "structure": """
【構成】
① リード文1〜2行：記事のポイントを分かりやすく紹介
② 本文：2〜3段落（各段落2〜3行）
③ 「詳細はこちら：{url}」
④ ハッシュタグ：3〜5個

【注意】
- 300〜450字
- 丁寧で信頼感のある文体
""",
    },
    "tiktok": {
        "name": "TikTok",
        "target_chars": "スライド用テキスト（各スライド30字以内・3〜5枚）",
        "structure": """
【構成】
スライド動画用のテキストを3〜5枚分作成してください。
各スライドのテキストは30字以内で、インパクトのある短い一文にしてください。

出力形式（必ずこの形式で）:
SLIDE1: （テキスト）
SLIDE2: （テキスト）
SLIDE3: （テキスト）
SLIDE4: （テキスト）※任意
SLIDE5: （テキスト）※任意

【注意】
- 各スライド30字以内
- 若い世代にも伝わる平易な表現
- 最後のスライドに必ず「あおぞらケアグループ」を入れる
""",
    },
}


def generate_posts(article: Article, platforms: list[str] = None) -> dict:
    """記事からSNS投稿文を生成する"""
    project_id = os.getenv("GCP_PROJECT_ID")
    location = os.getenv("VERTEX_LOCATION", "asia-northeast1")
    model_name = os.getenv("VERTEX_MODEL", "gemini-2.5-flash")

    vertexai.init(project=project_id, location=location)
    model = GenerativeModel(model_name)
    config = GenerationConfig(max_output_tokens=1024, temperature=0.7)

    target_platforms = platforms or list(SNS_SPECS.keys())
    results = {}

    for platform in target_platforms:
        if platform not in SNS_SPECS:
            continue

        spec = SNS_SPECS[platform]
        prompt = _build_prompt(spec, article)

        try:
            response = model.generate_content(prompt, generation_config=config)
            content = response.text.strip()
            time.sleep(1)
        except Exception as e:
            content = f"生成エラー: {e}"

        results[platform] = {
            "platform_name": spec["name"],
            "content": content,
            "char_count": len(content),
        }

    return results


def _build_prompt(spec: dict, article: Article) -> str:
    structure = spec["structure"].replace("{url}", article.url)
    return f"""あなたはあおぞらケアグループ（ACG）のSNS担当者です。
以下のブランド情報と記事内容をもとに、{spec['name']}向けの投稿文を1つ作成してください。

{BRAND_CONTEXT}

【記事情報】
タイトル: {article.title}
URL: {article.url}
投稿日: {article.date}
本文（抜粋）:
{article.body[:600]}

【投稿の構成・フォーマット（厳守）】
{structure}

目標文字数: {spec['target_chars']}

投稿文のみを出力してください（説明文・前置きは不要です）。"""
