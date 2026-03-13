"""
定期投稿トリガー Cloud Function
Cloud Schedulerから呼び出され、スケジュール済み投稿を処理する
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


@functions_framework.http
def scheduler_trigger(request):
    """Cloud Schedulerから定期的に呼び出される"""

    now = datetime.datetime.utcnow()

    # スケジュール済みの投稿を取得
    scheduled_posts = db.collection("scheduled_posts") \
        .where("status", "==", "scheduled") \
        .where("scheduled_at", "<=", now) \
        .stream()

    count = 0
    for post in scheduled_posts:
        post_data = post.to_dict()

        # 投稿タスクを作成
        task_payload = {
            "platform": post_data["platform"],
            "source": "scheduled",
            "payload": post_data["content"]
        }

        parent = tasks_client.queue_path(GCP_PROJECT, GCP_LOCATION, CLOUD_TASKS_QUEUE)
        task = {
            "http_request": {
                "http_method": tasks_v2.HttpMethod.POST,
                "url": f"{POSTING_ENGINE_URL}/post",
                "headers": {"Content-Type": "application/json"},
                "body": json.dumps(task_payload).encode(),
            }
        }
        tasks_client.create_task(parent=parent, task=task)

        # ステータスを処理中に更新
        post.reference.update({"status": "processing"})
        count += 1

    return {"message": f"{count}件の投稿タスクを作成しました"}, 200
