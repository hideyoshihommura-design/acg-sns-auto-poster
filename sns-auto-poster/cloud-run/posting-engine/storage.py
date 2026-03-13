"""
Firestore データ管理
"""

import os
from google.cloud import firestore
import datetime


db = firestore.Client()


def save_post_result(platform: str, post_id: str, content: str, image_url: str, result: dict):
    """投稿結果をFirestoreに保存する"""
    db.collection("post_history").add({
        "platform": platform,
        "post_id": post_id,
        "content": content,
        "image_url": image_url,
        "result": result,
        "posted_at": firestore.SERVER_TIMESTAMP,
        "status": result.get("status", "unknown"),
    })


def save_error(platform: str, content: str, error: str):
    """エラー情報をFirestoreに保存する"""
    db.collection("post_errors").add({
        "platform": platform,
        "content": content,
        "error": error,
        "occurred_at": firestore.SERVER_TIMESTAMP,
    })


def get_scheduled_posts(platform: str = None):
    """スケジュール済み投稿を取得する"""
    query = db.collection("scheduled_posts").where("status", "==", "scheduled")
    if platform:
        query = query.where("platform", "==", platform)
    return [doc.to_dict() | {"id": doc.id} for doc in query.stream()]


def update_scheduled_post_status(post_id: str, status: str):
    """スケジュール投稿のステータスを更新する"""
    db.collection("scheduled_posts").document(post_id).update({
        "status": status,
        "updated_at": firestore.SERVER_TIMESTAMP,
    })


def create_scheduled_post(platform: str, content: str, image_url: str, scheduled_at: datetime.datetime):
    """スケジュール投稿を作成する"""
    doc_ref = db.collection("scheduled_posts").add({
        "platform": platform,
        "content": content,
        "image_url": image_url,
        "scheduled_at": scheduled_at,
        "status": "scheduled",
        "created_at": firestore.SERVER_TIMESTAMP,
    })
    return doc_ref[1].id


def get_post_history(platform: str = None, limit: int = 50):
    """投稿履歴を取得する"""
    query = db.collection("post_history").order_by(
        "posted_at", direction=firestore.Query.DESCENDING
    ).limit(limit)
    if platform:
        query = query.where("platform", "==", platform)
    return [doc.to_dict() | {"id": doc.id} for doc in query.stream()]
