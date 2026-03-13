"""
各SNSプラットフォームへの投稿処理
"""

import os
import tweepy
import requests
from google.cloud import secretmanager


secret_client = secretmanager.SecretManagerServiceClient()
GCP_PROJECT = os.environ.get("GCP_PROJECT")


def _get_secret(secret_name: str) -> str:
    """Secret Managerからシークレットを取得する"""
    name = f"projects/{GCP_PROJECT}/secrets/{secret_name}/versions/latest"
    response = secret_client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8")


# ===== Twitter/X =====

def post_to_twitter(text: str, image_url: str = None) -> dict:
    """Twitter/Xに投稿する"""
    api_key = _get_secret("twitter-api-key")
    api_secret = _get_secret("twitter-api-secret")
    access_token = _get_secret("twitter-access-token")
    access_token_secret = _get_secret("twitter-access-token-secret")

    client = tweepy.Client(
        consumer_key=api_key,
        consumer_secret=api_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
    )

    media_ids = None
    if image_url:
        auth = tweepy.OAuth1UserHandler(api_key, api_secret, access_token, access_token_secret)
        api = tweepy.API(auth)
        image_data = requests.get(image_url).content
        with open("/tmp/twitter_image.jpg", "wb") as f:
            f.write(image_data)
        media = api.media_upload("/tmp/twitter_image.jpg")
        media_ids = [media.media_id]

    response = client.create_tweet(text=text, media_ids=media_ids)
    return {"platform": "twitter", "post_id": response.data["id"], "status": "success"}


# ===== Instagram =====

def post_to_instagram(text: str, image_url: str) -> dict:
    """Instagramに投稿する（画像必須）"""
    access_token = _get_secret("instagram-access-token")
    instagram_account_id = _get_secret("instagram-account-id")

    # メディアオブジェクトを作成
    media_response = requests.post(
        f"https://graph.facebook.com/v18.0/{instagram_account_id}/media",
        data={
            "image_url": image_url,
            "caption": text,
            "access_token": access_token,
        }
    )
    media_response.raise_for_status()
    media_id = media_response.json()["id"]

    # メディアを公開
    publish_response = requests.post(
        f"https://graph.facebook.com/v18.0/{instagram_account_id}/media_publish",
        data={
            "creation_id": media_id,
            "access_token": access_token,
        }
    )
    publish_response.raise_for_status()

    return {"platform": "instagram", "post_id": publish_response.json()["id"], "status": "success"}


# ===== Facebook =====

def post_to_facebook(text: str, image_url: str = None) -> dict:
    """Facebookページに投稿する"""
    access_token = _get_secret("facebook-access-token")
    page_id = _get_secret("facebook-page-id")

    if image_url:
        response = requests.post(
            f"https://graph.facebook.com/v18.0/{page_id}/photos",
            data={
                "url": image_url,
                "message": text,
                "access_token": access_token,
            }
        )
    else:
        response = requests.post(
            f"https://graph.facebook.com/v18.0/{page_id}/feed",
            data={
                "message": text,
                "access_token": access_token,
            }
        )

    response.raise_for_status()
    return {"platform": "facebook", "post_id": response.json()["id"], "status": "success"}


# ===== TikTok =====

def post_to_tiktok(text: str, video_url: str) -> dict:
    """TikTokに投稿する（動画必須）"""
    access_token = _get_secret("tiktok-access-token")

    # TikTok Content Posting API
    response = requests.post(
        "https://open.tiktokapis.com/v2/post/publish/video/init/",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json={
            "post_info": {
                "title": text[:150],
                "privacy_level": "PUBLIC_TO_EVERYONE",
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "video_url": video_url,
            }
        }
    )
    response.raise_for_status()

    return {"platform": "tiktok", "post_id": response.json().get("data", {}).get("publish_id"), "status": "success"}
