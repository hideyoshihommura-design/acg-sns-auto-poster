"""
SNS投稿文生成モジュール
Google Gemini APIを使って各SNSプラットフォーム向けの投稿文を生成する
"""

import os
import time
from datetime import date
from typing import Optional


# ホリエモンAI学校 介護校のブランド文脈
# LPのURL（全投稿に必ず含める）
LP_URL = "https://fc.horiemon.ai/kaigo"

BRAND_CONTEXT = """
【スクールの概要】
名称: 介護校 ホリエモンAI学校（HORIEMON AI SCHOOL）
キャッチコピー: 「AI活用の人材を、社内で育てるお手伝いをします」

【提供サービスの特徴】
- 240講座以上の動画講義（ChatGPT・Gemini・Copilot・NotebookLMなど初心者でも使いやすいツールに特化）
- チャットでの講師サポート（分からないことはいつでも質問可能）
- 毎月MTGで伴走支援（困りごとを一緒に解決）
- 業務・業種に合わせたオーダーメイドカリキュラム（2〜6ヶ月で設計）
- 「文章生成AI能力検定 初級」の資格取得サポート
- 法人向け生成AI研修サービス：実績社数伸び率No.1・講義の分かりやすさNo.1・信頼度No.1・満足度No.1

【受講料と助成金】
- 年間受講料: 310,000円/年（税込341,000円）
- 人材開発支援助成金（事業展開等リスキリング支援コース）で最大75%が助成対象
- 助成金活用後の実質負担: 1人あたり70,000円/年〜（最安 5,833円/月〜）
- 4名以上の受講で社労士サポートフィーを当社が負担（さらにお得）

【受講対象者】
- エンジニアではない介護・在宅医療事業者のスタッフ・管理職・経営者
- AI・DX・自動化が「わからない」非エンジニア（受講者の95%がAI未経験）
- PC操作ができる程度のスキルがあればOK

【読者・ターゲット】
- 介護事業所の経営者・管理職（サービス提供責任者、施設長、法人本部スタッフ等）
- 介護現場でのAI活用・DX推進に関心がある方
- 人材不足・業務負担の増加・離職率などの課題を抱えている介護事業者

【投稿で伝えるべきキーメッセージ】
1. 介護現場でAIを使えばこんな業務が楽になる（具体的な業務例）
2. AI未経験でも大丈夫・難しくない（非エンジニア向け）
3. 助成金を使えば実質70,000円〜でAI人材育成ができる
4. 介護業界の人材不足・業務負担・離職率問題をAIで解決できる
5. スタッフがAIを使えるようになると事業所全体の価値が上がる

【投稿で避けるべきこと】
- 一般的なビジネスDX・IT企業向けの内容（介護に紐付けること）
- 過度な売り込み・宣伝色の強い表現
- AIを難しく・専門的に語りすぎる表現
"""

# 各SNSの文字数制限と投稿仕様
SNS_SPECS = {
    "x": {
        "name": "X（Twitter）",
        "max_chars": None,
        "target_chars": "200〜280字",
        "structure": """
【構成】
① 冒頭1行：今日の生成AI・AIツールの最新ニュース・新機能を「へえ、こんなことできるの」と感じさせる一文（絵文字1個OK）
② 本文2〜4行：そのAIを介護現場で使うと「この業務が楽になる」という具体的なイメージを1つだけ展開
③ まとめ1行：ホリエモンAI学校介護校への自然なつながり（押しつけない）
④ LP URL： https://fc.horiemon.ai/kaigo
⑤ ハッシュタグ：5〜7個（必ず生成すること）
   例：#生成AI #介護AI #介護DX #業務効率化 #ChatGPT #介護職 #AIリスキリング

【注意】
- 200〜280字に収める（毎日読んでもらうため短くテンポよく）
- 箇条書きは使わない。会話調の文体で
- 「介護の悩み」から始めず、必ず「AIニュース・AI技術」から書き始める
- ハッシュタグは本文・URLの後に必ず記載する（省略禁止）
""",
    },
    "instagram": {
        "name": "Instagram",
        "max_chars": 2200,
        "target_chars": "本文250〜350字＋ハッシュタグ10〜15個",
        "structure": """
【構成】
① 冒頭1行（最重要）：今日の生成AI・AIツールニュースを「これ、介護で使えそう！」と思わせる一文で引き込む
② 空行
③ 本文：3つの短いブロック、各ブロックは2〜3行。絵文字を各ブロック冒頭に1個
   - ブロック1：今日のAIニュース・新機能の紹介（何ができるのか）
   - ブロック2：介護現場でこのAIを使うと「この場面が変わる」という具体的な活用イメージ
   - ブロック3：ホリエモンAI学校介護校でこのAIを学べる・実践できる（1点のみ）
④ 空行
⑤ ハッシュタグ：10〜15個を1行にまとめて末尾に記載

【注意】
- 本文は250〜350字（ハッシュタグ除く）
- 「介護の悩み」から始めず、必ず「AIニュース・新技術」から書き始める
- 価格・数字は1か所のみ（「助成金で月5,833円〜」など）
- ハッシュタグの前の行に「詳しくはこちら👇\nhttps://fc.horiemon.ai/kaigo」を必ず入れる
""",
    },
    "facebook": {
        "name": "Facebook",
        "max_chars": 63206,
        "target_chars": "350〜500字",
        "structure": """
【構成】
① リード文1〜2行：今日の生成AI・AIツールの最新ニュースを紹介する（「〜というAIが登場しました」「〜がアップデートされました」など）
② 本文：2〜3段落（各段落3〜4行）
   - 段落1：そのAI・新機能が何をできるのか、どう便利なのかを分かりやすく説明
   - 段落2：介護現場でこのAIを活用するとどんな業務・場面が変わるか（具体的に）
   - 段落3：ホリエモンAI学校介護校の紹介（1段落のみ・さりげなく）
③ 締め1行：「あなたの事業所でも試してみませんか？」など読者への問いかけ
④ 「▶ 詳細はこちら：https://fc.horiemon.ai/kaigo」
⑤ ハッシュタグ：5〜8個（必ず生成すること）
   例：#生成AI #介護AI #介護DX #業務効率化 #ChatGPT #介護経営 #AIリスキリング #介護職

【注意】
- 350〜500字（Facebookは長文より「ちょうど読める」長さが反応率高い）
- 「介護の悩み」から始めず、必ず「AIニュース・新技術の紹介」から書き始める
- AIの固有名詞（ツール名・サービス名）を必ず1つ入れる
- ハッシュタグは詳細URLの後に必ず記載する（省略禁止）
""",
    },
}


def build_prompt(
    platform: str,
    theme: str,
    business_name: str,
    google_trends: list[str],
    news_articles: list[dict],
    today: Optional[date] = None,
) -> str:
    """各SNSプラットフォーム向けのプロンプトを構築する"""
    spec = SNS_SPECS[platform]
    today_str = (today or date.today()).strftime("%Y年%m月%d日")

    # トレンドキーワードのテキスト
    trends_text = ""
    if google_trends:
        trends_text = f"\n【今日のGoogleトレンドキーワード（参考）】\n" + "、".join(google_trends[:5])

    # ニュース記事のテキスト
    news_text = ""
    if news_articles:
        news_lines = []
        for i, article in enumerate(news_articles[:4], 1):
            news_lines.append(f"{i}. {article['title']}（{article['source']}）")
            if article.get("summary"):
                news_lines.append(f"   {article['summary'][:100]}")
        news_text = "\n【今日の最新ニュース（参考）】\n" + "\n".join(news_lines)

    prompt = f"""あなたは介護業界専門のSNSマーケティング担当者です。
以下のスクール情報・ブランド文脈をしっかり理解した上で、{spec['name']}向けの投稿文を1つ作成してください。

{BRAND_CONTEXT}

【今回の投稿設定】
- 投稿日: {today_str}
- 今日のサブテーマ（参考）: {theme}
- 対象SNS: {spec['name']}
- 目標文字数: {spec['target_chars']}
{trends_text}
{news_text}

【投稿の構成・フォーマット（厳守）】
{spec['structure']}

【内容の必須条件】
1. 必ず「生成AI・AIツールの最新ニュースや新機能」を起点に書き始める（介護の悩みから始めない）
2. 取り上げるAI・ツールの固有名詞（例：ChatGPT、Gemini、Copilot、NotebookLM等の初心者向けツール）を必ず1つ入れる
3. 「このAIを介護現場で使うと○○業務がこう変わる」という具体的な活用イメージを1つだけ展開する
4. AIを難しく語らず「介護スタッフでも使える」という温度感で書く
5. 売り込みにならず、読者にとって「これ試してみたい」と思わせる情報提供の形にする

【使用するAIツールの注意】
- 紹介するAIツールは初心者でも使いやすいもの（ChatGPT・Gemini・Copilot・NotebookLM・Perplexity等）に限定する
- ClaudeやAPIを使うような上級者向けツールは「ホリエモンAI学校介護校で学べる」という文脈では使わない
- スクールでは初心者が日常業務でAIを使えるようになることを目標としている点を意識する

【出力の注意事項】
- 必ず日本語のみで書くこと（中国語・英語を混入しない）
- 同じ内容・表現を繰り返さない
- 価格・数字は正確に（「無料」と有料金額を同時に書かない）
- 目標文字数を必ず守ること
- LP URL「https://fc.horiemon.ai/kaigo」を必ず投稿文に含めること（省略・変更禁止）

投稿文のみを出力してください（説明文・見出し・前置きは不要です）。"""

    return prompt


def generate_posts(
    theme: str,
    business_name: str,
    trending_data: dict,
    platforms: Optional[list[str]] = None,
) -> dict:
    """
    複数のSNSプラットフォーム向けの投稿文を生成する

    Args:
        theme: 投稿テーマ
        business_name: ビジネス・サービス名
        trending_data: trends.fetch_trending_topics() の返り値
        platforms: 生成対象のプラットフォームリスト（Noneの場合は全て）

    Returns:
        {platform: {"platform_name": str, "content": str}, ...}
    """
    import vertexai
    from vertexai.generative_models import GenerativeModel, GenerationConfig

    project_id = os.getenv("GCP_PROJECT_ID")
    location = os.getenv("VERTEX_LOCATION", "asia-northeast1")
    model_name = os.getenv("VERTEX_MODEL", "gemini-2.0-flash-001")

    vertexai.init(project=project_id, location=location)
    model = GenerativeModel(model_name)
    generation_config = GenerationConfig(max_output_tokens=1024, temperature=0.7)

    target_platforms = platforms or list(SNS_SPECS.keys())
    results = {}

    google_trends = trending_data.get("google_trends", [])
    news_articles = trending_data.get("news_articles", [])
    today = date.today()

    for platform in target_platforms:
        if platform not in SNS_SPECS:
            continue

        prompt = build_prompt(
            platform=platform,
            theme=theme,
            business_name=business_name,
            google_trends=google_trends,
            news_articles=news_articles,
            today=today,
        )

        try:
            response = model.generate_content(prompt, generation_config=generation_config)
            content = response.text.strip()
            time.sleep(1)  # レート制限対策
        except Exception as e:
            content = f"生成エラー: {e}"

        results[platform] = {
            "platform_name": SNS_SPECS[platform]["name"],
            "content": content,
            "char_count": len(content),
            "max_chars": SNS_SPECS[platform]["max_chars"],
        }

    return results
