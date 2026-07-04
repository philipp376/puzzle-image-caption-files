import io
import os

import numpy as np
import requests
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import Response
from PIL import Image, ImageDraw, ImageFont
from pydantic import BaseModel

load_dotenv()

API_KEY = os.getenv("API_KEY")

app = FastAPI()


class ProcessImageRequest(BaseModel):
    image_url: str
    caption: str


def center_crop_to_square(image: Image.Image) -> Image.Image:
    width, height = image.size
    side = min(width, height)
    left = (width - side) // 2
    top = (height - side) // 2
    right = left + side
    bottom = top + side
    return image.crop((left, top, right, bottom))


def load_font(image_width: int) -> ImageFont.FreeTypeFont:
    # Scale font size relative to image width, try common bold system fonts,
    # fall back to Pillow's default font if none are found.
    font_size = max(20, image_width // 15)
    candidate_paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "arialbd.ttf",
    ]
    for path in candidate_paths:
        try:
            return ImageFont.truetype(path, font_size)
        except (OSError, IOError):
            continue
    return ImageFont.load_default()


def overlay_caption(image: Image.Image, caption: str) -> Image.Image:
    image = image.convert("RGB")
    draw = ImageDraw.Draw(image)
    font = load_font(image.width)

    bbox = draw.textbbox((0, 0), caption, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    margin_bottom = max(10, image.height // 20)
    x = (image.width - text_width) / 2
    y = image.height - text_height - margin_bottom

    # Simple black outline behind the white text so it stays readable
    # against light backgrounds.
    outline_range = 2
    for dx in range(-outline_range, outline_range + 1):
        for dy in range(-outline_range, outline_range + 1):
            if dx != 0 or dy != 0:
                draw.text((x + dx, y + dy), caption, font=font, fill="black")
    draw.text((x, y), caption, font=font, fill="white")

    return image


@app.post("/process-image")
def process_image(
    payload: ProcessImageRequest,
    x_api_key: str = Header(default=None, alias="X-API-Key"),
):
    if not API_KEY:
        raise HTTPException(
            status_code=500, detail="API_KEY is not configured on the server."
        )
    if x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")

    try:
        response = requests.get(payload.image_url, timeout=10)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise HTTPException(
            status_code=400, detail=f"Could not download image: {exc}"
        )

    try:
        image = Image.open(io.BytesIO(response.content))
        image.load()
    except Exception:
        raise HTTPException(
            status_code=400, detail="URL did not return a valid image."
        )

    cropped = center_crop_to_square(image)
    final_image = overlay_caption(cropped, payload.caption)

    output_buffer = io.BytesIO()
    final_image.save(output_buffer, format="PNG")
    output_buffer.seek(0)

    return Response(content=output_buffer.getvalue(), media_type="image/png")


@app.get("/health")
def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
