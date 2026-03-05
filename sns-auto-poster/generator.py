"""
SNS投稿文生成モジュール
Google Gemini APIを使って各SNSプラットフォーム向けの投稿文を生成する
"""

import os
import time
from groq import Groq
from datetime import date
from typing import Optional


# ホリエモンAI学校 介護校のブランド文脈
BRAND_CONTEXT = """
【スクールの概要】
名称: 介護校 ホリエモンAI学校（HORIEMON AI SCHOOL）
キャッチコピー: 「AI活用の人材を、社内で育てるお手伝いをします」

【提供サービスの特徴】
- 240講座以上の動画講義（介護・在宅医療で実際に使える内容に特化）
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

# 各SNSの文字数制限と特徴
SNS_SPECS = {
    "x": {
        "name": "X（Twitter）",
        "max_chars": None,
        "style": "読みやすい長さで情報量を重視。改行・箇条書きを活用。ハッシュタグ2〜3個。",
    },
    "instagram": {
        "name": "Instagram",
        "max_chars": 2200,
        "style": "感情に訴える表現。改行を多用して読みやすく。絵文字を適度に使用。ハッシュタグ5〜10個を末尾に。",
    },
    "facebook": {
        "name": "Facebook",
        "max_chars": 63206,
        "style": "ストーリー性のある丁寧な文章。ビジネス向け。500〜800字程度。シェアされやすい内容。",
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
- 文字数目安: {"制限なし（300〜500字程度推奨）" if spec['max_chars'] is None else f"{spec['max_chars']}文字以内"}
- 文体・スタイル: {spec['style']}
{trends_text}
{news_text}

【投稿文を作成する際の必須条件】
1. 「介護現場で働くスタッフ・管理職・経営者」が読んで「自分ごと」と感じる内容にする
2. 今日の最新トレンドやニュースがあれば、介護業界・AI活用の文脈で自然に紐付ける
3. AIを難しく語らず「こんな業務が楽になる」という具体的な場面・効果で伝える
4. 介護業界特有の課題（人材不足・記録業務の負担・離職率・シフト管理等）に絡める
5. 売り込みにならず、読者にとって有益な情報・視点・共感を提供する形にする
6. ホリエモンAI学校介護校のアカウントとして自然な情報発信のトーンを維持する

投稿文のみを出力してください（説明文や前置きは不要です）。"""

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
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))
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
            response = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
            )
            content = response.choices[0].message.content
            time.sleep(3)  # レート制限対策
        except Exception as e:
            content = f"生成エラー: {e}"

        results[platform] = {
            "platform_name": SNS_SPECS[platform]["name"],
            "content": content,
            "char_count": len(content),
            "max_chars": SNS_SPECS[platform]["max_chars"],
        }

    return results
