"""
SNS投稿モジュール
X (Twitter), Instagram, Facebook への実際の投稿を行う

必要な環境変数:
  X (Twitter):
    X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET
  Instagram / Facebook (Meta Graph API):
    META_PAGE_ACCESS_TOKEN
    FACEBOOK_PAGE_ID
    INSTAGRAM_BUSINESS_ACCOUNT_ID
"""
import os
import time
from typing import Optional


def post_to_x(content: str) -> dict:
    """X (Twitter API v2) にテキストを投稿する"""
    try:
        import tweepy
    except ImportError:
        return {"success": False, "platform": "x", "error": "tweepy がインストールされていません: pip install tweepy"}

    api_key = os.getenv("X_API_KEY")
    api_secret = os.getenv("X_API_SECRET")
    access_token = os.getenv("X_ACCESS_TOKEN")
    access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")

    if not all([api_key, api_secret, access_token, access_token_secret]):
        return {"success": False, "platform": "x", "error": "X_API_KEY / X_API_SECRET / X_ACCESS_TOKEN / X_ACCESS_TOKEN_SECRET が未設定です"}

    try:
        client = tweepy.Client(
            consumer_key=api_key,
            consumer_secret=api_secret,
            access_token=access_token,
            access_token_secret=access_token_secret,
        )
        # X の文字制限: 無料プランは140字、有料は長文可。安全のため280字でカット
        response = client.create_tweet(text=content[:280])
        tweet_id = response.data["id"]
        return {
            "success": True,
            "platform": "x",
            "post_id": str(tweet_id),
            "url": f"https://x.com/i/web/status/{tweet_id}",
        }
    except Exception as e:
        return {"success": False, "platform": "x", "error": str(e)}


def post_to_facebook(content: str) -> dict:
    """Facebook Page に投稿する (Meta Graph API v21.0)"""
    import requests

    page_id = os.getenv("FACEBOOK_PAGE_ID")
    access_token = os.getenv("META_PAGE_ACCESS_TOKEN")

    if not all([page_id, access_token]):
        return {"success": False, "platform": "facebook", "error": "FACEBOOK_PAGE_ID / META_PAGE_ACCESS_TOKEN が未設定です"}

    try:
        resp = requests.post(
            f"https://graph.facebook.com/v21.0/{page_id}/feed",
            data={
                "message": content,
                "access_token": access_token,
            },
            timeout=20,
        )
        resp.raise_for_status()
        post_id = resp.json().get("id", "")
        return {
            "success": True,
            "platform": "facebook",
            "post_id": post_id,
            "url": f"https://www.facebook.com/{post_id.replace('_', '/posts/')}",
        }
    except Exception as e:
        error_detail = str(e)
        try:
            error_detail = e.response.json().get("error", {}).get("message", str(e))
        except Exception:
            pass
        return {"success": False, "platform": "facebook", "error": error_detail}


def post_to_instagram(content: str, image_url: Optional[str] = None) -> dict:
    """
    Instagram Business Account に投稿する (Meta Graph API v21.0)

    Instagram API の制約:
    - 画像URL が必須（テキストのみの投稿は不可）
    - 画像URLは公開アクセス可能なHTTPSのURL である必要がある
    - JPEG/PNG/GIF 対応
    """
    import requests

    ig_account_id = os.getenv("INSTAGRAM_BUSINESS_ACCOUNT_ID")
    access_token = os.getenv("META_PAGE_ACCESS_TOKEN")

    if not all([ig_account_id, access_token]):
        return {"success": False, "platform": "instagram", "error": "INSTAGRAM_BUSINESS_ACCOUNT_ID / META_PAGE_ACCESS_TOKEN が未設定です"}

    if not image_url:
        return {
            "success": False,
            "platform": "instagram",
            "error": "Instagram投稿には画像URLが必要です。WordPressのアイキャッチ画像を設定してください。",
        }

    try:
        # Step 1: メディアコンテナを作成
        container_resp = requests.post(
            f"https://graph.facebook.com/v21.0/{ig_account_id}/media",
            data={
                "image_url": image_url,
                "caption": content,
                "access_token": access_token,
            },
            timeout=30,
        )
        container_resp.raise_for_status()
        container_id = container_resp.json().get("id")

        if not container_id:
            return {"success": False, "platform": "instagram", "error": "メディアコンテナの作成に失敗しました"}

        # Step 2: コンテナ処理を待機してから公開
        time.sleep(5)
        publish_resp = requests.post(
            f"https://graph.facebook.com/v21.0/{ig_account_id}/media_publish",
            data={
                "creation_id": container_id,
                "access_token": access_token,
            },
            timeout=30,
        )
        publish_resp.raise_for_status()
        post_id = publish_resp.json().get("id", "")
        return {
            "success": True,
            "platform": "instagram",
            "post_id": post_id,
        }
    except Exception as e:
        error_detail = str(e)
        try:
            error_detail = e.response.json().get("error", {}).get("message", str(e))
        except Exception:
            pass
        return {"success": False, "platform": "instagram", "error": error_detail}


def post_all(posts: dict, image_url: Optional[str] = None) -> dict:
    """
    全プラットフォームへ投稿し結果を返す

    Args:
        posts: generate_posts() の返り値 {platform: {"content": str, ...}}
        image_url: Instagram用の画像URL（WordPress アイキャッチ等）

    Returns:
        {platform: {"success": bool, "post_id": str, "error": str}, ...}
    """
    results = {}

    platform_funcs = {
        "x": lambda content: post_to_x(content),
        "facebook": lambda content: post_to_facebook(content),
        "instagram": lambda content: post_to_instagram(content, image_url=image_url),
    }

    for platform, func in platform_funcs.items():
        if platform not in posts:
            continue
        content = posts[platform].get("content", "")
        if not content or content.startswith("生成エラー"):
            results[platform] = {"success": False, "platform": platform, "error": "投稿文が生成されていません"}
            continue
        print(f"[Poster] {platform} に投稿中...")
        results[platform] = func(content)
        success = results[platform].get("success", False)
        print(f"[Poster] {platform}: {'成功' if success else '失敗 - ' + results[platform].get('error', '')}")

    return results
