from app.services import scoring


def test_absent_platform_scores_zero():
    assert scoring.score_platform("github", {}) == 0
    assert scoring.ats_score({}) == 0


def test_github_score_monotonic_in_readme_coverage():
    base = {"present": True, "repo_count": 6, "license_pct": 0, "described_pct": 50,
            "total_stars": 1, "has_bio": True}
    low = scoring.score_github({**base, "readme_pct": 10})
    high = scoring.score_github({**base, "readme_pct": 90})
    assert high > low


def test_resume_score_rewards_keywords_and_metrics():
    weak = scoring.score_resume({"present": True, "missing_sections": ["projects"],
                                 "role_keyword_coverage_pct": 10,
                                 "quantified_bullets_pct": 0})
    strong = scoring.score_resume({"present": True, "missing_sections": [],
                                   "role_keyword_coverage_pct": 80,
                                   "quantified_bullets_pct": 70})
    assert strong > weak
    assert 0 <= weak <= 100 and 0 <= strong <= 100


def test_overall_weighted_and_bounded():
    scores = {"github": 80, "resume": 60, "linkedin": 40}
    result = scoring.overall(scores)
    assert 40 <= result <= 80
    assert scoring.overall({}) == 0
