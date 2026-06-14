"""
Engagement config loader and auth adapter.

Supported server types:
  aidbox  — OAuth2 client_credentials (fetches Bearer token from /auth/token)
  hapi    — HTTP Basic auth or no auth
"""

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import requests


@dataclass
class EngagementConfig:
    name: str
    server_type: str          # "aidbox" | "hapi"
    base_url: str
    # Aidbox OAuth2
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    # HAPI Basic (both optional — HAPI is often open)
    basic_user: Optional[str] = None
    basic_password: Optional[str] = None


def load_engagement(config_path) -> EngagementConfig:
    with open(config_path) as f:
        data = json.load(f)

    server_type = data["server_type"]
    if server_type not in ("aidbox", "hapi"):
        raise ValueError(f"Unsupported server_type '{server_type}'. Must be 'aidbox' or 'hapi'.")

    return EngagementConfig(
        name=data["name"],
        server_type=server_type,
        base_url=data["base_url"].rstrip("/"),
        client_id=data.get("client_id"),
        client_secret=data.get("client_secret"),
        basic_user=data.get("basic_user"),
        basic_password=data.get("basic_password"),
    )


def get_fhir_headers(engagement: EngagementConfig) -> dict:
    """Return HTTP headers for FHIR requests, including auth."""
    base = {
        "Content-Type": "application/fhir+json",
        "Accept": "application/fhir+json",
    }

    if engagement.server_type == "aidbox":
        token = _fetch_aidbox_token(engagement)
        base["Authorization"] = f"Bearer {token}"

    elif engagement.server_type == "hapi":
        if engagement.basic_user and engagement.basic_password:
            import base64
            creds = base64.b64encode(
                f"{engagement.basic_user}:{engagement.basic_password}".encode()
            ).decode()
            base["Authorization"] = f"Basic {creds}"
        # else: no auth (public HAPI instance)

    return base


def _fetch_aidbox_token(engagement: EngagementConfig) -> str:
    if not engagement.client_id or not engagement.client_secret:
        raise ValueError(
            f"Engagement '{engagement.name}' has server_type 'aidbox' "
            "but is missing client_id or client_secret."
        )
    response = requests.post(
        f"{engagement.base_url}/auth/token",
        data={
            "grant_type": "client_credentials",
            "client_id": engagement.client_id,
            "client_secret": engagement.client_secret,
        },
    )
    response.raise_for_status()
    return response.json()["access_token"]
