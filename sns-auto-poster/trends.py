"""
トレンド・ニュース収集モジュール
介護・生成AIに特化したRSSフィードとGoogle Trendsから最新情報を取得する
"""

import re
import feedparser
from datetime import datetime
from typing import Optional


# 介護・福祉専門のRSSフィード
KAIGO_FEEDS = {
    "介護ニュース（Joint）": "https://www.joint-kaigo.com/feed/",
    "介護のほんね": "https://kaigonohonne.com/news/feed",
    "シルバー産業新聞": "https://www.silver-news.com/feed",
    "けあNews": "https://www.care-news.jp/feed",
    "福祉新聞": "https://www.fukushishimbun.co.jp/feed",
}

# 生成AI・AIビジネス専門のRSSフィード
GENAI_FEEDS = {
    "AIsmiley": "https://aismiley.co.jp/feed/",
    "AINOW": "https://ainow.ai/feed/",
    "ITmedia AI+": "https://rss.itmedia.co.jp/rss/2.0/aiplus.xml",
    "TechCrunch日本版": "https://jp.techcrunch.com/feed/",
    "日経テクノロジー": "https://xtech.nikkei.com/rss/index.rdf",
}

# 介護×AIに関連するキーワード（フィルタリング用）
KAIGO_KEYWORDS = [
    "介護", "在宅医療", "訪問介護", "デイサービス", "特養", "老人ホーム",
    "ケアマネ", "介護士", "介護職", "高齢者", "認知症", "福祉", "介護保険",
    "人材不足", "離職率", "介護記録", "シフト", "介護DX",
]

GENAI_KEYWORDS = [
    "生成AI", "ChatGPT", "Claude", "Gemini", "Copilot", "LLM",
    "AI活用", "AI業務", "AI研修", "DX", "自動化", "業務効率",
    "プロンプト", "AIツール", "人工知能", "AIリスキリング",
]


def _clean_html(text: str) -> str:
    """HTMLタグを除去してテキストを整形する"""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:200] if len(text) > 200 else text


def _score_article(title: str, summary: str) -> int:
    """介護・生成AIへの関連度スコアを計算する（高いほど関連度が高い）"""
    text = title + summary
    score = 0
    for kw in KAIGO_KEYWORDS:
        if kw in text:
            score += 2 if kw in title else 1
    for kw in GENAI_KEYWORDS:
        if kw in text:
            score += 2 if kw in title else 1
    return score


def fetch_kaigo_news(max_items: int = 8) -> list[dict]:
    """介護専門フィードからニュースを取得する"""
    articles = []
    for source_name, feed_url in KAIGO_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:max_items]:
                title = entry.get("title", "")
                summary = _clean_html(entry.get("summary", entry.get("description", "")))
                if title:
                    articles.append({
                        "title": title,
                        "summary": summary,
                        "source": source_name,
                        "published": entry.get("published", datetime.now().isoformat()),
                        "score": _score_article(title, summary),
                        "category": "介護",
                    })
        except Exception:
            continue
    return articles


def fetch_genai_news(max_items: int = 8) -> list[dict]:
    """生成AI専門フィードからニュースを取得し、業務活用関連に絞る"""
    articles = []
    for source_name, feed_url in GENAI_FEEDS.items():
        try:
            feed = feedparser.parse(feed_url)
            for entry in feed.entries[:max_items]:
                title = entry.get("title", "")
                summary = _clean_html(entry.get("summary", entry.get("description", "")))
                score = _score_article(title, summary)
                # 生成AI関連キーワードが含まれる記事のみ採用
                if title and any(kw in title + summary for kw in GENAI_KEYWORDS):
                    articles.append({
                        "title": title,
                        "summary": summary,
                        "source": source_name,
                        "published": entry.get("published", datetime.now().isoformat()),
                        "score": score,
                        "category": "生成AI",
                    })
        except Exception:
            continue
    return articles


def fetch_google_trends_kaigo_ai() -> list[str]:
    """
    Google Trendsから介護・AI関連のトレンドキーワードを取得する
    - 日本のトレンドを取得後、介護・AIキーワードで絞り込む
    - 該当なければ介護・AIの関連ワードを直接検索してトレンド上位を返す
    """
    try:
        from pytrends.request import TrendReq
        pytrends = TrendReq(hl="ja-JP", tz=540)

        # 介護・生成AIキーワードの関連トレンドを取得
        search_terms = ["介護AI", "生成AI 業務", "ChatGPT 介護", "介護DX"]
        related_keywords = []

        for term in search_terms[:2]:  # レート制限対策で2件のみ
            try:
                pytrends.build_payload([term], geo="JP", timeframe="now 7-d")
                related = pytrends.related_queries()
                if term in related and related[term]["top"] is not None:
                    top_queries = related[term]["top"]["query"].tolist()[:3]
                    related_keywords.extend(top_queries)
            except Exception:
                continue

        return list(dict.fromkeys(related_keywords))[:8]  # 重複除去して最大8件
    except Exception:
        return []


def fetch_trending_topics(theme: Optional[str] = None) -> dict:
    """
    介護・生成AIに特化したトレンド情報をまとめて取得する

    Returns:
        {
            "google_trends": [...],
            "news_articles": [...],  # 介護・生成AI関連に絞り込み済み・スコア順
            "fetched_at": "ISO datetime",
        }
    """
    # 介護ニュースと生成AIニュースをそれぞれ取得
    kaigo_articles = fetch_kaigo_news(max_items=6)
    genai_articles = fetch_genai_news(max_items=6)

    # 合算してスコア順に並べ替え
    all_articles = kaigo_articles + genai_articles
    all_articles.sort(key=lambda x: x["score"], reverse=True)

    # 介護・生成AIそれぞれ最低2件ずつ確保しながら上位8件を選択
    top_kaigo = [a for a in all_articles if a["category"] == "介護"][:3]
    top_genai = [a for a in all_articles if a["category"] == "生成AI"][:3]
    selected = top_kaigo + top_genai

    # 残りをスコア順で補完（最大8件）
    selected_titles = {a["title"] for a in selected}
    rest = [a for a in all_articles if a["title"] not in selected_titles]
    selected = (selected + rest)[:8]

    google_trends = fetch_google_trends_kaigo_ai()

    return {
        "google_trends": google_trends,
        "news_articles": selected,
        "fetched_at": datetime.now().isoformat(),
    }
