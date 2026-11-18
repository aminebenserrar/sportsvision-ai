"""Serve SportsVision AI and run inference with the user's trained model."""

import io
import json
import logging
import re
import threading
import warnings
import zipfile
from contextlib import asynccontextmanager
from pathlib import Path

import numpy as np
import tensorflow as tf
from fastapi import FastAPI, File, HTTPException, UploadFile, Request
from fastapi.responses import FileResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from PIL import Image, ImageOps, UnidentifiedImageError
from starlette.concurrency import run_in_threadpool

ROOT = Path(__file__).resolve().parent.parent
MAX_BYTES = 10 * 1024 * 1024
MAX_BATCH_FILES = 20
MAX_BATCH_BYTES = 50 * 1024 * 1024
SPORTS = ("basketball", "football", "tennis")
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


class BatchBodyLimit:
    """Bound batch bodies before multipart parsing, including chunked uploads."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['path'] not in {'/api/organize', '/api/organize/zip'}:
            return await self.app(scope, receive, send)
        chunks = []
        total = 0
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            total += len(message.get('body', b''))
            # Allow 1 MiB for multipart headers, in addition to 50 MiB of files.
            if total > MAX_BATCH_BYTES + 1024 * 1024:
                return await JSONResponse({'detail': 'Batch upload exceeds the 50 MB limit.'}, 413)(scope, receive, send)
            chunks.append(message)
            if not message.get('more_body', False):
                break
        iterator = iter(chunks)

        async def replay():
            return next(iterator, {'type': 'http.request', 'body': b'', 'more_body': False})

        await self.app(scope, replay, send)


app.add_middleware(BatchBodyLimit)


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
                if source.width * source.height > Image.MAX_IMAGE_PIXELS:
                    raise HTTPException(413, "Image dimensions are too large. Use an image under 25 megapixels.")
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


def archive_name(filename: str, index: int, contents: bytes, sport: str):
    """Use safe flat filenames, a unique index, and the actual decoded extension."""
    leaf = filename.replace('\\', '/').rsplit('/', 1)[-1]
    stem = re.sub(r'[^A-Za-z0-9_-]+', '_', Path(leaf).stem).strip('_')[:80] or 'image'
    with Image.open(io.BytesIO(contents)) as image:
        extension = {'JPEG': 'jpg', 'PNG': 'png', 'WEBP': 'webp'}[image.format]
    return f'{sport}/{index + 1:03d}_{stem}.{extension}'


async def organize_uploads(request: Request, include_zip=False):
    # Form context closes all temporary multipart uploads, including failed files.
    async with request.form(max_files=MAX_BATCH_FILES, max_fields=0) as form:
        files = form.getlist('files')
        if not files or len(files) > MAX_BATCH_FILES or len(form.multi_items()) != len(files):
            raise HTTPException(400, 'Upload 1–20 images using the files field.')
        if any(not hasattr(file, 'read') for file in files):
            raise HTTPException(400, 'Each files field must be an uploaded file.')
        if sum(file.size or 0 for file in files) > MAX_BATCH_BYTES:
            raise HTTPException(413, 'The combined image size must be 50 MB or smaller.')
        counts = dict.fromkeys(SPORTS, 0)
        results = []
        buffer = io.BytesIO() if include_zip else None
        archive = zipfile.ZipFile(buffer, 'w', compression=zipfile.ZIP_STORED) if include_zip else None
        try:
            if archive:
                for sport in SPORTS:
                    archive.writestr(f'{sport}/', b'')
            for index, file in enumerate(files):
                item = {'index': index, 'filename': file.filename or 'image'}
                try:
                    if file.content_type not in {'image/jpeg', 'image/png', 'image/webp'}:
                        raise HTTPException(415, 'Please upload a JPEG, PNG, or WebP image.')
                    contents = await file.read(MAX_BYTES + 1)
                    if not contents:
                        raise HTTPException(400, 'The uploaded file is empty.')
                    if len(contents) > MAX_BYTES:
                        raise HTTPException(413, 'The image must be 10 MB or smaller.')
                    result = await run_in_threadpool(classify, contents)
                    sport = result['predicted_sport']
                    if sport not in counts:
                        raise HTTPException(500, 'The predicted category is not supported.')
                    name = archive_name(item['filename'], index, contents, sport)
                    if archive:
                        # Store the original bytes, not the 224×224 model input.
                        await run_in_threadpool(archive.writestr, name, contents)
                    counts[sport] += 1
                    item.update(status='success', archive_path=name, **result)
                except HTTPException as error:
                    item.update(status='error', error=error.detail)
                except Exception:
                    logger.exception('Batch item processing failed')
                    item.update(status='error', error='This image could not be processed.')
                results.append(item)
            succeeded = sum(counts.values())
            summary = {'results': results, 'counts': counts, 'total': len(files),
                       'succeeded': succeeded, 'failed': len(files) - succeeded}
            if archive:
                if not succeeded:
                    raise HTTPException(422, 'No valid images could be organized. Check the batch results.')
                archive.close()
                return Response(buffer.getvalue(), media_type='application/zip', headers={
                    'Content-Disposition': 'attachment; filename="sportsvision_organized.zip"',
                    'Cache-Control': 'no-store',
                    'X-Organized-Count': str(succeeded), 'X-Failed-Count': str(len(files) - succeeded),
                })
            return JSONResponse(summary, headers={'Cache-Control': 'no-store'})
        finally:
            if archive:
                archive.close()
            if buffer:
                buffer.close()


@app.post('/api/organize')
async def organize(request: Request):
    return await organize_uploads(request)


@app.post('/api/organize/zip')
async def organized_zip(request: Request):
    # Revalidate/reclassify the supplied originals: no stored uploads or client-trusted labels.
    return await organize_uploads(request, include_zip=True)
