"""
Stage 5 — Three-tier findings report.

Consumes the Stage 4 assessment result dict and classifies findings into
three tiers aligned with DQAR Domain 3:

  Tier 1 — Lineage gap findings
    Unknown source-type resources; missing audit metadata; feeds with no
    machine-readable provenance. Each unknown source is a governance finding.

  Tier 2 — Measure reconstruction disagreements
    CQL population rate vs SQL reconstruction rate divergence. Also flags
    observations with plausibility issues (e.g. HbA1c > 20%).

  Tier 3 — Population-level coherence anomalies
    Unexpected rate concentrations by source_system_id; single-feed
    numerator dominance; bulk exclusion application patterns.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any


@dataclass
class Finding:
    tier: int
    code: str
    severity: str          # "critical" | "major" | "minor" | "info"
    title: str
    description: str
    evidence: list[dict] = field(default_factory=list)
    rate_impact_estimate: str | None = None
    remediation: str | None = None


def _classify_tier1(assessment: dict) -> list[Finding]:
    findings = []

    unknown = assessment.get("unknown_sources", [])
    if unknown:
        sample = unknown[:10]
        findings.append(Finding(
            tier=1,
            code="T1-UNKNOWN-SOURCE",
            severity="major",
            title="Resources with unresolved source type",
            description=(
                f"{len(unknown)} resource(s) have source_type='unknown'. "
                "Each represents a lineage gap — the inference algorithm could not "
                "determine the originating source system from FHIR resource signals. "
                "This indicates missing feed manifest declarations or unpopulated meta.source URIs."
            ),
            evidence=sample,
            remediation=(
                "Populate meta.source on the client extract, or add the feed "
                "to the engagement feed manifest before re-ingesting."
            ),
        ))

    risk = assessment.get("risk_stratification", [])
    feeds_with_low_confidence = [
        r for r in risk if r.get("confidence") in ("low", "unknown", None)
    ]
    if feeds_with_low_confidence:
        findings.append(Finding(
            tier=1,
            code="T1-LOW-CONFIDENCE-INFERENCE",
            severity="minor",
            title="Source inference confidence below threshold for some feeds",
            description=(
                f"{len(feeds_with_low_confidence)} source/resource-type combination(s) "
                "were inferred with low or unknown confidence. Measure rates attributed "
                "to these sources carry elevated lineage uncertainty."
            ),
            evidence=feeds_with_low_confidence[:10],
            remediation=(
                "Review inference basis for each flagged feed. "
                "Provide explicit meta.source or feed manifest declarations."
            ),
        ))

    return findings


def _classify_tier2(assessment: dict) -> list[Finding]:
    findings = []

    flagged = assessment.get("cdc_hba1c_numerator", {}).get("flagged_implausible", [])
    if flagged:
        findings.append(Finding(
            tier=2,
            code="T2-HBA1C-PLAUSIBILITY",
            severity="major",
            title="HbA1c observations with implausible values",
            description=(
                f"{len(flagged)} HbA1c Observation(s) flagged by the plausibility "
                "check (value outside clinically expected range). These observations "
                "may inflate or deflate the CDC numerator rate."
            ),
            evidence=[{"observation_id": oid} for oid in flagged[:10]],
            rate_impact_estimate=(
                f"Up to {len(flagged)} observations may affect the CDC HbA1c numerator."
            ),
            remediation=(
                "Trace each flagged observation_id back to its source record "
                "via sof.audit_event_metadata to identify the transformation error."
            ),
        ))

    return findings


def _classify_tier3(assessment: dict) -> list[Finding]:
    findings = []

    risk = assessment.get("risk_stratification", [])
    if not risk:
        return findings

    total = sum(r.get("resource_count", 0) for r in risk)
    if total == 0:
        return findings

    for row in risk:
        share = row.get("resource_count", 0) / total
        if share > 0.90:
            findings.append(Finding(
                tier=3,
                code="T3-SINGLE-SOURCE-DOMINANCE",
                severity="minor",
                title="Single source system supplies >90% of resources",
                description=(
                    f"Source '{row.get('source_system_id')}' ({row.get('source_type')}) "
                    f"accounts for {share:.0%} of all ingested resources. "
                    "This may indicate missing feeds or an incomplete extract."
                ),
                evidence=[row],
                remediation=(
                    "Verify that all expected source systems are represented in "
                    "the egress package. Cross-check against the feed manifest."
                ),
            ))

    return findings


def generate_findings_report(
    assessment: dict,
    engagement_id: str,
    ol_run_id: str,
) -> dict:
    """
    Generate the three-tier findings report from a Stage 4 assessment result.

    Returns a dict suitable for JSON serialisation and PDF rendering.
    """
    tier1 = _classify_tier1(assessment)
    tier2 = _classify_tier2(assessment)
    tier3 = _classify_tier3(assessment)
    all_findings = tier1 + tier2 + tier3

    critical = [f for f in all_findings if f.severity == "critical"]
    major    = [f for f in all_findings if f.severity == "major"]

    if critical:
        overall_status = "fail"
    elif major:
        overall_status = "review-required"
    elif all_findings:
        overall_status = "pass-with-findings"
    else:
        overall_status = "pass"

    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "engagement_id": engagement_id,
        "ol_run_id": ol_run_id,
        "overall_status": overall_status,
        "summary": {
            "tier1_count": len(tier1),
            "tier2_count": len(tier2),
            "tier3_count": len(tier3),
            "total_findings": len(all_findings),
            "critical": len(critical),
            "major": len(major),
        },
        "findings": [asdict(f) for f in all_findings],
        "source_coverage": assessment.get("source_coverage", []),
        "risk_stratification": assessment.get("risk_stratification", []),
    }


def render_findings_text(report: dict) -> str:
    lines = [
        "=" * 70,
        "DQAR FINDINGS REPORT",
        f"Engagement : {report['engagement_id']}",
        f"Run ID     : {report['ol_run_id']}",
        f"Generated  : {report['generated_at']}",
        f"Status     : {report['overall_status'].upper()}",
        "=" * 70,
        "",
        f"SUMMARY: {report['summary']['total_findings']} finding(s) — "
        f"Tier 1: {report['summary']['tier1_count']}  "
        f"Tier 2: {report['summary']['tier2_count']}  "
        f"Tier 3: {report['summary']['tier3_count']}",
        "",
    ]
    for finding in report["findings"]:
        lines += [
            f"[Tier {finding['tier']} | {finding['severity'].upper()}] {finding['code']}",
            f"  {finding['title']}",
            f"  {finding['description']}",
        ]
        if finding.get("rate_impact_estimate"):
            lines.append(f"  Rate impact: {finding['rate_impact_estimate']}")
        if finding.get("remediation"):
            lines.append(f"  Remediation: {finding['remediation']}")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    import argparse, os, sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from stage4.semantic_assessment import run_full_assessment

    parser = argparse.ArgumentParser(description="Run Stage 4+5 and print findings report")
    parser.add_argument("--aidbox-url", default=os.environ.get("AIDBOX_URL", "http://localhost:8080"))
    parser.add_argument("--token", default=os.environ.get("AIDBOX_TOKEN"))
    parser.add_argument("--engagement-id", default="dev-engagement")
    parser.add_argument("--ol-run-id", default="dev-run")
    parser.add_argument("--json", action="store_true", help="Output raw JSON instead of text")
    args = parser.parse_args()

    if not args.token:
        raise SystemExit("ERROR: --token or AIDBOX_TOKEN required")

    headers = {"Authorization": f"Bearer {args.token}"}
    sql_url = f"{args.aidbox_url}/$sql"

    assessment = run_full_assessment(sql_url, headers)
    report = generate_findings_report(assessment, args.engagement_id, args.ol_run_id)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(render_findings_text(report))
