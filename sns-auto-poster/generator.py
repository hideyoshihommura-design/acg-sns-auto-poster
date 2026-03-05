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
# LPのURL（全投稿に必ず含める）
LP_URL = "https://fc.horiemon.ai/kaigo"

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

# 各SNSの文字数制限と投稿仕様
SNS_SPECS = {
    "x": {
        "name": "X（Twitter）",
        "max_chars": None,
        "target_chars": "200〜280字",
        "structure": """
【構成】
① 冒頭1行：介護現場の「あるある」な悩みや気づきで共感を掴む（絵文字1個OK）
② 本文2〜4行：今日のニュース・トレンドをもとにした「1つの気づき or 実践ヒント」を簡潔に
③ まとめ1行：ホリエモンAI学校介護校への自然なつながり（押しつけない）
④ ハッシュタグ：2〜3個のみ（#介護AI #業務効率化 など）

【注意】
- 200〜280字に収める（毎日読んでもらうため短くテンポよく）
- 箇条書きは使わない。会話調の文体で
- 末尾にLP URLを必ず記載する： https://fc.horiemon.ai/kaigo
""",
    },
    "instagram": {
        "name": "Instagram",
        "max_chars": 2200,
        "target_chars": "本文250〜350字＋ハッシュタグ10〜15個",
        "structure": """
【構成】
① 冒頭1行（最重要）：「もっと見る」前に表示される部分。疑問形か共感フレーズで引き込む
② 空行
③ 本文：3〜4つの短いブロックに分け、各ブロックは2〜3行。絵文字を各ブロック冒頭に1個
   - ブロック1：介護現場の課題・悩み（今日のニュースと絡める）
   - ブロック2：AIを使うと具体的にどう変わるか（1つだけ）
   - ブロック3：ホリエモンAI学校介護校なら解決できる理由（1点のみ）
④ 空行
⑤ ハッシュタグ：10〜15個を1行にまとめて末尾に記載

【注意】
- 本文は250〜350字（ハッシュタグ除く）
- 1ブロックに詰め込みすぎない
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
① リード文1〜2行：今日の介護・AIニュースの話題に触れる（「〜というニュースを見ました」など）
② 本文：介護現場への影響・現場目線の考察を2〜3段落（各段落3〜4行）
   - 段落1：現場の課題と今日のトレンドの接点
   - 段落2：AIを使った具体的な解決イメージ
   - 段落3：ホリエモンAI学校介護校の紹介（1段落のみ・さりげなく）
③ 締め1行：読者への問いかけや行動を促す言葉

【注意】
- 350〜500字（Facebookは長文より「ちょうど読める」長さが反応率高い）
- ニュースソースの固有名詞（サービス名・法律名など）を1つは入れる
- ハッシュタグは3〜5個のみ
- 締めの一行の直後に「▶ 詳細はこちら：https://fc.horiemon.ai/kaigo」を必ず入れる
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
1. 「介護現場で働くスタッフ・管理職・経営者」が読んで「自分ごと」と感じる内容にする
2. 今日の最新ニュースを1つ自然に取り込む（記事名・固有名詞を活用）
3. AIを難しく語らず「こんな業務が楽になる」という具体的な場面で伝える
4. 介護業界特有の課題（人材不足・記録業務・離職率・シフト管理等）に絡める
5. 売り込みにならず、読者にとって有益な情報・共感を提供する形にする

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
                model="qwen/qwen3-32b",
                messages=[{"role": "user", "content": prompt}],
                max_tokens=1024,
                reasoning_effort="none",  # 思考プロセスの出力を無効化
            )
            content = response.choices[0].message.content
            # <think>...</think> ブロックが残っている場合は除去
            import re as _re
            content = _re.sub(r"<think>.*?</think>", "", content, flags=_re.DOTALL).strip()
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
