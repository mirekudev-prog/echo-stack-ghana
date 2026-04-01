"""
storage.py — Supabase Storage upload helper for EchoStack
Drop-in replacement for local disk uploads.

Requires env vars:
  SUPABASE_URL         = https://trzisijyeetygylpsidl.supabase.co
  SUPABASE_SERVICE_KEY = your service_role key
  SUPABASE_BUCKET      = echostack-uploads  (or set this env var)
"""

import os
import mimetypes
import datetime
import httpx

SUPABASE_URL    = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY    = os.environ.get("SUPABASE_SERVICE_KEY", "")
BUCKET          = os.environ.get("SUPABASE_BUCKET", "echostack-uploads")


def _headers():
    return {
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "apikey": SUPABASE_KEY,
    }


async def upload_to_supabase(file_bytes: bytes, filename: str, content_type: str = "") -> str:
    """
    Upload bytes to Supabase Storage.
    Returns the public URL of the uploaded file.
    Raises Exception on failure.
    """
    if not SUPABASE_URL or not SUPABASE_KEY:
        raise Exception("SUPABASE_URL and SUPABASE_SERVICE_KEY env vars are required")

    # Build a timestamped unique path
    ts = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    ext = os.path.splitext(filename)[1] or mimetypes.guess_extension(content_type or "") or ".bin"
    safe_name = f"{ts}_{filename}"
    path = safe_name.replace(" ", "_")

    upload_url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{path}"

    headers = _headers()
    headers["Content-Type"] = content_type or "application/octet-stream"
    headers["x-upsert"] = "true"   # overwrite if same name

    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(upload_url, content=file_bytes, headers=headers)
        if resp.status_code not in (200, 201):
            raise Exception(f"Supabase upload failed: {resp.status_code} {resp.text[:200]}")

    # Return public URL
    public_url = f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{path}"
    return public_url


async def delete_from_supabase(public_url: str) -> bool:
    """Delete a file from Supabase Storage given its public URL."""
    if not public_url or BUCKET not in public_url:
        return False
    try:
        # Extract path after /public/{bucket}/
        path = public_url.split(f"/public/{BUCKET}/", 1)[-1]
        delete_url = f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{path}"
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.delete(delete_url, headers=_headers())
        return resp.status_code in (200, 204)
    except Exception:
        return False
