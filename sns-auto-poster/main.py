"""
Cloud Run エントリーポイント
Cloud Scheduler から30分ごとに呼び出される
"""

import os
from flask import Flask, jsonify
from scraper import fetch_latest_articles
from generator import generate_posts
from hubspot_poster import create_all_drafts
from tiktok_poster import post_to_tiktok
from storage import is_posted, mark_as_posted, save_generated_posts

app = Flask(__name__)


@app.route("/run", methods=["POST", "GET"])
def run():
    """新着記事をチェックしてSNS投稿を処理する"""
    print("[main] 記事チェック開始")
    results = []

    try:
        articles = fetch_latest_articles(limit=5)
        print(f"[main] {len(articles)} 件の記事を取得")

        for article in articles:
            if is_posted(article.id):
                print(f"[main] スキップ（処理済み）: {article.title}")
                continue

            print(f"[main] 処理開始: {article.title}")

            # 投稿文生成
            generated = generate_posts(article)
            save_generated_posts(article.id, generated)

            # HubSpot に下書き作成（X・Instagram・Facebook）
            hubspot_result = create_all_drafts(article, generated)

            # TikTok 投稿
            tiktok_result = {}
            if "tiktok" in generated:
                tiktok_result = post_to_tiktok(
                    article.title,
                    generated["tiktok"]["content"],
                    article.image_url,
                )

            # 処理済みとしてマーク
            mark_as_posted(article.id, {
                "title": article.title,
                "url": article.url,
                "hubspot": hubspot_result,
                "tiktok": tiktok_result,
            })

            results.append({
                "title": article.title,
                "url": article.url,
                "hubspot": hubspot_result,
                "tiktok": tiktok_result,
            })
            print(f"[main] 処理完了: {article.title}")

    except Exception as e:
        print(f"[main] エラー: {e}")
        return jsonify({"status": "error", "error": str(e)}), 500

    return jsonify({
        "status": "ok",
        "processed": len(results),
        "results": results,
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
