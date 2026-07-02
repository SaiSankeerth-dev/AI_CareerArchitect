"""Deterministic 0-100 scoring rubrics. No LLM, no cost, reproducible."""


def _clamp(value: float) -> int:
    return max(0, min(100, round(value)))


def score_github(analysis: dict) -> int:
    if not analysis.get("present"):
        return 0
    completeness = 40 * min(1.0, analysis.get("repo_count", 0) / 6)
    quality = (
        0.15 * analysis.get("readme_pct", 0)
        + 0.075 * analysis.get("license_pct", 0)
        + 0.075 * analysis.get("described_pct", 0)
    )  # max 30
    activity = 15 if analysis.get("total_stars", 0) > 0 else 8
    identity = 15 if analysis.get("has_bio") else 5
    return _clamp(completeness + quality + activity + identity)


def score_linkedin(analysis: dict) -> int:
    if not analysis.get("present"):
        return 0
    coverage = 0.5 * analysis.get("role_keyword_coverage_pct", 0)  # max 50
    depth = 30 * min(1.0, analysis.get("text_length", 0) / 3000)
    titled = 20 if analysis.get("title") else 0
    return _clamp(coverage + depth + titled)


def score_resume(analysis: dict) -> int:
    if not analysis.get("present"):
        return 0
    sections = 30 * (1 - len(analysis.get("missing_sections", [])) / 4)
    coverage = 0.4 * analysis.get("role_keyword_coverage_pct", 0)  # max 40
    metrics = 0.3 * analysis.get("quantified_bullets_pct", 0)  # max 30
    return _clamp(sections + coverage + metrics)


def score_portfolio(analysis: dict) -> int:
    if not analysis.get("present"):
        return 0
    score = 40
    score += 20 if analysis.get("has_meta_description") else 0
    score += 20 if analysis.get("has_og_tags") else 0
    score += 20 if analysis.get("mentions_contact") else 0
    return _clamp(score)


def score_coding(analysis: dict) -> int:
    if not analysis.get("present"):
        return 0
    return _clamp(40 + 15 * len(analysis.get("profiles", {})))


def score_brand(analysis: dict) -> int:
    if not analysis:
        return 0
    base = 20 * min(4, analysis.get("platform_count", 0))
    consistent = 20 if analysis.get("name_consistent") else 0
    return _clamp(base + consistent)


SCORERS = {
    "github": score_github,
    "linkedin": score_linkedin,
    "resume": score_resume,
    "portfolio": score_portfolio,
    "coding": score_coding,
    "brand": score_brand,
}


def score_platform(platform: str, analysis: dict) -> int:
    scorer = SCORERS.get(platform)
    return scorer(analysis) if scorer else 0


def ats_score(resume_analysis: dict) -> int:
    if not resume_analysis.get("present"):
        return 0
    coverage = 0.6 * resume_analysis.get("role_keyword_coverage_pct", 0)
    sections = 25 * (1 - len(resume_analysis.get("missing_sections", [])) / 4)
    structure = 15 if resume_analysis.get("bullet_count", 0) >= 5 else 5
    return _clamp(coverage + sections + structure)


def overall(platform_scores: dict[str, int]) -> int:
    weights = {"github": 0.25, "linkedin": 0.2, "resume": 0.25,
               "portfolio": 0.1, "coding": 0.1, "brand": 0.1}
    present = {k: v for k, v in platform_scores.items() if k in weights}
    if not present:
        return 0
    total_weight = sum(weights[k] for k in present)
    return _clamp(sum(v * weights[k] for k, v in present.items()) / total_weight)
