"""
Firestoreを使った投稿済み記事の管理モジュール
"""

import os
from google.cloud import firestore


_db = None


def _get_db() -> firestore.Client:
    global _db
    if _db is None:
        _db = firestore.Client(project=os.getenv("GCP_PROJECT_ID"))
    return _db


def is_posted(article_id: str) -> bool:
    """記事が既に処理済みかどうかを確認する"""
    doc = _get_db().collection("posted_articles").document(_safe_id(article_id)).get()
    return doc.exists


def mark_as_posted(article_id: str, metadata: dict = None) -> None:
    """記事を処理済みとしてマークする"""
    from datetime import datetime, timezone
    _get_db().collection("posted_articles").document(_safe_id(article_id)).set({
        "article_id": article_id,
        "posted_at": datetime.now(timezone.utc),
        **(metadata or {}),
    })


def save_generated_posts(article_id: str, posts: dict) -> None:
    """生成した投稿文を保存する"""
    from datetime import datetime, timezone
    _get_db().collection("generated_posts").document(_safe_id(article_id)).set({
        "article_id": article_id,
        "posts": posts,
        "created_at": datetime.now(timezone.utc),
    })


def _safe_id(url: str) -> str:
    """URLをFirestoreのドキュメントIDに使える形式に変換する"""
    return url.replace("/", "_").replace(":", "").replace(".", "_")[:500]
