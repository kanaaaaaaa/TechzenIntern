import json
import os

from django.core.exceptions import ImproperlyConfigured
from rest_framework import status
from rest_framework.exceptions import ValidationError
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

MAX_IMAGE_SIZE = 10 * 1024 * 1024  # 10 MB
ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _vision_credentials():
    """Credentials for the Vision client.

    Locally, GOOGLE_APPLICATION_CREDENTIALS points at a key file on disk and
    the client picks it up on its own (pass None). In hosted environments
    there's no persistent disk to put that file on, so the key's JSON
    contents are held in GOOGLE_APPLICATION_CREDENTIALS_JSON instead.
    """
    raw_json = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    if not raw_json:
        return None

    from google.oauth2 import service_account

    try:
        info = json.loads(raw_json)
    except json.JSONDecodeError as exc:
        raise ImproperlyConfigured(
            "GOOGLE_APPLICATION_CREDENTIALS_JSON is not valid JSON."
        ) from exc

    return service_account.Credentials.from_service_account_info(info)


class OcrView(APIView):
    """Runs Cloud Vision OCR on an uploaded photo and returns the extracted text."""

    permission_classes = [AllowAny]
    parser_classes = [MultiPartParser]

    def post(self, request):
        image = request.FILES.get("image")
        if not image:
            raise ValidationError({"image": ["An image file is required."]})

        if image.content_type not in ALLOWED_CONTENT_TYPES:
            raise ValidationError({"image": ["Only JPEG, PNG, or WebP images are supported."]})

        if image.size > MAX_IMAGE_SIZE:
            raise ValidationError({"image": ["Image must be smaller than 10MB."]})

        text = self._run_ocr(image.read())
        return Response({"text": text}, status=status.HTTP_200_OK)

    @staticmethod
    def _run_ocr(image_bytes):
        try:
            from google.cloud import vision
        except ImportError as exc:
            raise ImproperlyConfigured(
                "google-cloud-vision is not installed. Add it to requirements.txt."
            ) from exc

        client = vision.ImageAnnotatorClient(credentials=_vision_credentials())
        vision_image = vision.Image(content=image_bytes)
        response = client.document_text_detection(image=vision_image)

        if response.error.message:
            raise ValidationError({"image": [f"OCR failed: {response.error.message}"]})

        return (response.full_text_annotation.text or "").strip()
