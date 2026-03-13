"""
SNS投稿エンジン - Cloud Run メインサーバー
"""

import os
import uuid
from flask import Flask, request, jsonify
from content_generator import generate_from_wordpress, generate_from_material, generate_image_prompt
from image_generator import generate_image, use_wordpress_image
from poster import post_to_twitter, post_to_instagram, post_to_facebook, post_to_tiktok
from storage import save_post_result, save_error


app = Flask(__name__)


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"}), 200


@app.route("/post", methods=["POST"])
def post():
    """SNS投稿を実行するエンドポイント"""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request"}), 400

    platform = data.get("platform")
    source = data.get("source")  # "wordpress" or "scheduled" or "material"
    payload = data.get("payload", {})

    if not platform or not source:
        return jsonify({"error": "platform and source are required"}), 400

    try:
        # コンテンツ生成
        if source == "wordpress":
            content = generate_from_wordpress(
                post_title=payload.get("post_title", ""),
                post_content=payload.get("post_content", ""),
                post_url=payload.get("post_url", ""),
                platform=platform,
            )
            # WordPress記事の画像をそのまま使用
            image_url = use_wordpress_image(payload.get("post_image_url", ""))

        elif source == "material":
            content = generate_from_material(
                material_text=payload.get("material_text", ""),
                platform=platform,
                topic=payload.get("topic", ""),
            )
            # AI画像生成
            img_prompt = generate_image_prompt(payload.get("topic", content[:50]), platform)
            image_url = generate_image(img_prompt, f"{platform}_{uuid.uuid4().hex[:8]}.png")

        else:
            content = payload.get("content", "")
            image_url = payload.get("image_url", "")

        # プラットフォームに投稿
        result = _post_to_platform(platform, content, image_url, payload)

        # 結果を保存
        save_post_result(platform, result.get("post_id", ""), content, image_url, result)

        return jsonify(result), 200

    except Exception as e:
        error_msg = str(e)
        save_error(platform, str(payload), error_msg)
        return jsonify({"error": error_msg}), 500


def _post_to_platform(platform: str, content: str, image_url: str, payload: dict) -> dict:
    """プラットフォームに応じた投稿処理を実行する"""
    if platform == "twitter":
        return post_to_twitter(content, image_url)
    elif platform == "instagram":
        return post_to_instagram(content, image_url)
    elif platform == "facebook":
        return post_to_facebook(content, image_url)
    elif platform == "tiktok":
        video_url = payload.get("video_url", image_url)
        return post_to_tiktok(content, video_url)
    else:
        raise ValueError(f"未対応のプラットフォーム: {platform}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
