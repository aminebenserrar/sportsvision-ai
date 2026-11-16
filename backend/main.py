"""Serve SportsVision AI and run inference with the user's trained model."""

import io
import json
import logging
import threading
import warnings
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
import tensorflow as tf
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

ROOT = Path(__file__).resolve().parent.parent
MAX_BYTES = 10 * 1024 * 1024
Image.MAX_IMAGE_PIXELS = 25_000_000
logger = logging.getLogger(__name__)
inference_lock = threading.Lock()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Load once per process. Do not compile, retrain, or download another model.
    labels = json.loads((ROOT / "models" / "labels.json").read_text(encoding="utf-8-sig"))
    if (not isinstance(labels, list) or len(labels) != 3
            or any(not isinstance(label, str) or not label.strip() for label in labels)
            or len(set(labels)) != len(labels)):
        raise RuntimeError("models/labels.json must contain three unique class names in model order.")
    model = tf.keras.models.load_model(ROOT / "models" / "sports_model.keras", compile=False)
    if model.input_shape != (None, 224, 224, 3) or model.output_shape != (None, len(labels)):
        raise RuntimeError("The model must accept 224×224 RGB input and output one probability per label.")
    app.state.model = model
    app.state.labels = labels
    yield
    del app.state.model


app = FastAPI(title="SportsVision AI", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=ROOT / "frontend"), name="static")


@app.get("/", include_in_schema=False)
def homepage():
    return FileResponse(ROOT / "frontend" / "index.html")


@app.get("/api/health")
def health():
    return {"status": "ready", "classes": app.state.labels}


def classify(contents: bytes):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(contents)) as source:
                if source.format not in {"JPEG", "PNG", "WEBP"}:
                    raise HTTPException(415, "Please upload a JPEG, PNG, or WebP image.")
                if getattr(source, "n_frames", 1) != 1:
                    raise HTTPException(415, "Please upload a still image, not an animated image.")
                source.load()
                rgb = ImageOps.exif_transpose(source).convert("RGB")
                resized = rgb.resize((224, 224), Image.Resampling.BILINEAR)
                # The saved model rescales internally. Keep these pixels at 0–255.
                batch = np.expand_dims(np.asarray(resized, dtype=np.float32), axis=0)
    except (Image.DecompressionBombError, Image.DecompressionBombWarning) as exc:
        raise HTTPException(413, "Image dimensions are too large. Use an image under 25 megapixels.") from exc
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise HTTPException(400, "This image could not be decoded. Try another image.") from exc

    try:
        # Serialize model calls; blocking decoding and inference run off the event loop.
        with inference_lock:
            probabilities = np.asarray(app.state.model(batch, training=False))[0]
        if (probabilities.shape != (len(app.state.labels),)
                or not np.all(np.isfinite(probabilities))
                or np.any(probabilities < 0) or np.any(probabilities > 1)
                or not np.isclose(probabilities.sum(), 1.0, atol=1e-3)):
            raise ValueError("Model returned invalid softmax probabilities.")
        winner = int(np.argmax(probabilities))
        return {
            "predicted_sport": app.state.labels[winner],
            "confidence": float(probabilities[winner]),
            "probabilities": [
                {"sport": label, "probability": float(probabilities[index])}
                for index, label in enumerate(app.state.labels)
            ],
        }
    except Exception as exc:
        logger.exception("Model inference failed")
        raise HTTPException(500, "Analysis failed. Please try again.") from exc


@app.post("/api/predict")
async def predict(file: UploadFile = File(...)):
    try:
        if file.content_type not in {"image/jpeg", "image/png", "image/webp"}:
            raise HTTPException(415, "Please upload a JPEG, PNG, or WebP image.")
        contents = await file.read(MAX_BYTES + 1)
        if len(contents) > MAX_BYTES:
            raise HTTPException(413, "The image must be 10 MB or smaller.")
        if not contents:
            raise HTTPException(400, "The uploaded file is empty.")
        return await run_in_threadpool(classify, contents)
    finally:
        await file.close()
