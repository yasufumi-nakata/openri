"""Fixed tests for the expanded APA statistics, reference-linkage, and EXIF checks."""

import pytest
from openri.analyzer import analyze_manuscript
from openri.image_inspect import inspect_image
from openri.models import RunRequest, Status
from openri.references import citation_context_audit


def _by_id(report, check_id):
    return next(f for f in report.findings if f.check_id == check_id)


def test_chi_square_superscript_mismatch_detected():
    text = """
Results
The association was significant, χ²(2) = 1.00, p < .001.
"""
    report = analyze_manuscript(RunRequest(manuscript_text=text))
    finding = _by_id(report, "statistical_consistency")
    assert finding.status == Status.FAILED
    assert finding.evidence[0].data["test"] == "χ²"
    assert finding.evidence[0].data["calculated_p"] == pytest.approx(0.6065, abs=1e-3)


def test_chi_square_superscript_consistent_passes():
    text = """
Results
The association was significant, χ²(1) = 15.0, p < .001.
"""
    report = analyze_manuscript(RunRequest(manuscript_text=text))
    finding = _by_id(report, "statistical_consistency")
    assert finding.status == Status.PASSED
    assert "1件" in finding.message


def test_correlation_r_recomputation_consistent():
    text = """
Results
Scores correlated with age, r(58) = .45, p < .001.
"""
    report = analyze_manuscript(RunRequest(manuscript_text=text))
    finding = _by_id(report, "statistical_consistency")
    assert finding.status == Status.PASSED
    assert "1件" in finding.message


def test_correlation_r_significance_flip_detected():
    text = """
Results
Scores correlated with age, r(58) = .10, p < .05.
"""
    report = analyze_manuscript(RunRequest(manuscript_text=text))
    finding = _by_id(report, "statistical_consistency")
    assert finding.status == Status.FAILED
    data = finding.evidence[0].data
    assert data["test"].lower() == "r"
    assert data["threshold_flip"] is True
    assert data["calculated_p"] == pytest.approx(0.447, abs=5e-3)


def test_standalone_z_without_df_mismatch_detected():
    text = """
Results
The difference was highly significant, z = 1.00, p < .001.
"""
    report = analyze_manuscript(RunRequest(manuscript_text=text))
    finding = _by_id(report, "statistical_consistency")
    assert finding.status == Status.FAILED
    assert finding.evidence[0].data["calculated_p"] == pytest.approx(0.3173, abs=1e-3)


def test_standalone_z_consistent_passes():
    text = """
Results
The difference was significant, z = 3.29, p < .001.
"""
    report = analyze_manuscript(RunRequest(manuscript_text=text))
    finding = _by_id(report, "statistical_consistency")
    assert finding.status == Status.PASSED
    assert "1件" in finding.message


def test_standalone_z_inside_df_match_trailer_not_double_counted():
    text = """
Results
The contrast held, t(58) = 2.15, z = 1.00, p = 0.04.
"""
    report = analyze_manuscript(RunRequest(manuscript_text=text))
    finding = _by_id(report, "statistical_consistency")
    # The z shares the same reported p as the t-test, so only one pair is checked.
    assert "1件" in finding.message


def test_word_suffix_letters_are_not_test_statistics():
    text = """
Results
The effect(12) = 4.0, p = .001 pattern is prose, not an APA statistic.
"""
    report = analyze_manuscript(RunRequest(manuscript_text=text))
    finding = _by_id(report, "statistical_consistency")
    assert finding.status == Status.SKIPPED


def test_author_year_citation_without_reference_entry_is_flagged():
    text = """
Results
Previous work supports this effect (Smith, 2020) and (Tanaka, 2019).

References
Tanaka K. 2019. Related work. Journal of Testing.
"""
    audit = citation_context_audit(text)
    unresolved = audit["unresolved_author_year_citations"]
    assert len(unresolved) == 1
    assert unresolved[0]["author"] == "Smith"
    assert unresolved[0]["year"] == 2020

    report = analyze_manuscript(RunRequest(manuscript_text=text))
    finding = _by_id(report, "citation_context")
    assert finding.status == Status.WARNING


def test_author_year_citations_with_matching_references_are_resolved():
    text = """
Results
This replicates earlier findings (Tanaka, 2019) and (Garcia et al., 2021).

References
Tanaka K. 2019. Related work. Journal of Testing.
Garcia M, Lee J. 2021. Follow-up work. Journal of Replication.
"""
    audit = citation_context_audit(text)
    assert audit["unresolved_author_year_citations"] == []


def test_author_year_matching_skipped_without_reference_section():
    text = "Results\nEarlier findings agree (Smith, 2020)."
    audit = citation_context_audit(text)
    # Without a reference list this is a structural gap, not an author-year mismatch.
    assert audit["unresolved_author_year_citations"] == []


def test_image_exif_editing_software_is_flagged(tmp_path):
    Image = pytest.importorskip("PIL.Image")
    path = tmp_path / "figure.jpg"
    img = Image.new("RGB", (64, 64), "white")
    exif = Image.Exif()
    exif[305] = "Adobe Photoshop 25.0 (Macintosh)"
    img.save(path, exif=exif)

    inspection = inspect_image(path)
    assert inspection["available"] is True
    assert inspection["metadata"]["exif_software"].startswith("Adobe Photoshop")
    hits = [f for f in inspection["findings"] if f["kind"] == "editing-software-metadata"]
    assert len(hits) == 1
    assert "photoshop" in hits[0]["matched_markers"]
    assert hits[0]["severity"] == "medium"


def test_image_without_exif_software_not_flagged(tmp_path):
    Image = pytest.importorskip("PIL.Image")
    path = tmp_path / "figure.png"
    Image.new("RGB", (64, 64), "white").save(path)

    inspection = inspect_image(path)
    assert inspection["available"] is True
    assert inspection["metadata"]["exif_software"] is None
    assert all(f["kind"] != "editing-software-metadata" for f in inspection["findings"])
