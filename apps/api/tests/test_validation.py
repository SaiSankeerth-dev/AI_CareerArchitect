import pytest

from app.services.validation import check_grounding


EVIDENCE = [
    "GitHub profile: Jane Doe. Repo weather-app: A React weather dashboard "
    "[JavaScript] stars=12 topics=react,weather. Repo ml-pipeline: Training "
    "pipeline for image classification [Python] stars=3.",
    "Resume skills: Python, JavaScript, React, Docker. Experience: built a "
    "weather dashboard used by 200 students.",
]


def test_grounded_suggestion_passes():
    verdict = check_grounding(
        "Add a README to 'weather-app' describing the React weather dashboard.",
        EVIDENCE,
    )
    assert verdict.ok


def test_fabricated_metric_rejected():
    verdict = check_grounding(
        "Mention that your weather app serves 50,000 daily users.", EVIDENCE
    )
    assert not verdict.ok
    assert "50,000" in verdict.reason


def test_fabricated_employer_rejected():
    verdict = check_grounding(
        "Highlight your internship at Google on your profile.", EVIDENCE
    )
    assert not verdict.ok
    assert "Google" in verdict.reason


def test_real_metric_from_evidence_passes():
    verdict = check_grounding(
        "Add the true metric: weather dashboard used by 200 students.", EVIDENCE
    )
    assert verdict.ok


def test_generic_advice_passes_without_entities():
    verdict = check_grounding(
        "Add a meta description tag summarizing who you are.", EVIDENCE
    )
    assert verdict.ok


@pytest.mark.asyncio
async def test_validate_suggestion_requires_evidence_ids():
    from app.services.validation import validate_suggestion

    draft = {"suggested": "Add a README.", "reason": "", "evidence_ids": []}
    verdict = await validate_suggestion(draft, EVIDENCE)
    assert not verdict.ok
    assert "evidence" in verdict.reason.lower()
