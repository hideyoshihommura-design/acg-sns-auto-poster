"""
aozora-cg.com お知らせページのスクレイピングモジュール
"""

import json
import re
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass
from typing import Optional


NEWS_URL = "https://aozora-cg.com/news/"
HEADERS = {"User-Agent": "Mozilla/5.0 (compatible; ACG-SNS-Bot/1.0)"}


@dataclass
class Article:
    id: str           # 記事URL をIDとして使用
    title: str
    url: str
    date: str
    body: str
    image_url: Optional[str]


def fetch_latest_articles(limit: int = 5) -> list[Article]:
    """お知らせ一覧から最新記事を取得する"""
    res = requests.get(NEWS_URL, headers=HEADERS, timeout=10)
    res.raise_for_status()
    soup = BeautifulSoup(res.text, "html.parser")

    articles = []
    posts = soup.select(".news-post")

    for post in posts[:limit]:
        title_tag = post.select_one(".post-title a") or post.select_one("h2 a")
        if not title_tag:
            continue

        title = title_tag.get_text(strip=True)
        url = title_tag.get("href", "")
        if not url:
            continue

        article = fetch_article_detail(title, url)
        if article:
            articles.append(article)

    return articles


def fetch_article_detail(title: str, url: str) -> Optional[Article]:
    """個別記事ページから本文・画像・日付を取得する"""
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
        soup = BeautifulSoup(res.text, "html.parser")

        # 日付: JSON-LDから取得
        date = ""
        ld_script = soup.find("script", type="application/ld+json")
        if ld_script:
            try:
                ld = json.loads(ld_script.string)
                date = ld.get("datePublished", "")[:10]
            except Exception:
                pass

        # 本文
        content_el = soup.select_one("#content") or soup.select_one(".entry-content")
        body = content_el.get_text(separator="\n", strip=True) if content_el else ""
        body = re.sub(r"\n{3,}", "\n\n", body)[:1000]

        # アイキャッチ画像
        image_url = None
        og_image = soup.find("meta", property="og:image")
        if og_image:
            image_url = og_image.get("content")
        if not image_url:
            img = soup.select_one("#content img")
            if img:
                image_url = img.get("src")

        return Article(
            id=url,
            title=title,
            url=url,
            date=date,
            body=body,
            image_url=image_url,
        )

    except Exception as e:
        print(f"[scraper] 記事取得エラー {url}: {e}")
        return None
