"""
WordPress Webhook受信 Cloud Function
記事更新時に呼び出され、SNS投稿エンジンへ転送する
"""

import json
import os
import functions_framework
from google.cloud import firestore
from google.cloud import tasks_v2
import datetime


db = firestore.Client()
tasks_client = tasks_v2.CloudTasksClient()

GCP_PROJECT = os.environ.get("GCP_PROJECT")
GCP_LOCATION = os.environ.get("GCP_LOCATION", "asia-northeast1")
CLOUD_TASKS_QUEUE = os.environ.get("CLOUD_TASKS_QUEUE", "sns-posting-queue")
POSTING_ENGINE_URL = os.environ.get("POSTING_ENGINE_URL")
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET")


@functions_framework.http
def wordpress_webhook(request):
    """WordPressからのWebhookを受信する"""

    # シークレット検証
    secret = request.headers.get("X-Webhook-Secret")
    if secret != WEBHOOK_SECRET:
        return {"error": "Unauthorized"}, 401

    # リクエストボディを取得
    data = request.get_json(silent=True)
    if not data:
        return {"error": "Invalid request body"}, 400

    # 記事情報を取得
    post_id = data.get("post_id")
    post_title = data.get("post_title")
    post_content = data.get("post_content")
    post_url = data.get("post_url")
    post_image_url = data.get("post_image_url")
    post_status = data.get("post_status")

    # 公開済み記事のみ処理
    if post_status != "publish":
        return {"message": "Skipped: post is not published"}, 200

    # Firestoreに記事データを保存
    post_ref = db.collection("wordpress_posts").document(str(post_id))
    post_ref.set({
        "post_id": post_id,
        "post_title": post_title,
        "post_content": post_content,
        "post_url": post_url,
        "post_image_url": post_image_url,
        "created_at": firestore.SERVER_TIMESTAMP,
        "status": "pending"
    })

    # 各SNSプラットフォームへの投稿タスクを作成
    platforms = ["twitter", "instagram", "facebook", "tiktok"]
    for platform in platforms:
        _create_posting_task(post_id, platform, "wordpress", {
            "post_id": post_id,
            "post_title": post_title,
            "post_content": post_content,
            "post_url": post_url,
            "post_image_url": post_image_url,
            "source": "wordpress"
        })

    return {"message": f"Webhook received for post {post_id}"}, 200


def _create_posting_task(post_id, platform, source, payload):
    """Cloud Tasksにポスティングタスクを追加する"""
    parent = tasks_client.queue_path(GCP_PROJECT, GCP_LOCATION, CLOUD_TASKS_QUEUE)

    task_payload = {
        "platform": platform,
        "source": source,
        "payload": payload
    }

    task = {
        "http_request": {
            "http_method": tasks_v2.HttpMethod.POST,
            "url": f"{POSTING_ENGINE_URL}/post",
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(task_payload).encode(),
        }
    }

    tasks_client.create_task(parent=parent, task=task)
