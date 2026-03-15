"""
HubSpot Social API を使ってX・Instagram・Facebookに下書き投稿を作成するモジュール
"""

import os
import requests
from scraper import Article


HUBSPOT_API_BASE = "https://api.hubapi.com"


def _headers() -> dict:
    token = os.getenv("HUBSPOT_ACCESS_TOKEN")
    return {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }


def get_social_channels() -> list[dict]:
    """接続済みのSNSチャンネル一覧を取得する"""
    res = requests.get(
        f"{HUBSPOT_API_BASE}/broadcast/v1/channels/setting/publish/current",
        headers=_headers(),
        timeout=10,
    )
    res.raise_for_status()
    return res.json()


def create_draft_broadcast(
    channel_guid: str,
    message: str,
    article: Article,
) -> dict:
    """HubSpotにSNS下書き投稿を作成する（承認後に手動公開）"""
    payload = {
        "channelGuid": channel_guid,
        "content": {
            "body": message,
            "photoUrl": article.image_url or "",
            "linkUrl": article.url,
        },
        "status": "DRAFT",
    }

    res = requests.post(
        f"{HUBSPOT_API_BASE}/broadcast/v1/broadcasts",
        headers=_headers(),
        json=payload,
        timeout=10,
    )
    res.raise_for_status()
    return res.json()


def create_all_drafts(article: Article, generated_posts: dict) -> dict:
    """X・Instagram・Facebook の下書きをまとめて作成する"""
    platform_map = {
        "x": os.getenv("HUBSPOT_CHANNEL_X"),
        "instagram": os.getenv("HUBSPOT_CHANNEL_INSTAGRAM"),
        "facebook": os.getenv("HUBSPOT_CHANNEL_FACEBOOK"),
    }

    results = {}
    for platform, channel_guid in platform_map.items():
        if not channel_guid:
            print(f"[hubspot] {platform} のチャンネルGUIDが未設定のためスキップ")
            continue
        if platform not in generated_posts:
            continue

        message = generated_posts[platform]["content"]
        try:
            result = create_draft_broadcast(channel_guid, message, article)
            results[platform] = {"status": "ok", "broadcast_id": result.get("id")}
            print(f"[hubspot] {platform} 下書き作成完了: {result.get('id')}")
        except Exception as e:
            results[platform] = {"status": "error", "error": str(e)}
            print(f"[hubspot] {platform} 下書き作成エラー: {e}")

    return results
