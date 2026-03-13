"""
WordPress記事取得モジュール
WordPress REST API v2 から最新記事を取得・管理する
"""
import json
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

import requests


def _clean_html(text: str) -> str:
    """HTMLタグを除去してテキストを整形する"""
    text = re.sub(r"<[^>]+>", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def check_api_available(site_url: str) -> bool:
    """WordPress REST APIが利用可能かどうかを確認する"""
    base = site_url.rstrip("/")
    try:
        resp = requests.get(f"{base}/wp-json/wp/v2/posts", params={"per_page": 1}, timeout=10)
        return resp.ok
    except Exception:
        return False


def fetch_recent_articles(
    site_url: str,
    category_slug: Optional[str] = None,
    recent_hours: int = 48,
    max_items: int = 10,
) -> list[dict]:
    """WordPress REST API から直近 recent_hours 以内の公開記事を取得する（認証不要）"""
    base = site_url.rstrip("/")
    endpoint = f"{base}/wp-json/wp/v2/posts"

    params = {
        "per_page": max_items,
        "orderby": "date",
        "order": "desc",
        "status": "publish",
        "_fields": "id,date,date_gmt,title,content,excerpt,link,featured_media",
    }

    # カテゴリslugが指定されている場合はIDを取得してフィルタ
    if category_slug:
        try:
            cat_resp = requests.get(
                f"{base}/wp-json/wp/v2/categories",
                params={"slug": category_slug, "per_page": 1},
                timeout=10,
            )
            if cat_resp.ok and cat_resp.json():
                params["categories"] = cat_resp.json()[0]["id"]
        except Exception:
            pass

    try:
        resp = requests.get(endpoint, params=params, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[WordPress] 記事取得失敗: {e}")
        return []

    articles = []
    cutoff = datetime.now(timezone.utc) - timedelta(hours=recent_hours)

    for item in resp.json():
        # 日時をパース（date_gmt はUTC、date はサイトのタイムゾーン）
        pub_str = item.get("date_gmt") or item.get("date", "")
        try:
            if pub_str.endswith("Z"):
                pub_dt = datetime.fromisoformat(pub_str.replace("Z", "+00:00"))
            else:
                pub_dt = datetime.fromisoformat(pub_str)
                if pub_dt.tzinfo is None:
                    pub_dt = pub_dt.replace(tzinfo=timezone.utc)
        except Exception:
            pub_dt = datetime.now(timezone.utc)

        if pub_dt < cutoff:
            continue

        title = _clean_html(item.get("title", {}).get("rendered", ""))
        excerpt = _clean_html(item.get("excerpt", {}).get("rendered", ""))
        content_text = _clean_html(item.get("content", {}).get("rendered", ""))[:400]

        # アイキャッチ画像URL取得
        featured_image_url = None
        media_id = item.get("featured_media")
        if media_id:
            try:
                media_resp = requests.get(
                    f"{base}/wp-json/wp/v2/media/{media_id}",
                    params={"_fields": "source_url,media_details"},
                    timeout=10,
                )
                if media_resp.ok:
                    media_data = media_resp.json()
                    sizes = media_data.get("media_details", {}).get("sizes", {})
                    featured_image_url = (
                        sizes.get("large", {}).get("source_url")
                        or sizes.get("medium_large", {}).get("source_url")
                        or sizes.get("medium", {}).get("source_url")
                        or media_data.get("source_url")
                    )
            except Exception:
                pass

        articles.append({
            "id": item["id"],
            "title": title,
            "excerpt": excerpt if excerpt else content_text[:150],
            "content_preview": content_text,
            "url": item.get("link", ""),
            "published": pub_dt.isoformat(),
            "featured_image_url": featured_image_url,
            "source": "WordPress",
        })

    return articles


# --- 投稿済みIDの管理 ---

def _get_posted_ids_file() -> Path:
    output_dir = Path(os.getenv("OUTPUT_DIR", "./output"))
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir / "posted_wp_ids.json"


def load_posted_ids() -> set:
    """投稿済みWordPress記事IDのセットを返す"""
    f = _get_posted_ids_file()
    if not f.exists():
        return set()
    try:
        with open(f, encoding="utf-8") as fp:
            return set(json.load(fp))
    except Exception:
        return set()


def save_posted_id(article_id: int):
    """投稿済み記事IDを追記・保存する（直近500件を保持）"""
    ids = load_posted_ids()
    ids.add(article_id)
    id_list = sorted(ids)[-500:]
    with open(_get_posted_ids_file(), "w", encoding="utf-8") as f:
        json.dump(id_list, f)


def get_new_articles(
    site_url: str,
    category_slug: Optional[str] = None,
    recent_hours: int = 48,
) -> list[dict]:
    """まだSNSに投稿していない新着記事のみを返す"""
    posted_ids = load_posted_ids()
    articles = fetch_recent_articles(
        site_url=site_url,
        category_slug=category_slug,
        recent_hours=recent_hours,
    )
    return [a for a in articles if a["id"] not in posted_ids]
