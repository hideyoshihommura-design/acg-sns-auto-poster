"""
SNS自動投稿 管理画面 - Web UI
"""

import os
import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for
from google.cloud import firestore


app = Flask(__name__)
db = firestore.Client()
POSTING_ENGINE_URL = os.environ.get("POSTING_ENGINE_URL", "http://posting-engine:8080")


# ===== ダッシュボード =====

@app.route("/")
def dashboard():
    """ダッシュボード"""
    # 最近の投稿履歴（10件）
    recent_posts = list(
        db.collection("post_history")
        .order_by("posted_at", direction=firestore.Query.DESCENDING)
        .limit(10)
        .stream()
    )
    recent_posts = [doc.to_dict() | {"id": doc.id} for doc in recent_posts]

    # エラー数（直近24時間）
    since = datetime.datetime.utcnow() - datetime.timedelta(hours=24)
    errors = list(
        db.collection("post_errors")
        .where("occurred_at", ">=", since)
        .stream()
    )

    # スケジュール済み投稿数
    scheduled = list(
        db.collection("scheduled_posts")
        .where("status", "==", "scheduled")
        .stream()
    )

    return render_template("dashboard.html",
        recent_posts=recent_posts,
        error_count=len(errors),
        scheduled_count=len(scheduled),
    )


# ===== スケジュール管理 =====

@app.route("/schedule")
def schedule():
    """スケジュール管理ページ"""
    scheduled_posts = list(
        db.collection("scheduled_posts")
        .where("status", "==", "scheduled")
        .order_by("scheduled_at")
        .stream()
    )
    scheduled_posts = [doc.to_dict() | {"id": doc.id} for doc in scheduled_posts]
    return render_template("schedule.html", scheduled_posts=scheduled_posts)


@app.route("/schedule/create", methods=["POST"])
def create_schedule():
    """スケジュール投稿を作成する"""
    platform = request.form.get("platform")
    content = request.form.get("content")
    image_url = request.form.get("image_url", "")
    scheduled_at_str = request.form.get("scheduled_at")

    scheduled_at = datetime.datetime.fromisoformat(scheduled_at_str)

    db.collection("scheduled_posts").add({
        "platform": platform,
        "content": content,
        "image_url": image_url,
        "scheduled_at": scheduled_at,
        "status": "scheduled",
        "created_at": firestore.SERVER_TIMESTAMP,
    })

    return redirect(url_for("schedule"))


@app.route("/schedule/<post_id>/delete", methods=["POST"])
def delete_schedule(post_id):
    """スケジュール投稿を削除する"""
    db.collection("scheduled_posts").document(post_id).delete()
    return redirect(url_for("schedule"))


# ===== 投稿履歴 =====

@app.route("/history")
def history():
    """投稿履歴ページ"""
    platform_filter = request.args.get("platform", "")
    query = db.collection("post_history").order_by(
        "posted_at", direction=firestore.Query.DESCENDING
    ).limit(50)

    posts = [doc.to_dict() | {"id": doc.id} for doc in query.stream()]

    if platform_filter:
        posts = [p for p in posts if p.get("platform") == platform_filter]

    return render_template("history.html", posts=posts, platform_filter=platform_filter)


# ===== 素材アップロード・AI生成 =====

@app.route("/generate")
def generate():
    """AI生成ページ"""
    return render_template("generate.html")


@app.route("/generate/preview", methods=["POST"])
def generate_preview():
    """AI生成コンテンツのプレビュー"""
    import requests as req

    platform = request.form.get("platform")
    material_text = request.form.get("material_text")
    topic = request.form.get("topic", "")

    response = req.post(f"{POSTING_ENGINE_URL}/post", json={
        "platform": platform,
        "source": "material",
        "payload": {
            "material_text": material_text,
            "topic": topic,
        }
    })

    return jsonify(response.json())


# ===== システム管理 =====

@app.route("/system")
def system():
    """システム管理ページ"""
    return render_template("system.html",
        posting_engine_url=POSTING_ENGINE_URL,
    )


# ===== エラーログ =====

@app.route("/errors")
def errors():
    """エラーログページ"""
    error_logs = list(
        db.collection("post_errors")
        .order_by("occurred_at", direction=firestore.Query.DESCENDING)
        .limit(50)
        .stream()
    )
    error_logs = [doc.to_dict() | {"id": doc.id} for doc in error_logs]
    return render_template("errors.html", error_logs=error_logs)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8081))
    app.run(host="0.0.0.0", port=port, debug=False)
