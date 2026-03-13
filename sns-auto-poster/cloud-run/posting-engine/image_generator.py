"""
Vertex AI Imagen3 を使った画像生成
"""

import os
import vertexai
from vertexai.preview.vision_models import ImageGenerationModel
import base64
from google.cloud import storage


GCP_PROJECT = os.environ.get("GCP_PROJECT")
GCP_LOCATION = os.environ.get("GCP_LOCATION", "asia-northeast1")
GCS_BUCKET = os.environ.get("GCS_BUCKET")

vertexai.init(project=GCP_PROJECT, location=GCP_LOCATION)
imagen = ImageGenerationModel.from_pretrained("imagen-3.0-generate-001")
storage_client = storage.Client()


def generate_image(prompt: str, filename: str) -> str:
    """
    Imagen3で画像を生成しGCSに保存する
    Returns: GCS上の公開URL
    """
    images = imagen.generate_images(
        prompt=prompt,
        number_of_images=1,
        aspect_ratio="1:1",
        safety_filter_level="block_some",
    )

    image_data = images[0]._image_bytes

    # GCSにアップロード
    bucket = storage_client.bucket(GCS_BUCKET)
    blob = bucket.blob(f"generated-images/{filename}")
    blob.upload_from_string(image_data, content_type="image/png")
    blob.make_public()

    return blob.public_url


def use_wordpress_image(image_url: str) -> str:
    """
    WordPressの画像URLをそのまま返す
    """
    return image_url
