"""
DQAR Upload Portal — FastAPI application.

Run:
    uvicorn web.app:app --reload --port 8000

Engagement configs are loaded from config/engagements/{engagement_id}.json.
AWS credentials for S3 presigning use the standard boto3 credential chain.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from starlette.requests import Request

from web.presign import check_upload_exists, generate_presigned_put

app = FastAPI(title="DQAR Upload Portal", docs_url=None, redoc_url=None)

_ROOT = Path(__file__).parent.parent
_ENGAGEMENTS_DIR = _ROOT / "config" / "engagements"
_templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))


def _load_engagement(engagement_id: str) -> dict:
    path = _ENGAGEMENTS_DIR / f"{engagement_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Engagement '{engagement_id}' not found.")
    with open(path) as f:
        cfg = json.load(f)
    for field in ("s3_bucket", "s3_prefix", "s3_region"):
        if not cfg.get(field):
            raise HTTPException(
                status_code=500,
                detail=f"Engagement '{engagement_id}' is missing S3 field '{field}'.",
            )
    return cfg


@app.get("/upload/{engagement_id}", response_class=HTMLResponse)
async def upload_page(request: Request, engagement_id: str):
    cfg = _load_engagement(engagement_id)
    expiry = cfg.get("s3_upload_expiry", 172800)

    presigned_url = generate_presigned_put(
        bucket=cfg["s3_bucket"],
        prefix=cfg["s3_prefix"],
        region=cfg.get("s3_region", "us-east-1"),
        expiry=expiry,
    )

    already_uploaded = check_upload_exists(
        bucket=cfg["s3_bucket"],
        prefix=cfg["s3_prefix"],
        region=cfg.get("s3_region", "us-east-1"),
    )

    return _templates.TemplateResponse(
        "upload.html",
        {
            "request": request,
            "engagement_id": engagement_id,
            "display_name": cfg.get("display_name") or cfg["name"],
            "presigned_url": presigned_url,
            "expiry_seconds": expiry,
            "already_uploaded": already_uploaded,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    )


@app.get("/api/presign/{engagement_id}")
async def refresh_presign(engagement_id: str):
    """Return a fresh presigned URL. Called by the UI when the page-load URL is stale."""
    cfg = _load_engagement(engagement_id)
    expiry = cfg.get("s3_upload_expiry", 172800)
    url = generate_presigned_put(
        bucket=cfg["s3_bucket"],
        prefix=cfg["s3_prefix"],
        region=cfg.get("s3_region", "us-east-1"),
        expiry=expiry,
    )
    return JSONResponse({"presigned_url": url, "expiry_seconds": expiry})


@app.get("/api/status/{engagement_id}")
async def upload_status(engagement_id: str):
    """Check whether extract.tar.gz has landed in S3 for this engagement."""
    cfg = _load_engagement(engagement_id)
    exists = check_upload_exists(
        bucket=cfg["s3_bucket"],
        prefix=cfg["s3_prefix"],
        region=cfg.get("s3_region", "us-east-1"),
    )
    return JSONResponse({"uploaded": exists})
