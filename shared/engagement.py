"""
Engagement config loader and auth adapter.
Implementation lives in dqar-contracts — this module re-exports for
backward compatibility with existing imports in this repo.

Do not add new logic here. Import directly from dqar_contracts.shared
in any new code.
"""

from dqar_contracts.shared.engagement import (  # noqa: F401
    EngagementConfig,
    load_engagement,
    get_fhir_headers,
    engagement_schema_path,
)

__all__ = [
    "EngagementConfig",
    "load_engagement",
    "get_fhir_headers",
    "engagement_schema_path",
]
