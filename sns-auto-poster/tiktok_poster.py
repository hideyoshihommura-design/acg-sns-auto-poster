"""
TikTok用スライド動画生成・投稿モジュール
"""

import os
import re
import textwrap
import requests
import tempfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import moviepy.editor as mp
import numpy as np


# スライド設定
SLIDE_SIZE = (1080, 1920)  # TikTok縦型
SLIDE_DURATION = 3         # 各スライド表示秒数
BG_COLOR = (30, 144, 200)  # ACGブランドカラー（青系）
TEXT_COLOR = (255, 255, 255)
FONT_SIZE = 72


def parse_slides(tiktok_content: str) -> list[str]:
    """generator.pyが生成したスライドテキストをパースする"""
    slides = []
    for line in tiktok_content.split("\n"):
        match = re.match(r"SLIDE\d+:\s*(.+)", line.strip())
        if match:
            slides.append(match.group(1).strip())
    return slides if slides else [tiktok_content[:30]]


def _create_slide_image(text: str, bg_image_url: str = None) -> np.ndarray:
    """1枚のスライド画像を生成する"""
    img = Image.new("RGB", SLIDE_SIZE, BG_COLOR)

    # 背景画像がある場合は使用（暗くして文字を見やすく）
    if bg_image_url:
        try:
            res = requests.get(bg_image_url, timeout=5)
            bg = Image.open(res.raw).convert("RGB")
            bg = bg.resize(SLIDE_SIZE)
            overlay = Image.new("RGBA", SLIDE_SIZE, (0, 0, 0, 140))
            img = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
        except Exception:
            pass

    draw = ImageDraw.Draw(img)

    # フォント（システムフォントにフォールバック）
    try:
        font = ImageFont.truetype("/usr/share/fonts/truetype/noto/NotoSansCJK-Bold.ttc", FONT_SIZE)
    except Exception:
        font = ImageFont.load_default()

    # テキストを折り返して中央に配置
    lines = textwrap.wrap(text, width=10)
    total_height = len(lines) * (FONT_SIZE + 16)
    y = (SLIDE_SIZE[1] - total_height) // 2

    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        w = bbox[2] - bbox[0]
        x = (SLIDE_SIZE[0] - w) // 2
        draw.text((x, y), line, font=font, fill=TEXT_COLOR)
        y += FONT_SIZE + 16

    return np.array(img)


def create_slide_video(slides: list[str], image_url: str = None) -> str:
    """スライド動画を生成してファイルパスを返す"""
    clips = []
    for text in slides:
        frame = _create_slide_image(text, image_url)
        clip = mp.ImageClip(frame, duration=SLIDE_DURATION)
        clips.append(clip)

    video = mp.concatenate_videoclips(clips, method="compose")

    output_path = tempfile.mktemp(suffix=".mp4")
    video.write_videofile(
        output_path,
        fps=24,
        codec="libx264",
        audio=False,
        logger=None,
    )
    return output_path


def upload_to_tiktok(video_path: str, caption: str) -> dict:
    """TikTok Content Posting APIで動画をアップロードする"""
    access_token = os.getenv("TIKTOK_ACCESS_TOKEN")

    # Step 1: アップロード初期化
    init_res = requests.post(
        "https://open.tiktokapis.com/v2/post/publish/video/init/",
        headers={
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        },
        json={
            "post_info": {
                "title": caption[:150],
                "privacy_level": "PUBLIC_TO_EVERYONE",
                "disable_duet": False,
                "disable_comment": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "FILE_UPLOAD",
                "video_size": Path(video_path).stat().st_size,
                "chunk_size": Path(video_path).stat().st_size,
                "total_chunk_count": 1,
            },
        },
        timeout=30,
    )
    init_res.raise_for_status()
    init_data = init_res.json()["data"]
    upload_url = init_data["upload_url"]
    publish_id = init_data["publish_id"]

    # Step 2: 動画ファイルをアップロード
    file_size = Path(video_path).stat().st_size
    with open(video_path, "rb") as f:
        upload_res = requests.put(
            upload_url,
            headers={
                "Content-Range": f"bytes 0-{file_size - 1}/{file_size}",
                "Content-Type": "video/mp4",
            },
            data=f,
            timeout=120,
        )
    upload_res.raise_for_status()

    return {"status": "ok", "publish_id": publish_id}


def post_to_tiktok(article_title: str, tiktok_content: str, image_url: str = None) -> dict:
    """TikTok投稿のメイン処理"""
    try:
        slides = parse_slides(tiktok_content)
        video_path = create_slide_video(slides, image_url)
        result = upload_to_tiktok(video_path, article_title)
        Path(video_path).unlink(missing_ok=True)
        return result
    except Exception as e:
        print(f"[tiktok] 投稿エラー: {e}")
        return {"status": "error", "error": str(e)}
