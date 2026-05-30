# OpenRI peer-review corpus benchmark

This is an external-corpus smoke benchmark, not misconduct ground truth. Reviewer-text overlap is a heuristic proxy for whether OpenRI's review packet surfaces similar review dimensions.

## reviewbench

- Dataset: `Samarth0710/reviewbench` / split `iclr`
- Input mode: fulltext-markdown
- Cases: 10 of 22532
- Fetch cache: enabled
- Mean score: 54.6 (min 51, max 57)
- Mean coverage blockers: 4.0
- Mean claim count: 7.9
- Review concern overlap proxy: 0.738
- Routes: {"technical_check_then_peer_review": 10}
- Readiness: {"ai_review_with_coverage_blockers": 10}
- Active findings: {"citation_context": 10, "citation_integrity": 6, "claim_evidence_alignment": 10, "effect_size_ci_coverage": 1, "image_integrity": 10, "reporting_transparency": 10}

| Row | Score | Route | Decision | Active findings | Review concerns | Overlap |
| ---: | ---: | --- | --- | --- | --- | ---: |
| 0 | 57 | technical_check_then_peer_review | Reject | reporting_transparency, citation_context, claim_evidence_alignment, image_integrity | citation_or_related_work, claim_evidence_or_overclaim, clarity_or_presentation, method_or_experiment, reproducibility_or_code, statistics_or_results | 0.667 |
| 1 | 53 | technical_check_then_peer_review | Reject | reporting_transparency, citation_integrity, citation_context, claim_evidence_alignment, image_integrity | claim_evidence_or_overclaim, clarity_or_presentation, method_or_experiment, reproducibility_or_code | 0.75 |
| 2 | 57 | technical_check_then_peer_review | Reject | reporting_transparency, citation_context, claim_evidence_alignment, image_integrity | citation_or_related_work, claim_evidence_or_overclaim, clarity_or_presentation, method_or_experiment, reproducibility_or_code, statistics_or_results | 0.667 |
| 3 | 53 | technical_check_then_peer_review | Accept (Poster) | reporting_transparency, citation_integrity, citation_context, claim_evidence_alignment, image_integrity | citation_or_related_work, claim_evidence_or_overclaim, clarity_or_presentation, method_or_experiment, statistics_or_results | 0.6 |
| 4 | 53 | technical_check_then_peer_review | Accept (Poster) | reporting_transparency, citation_integrity, citation_context, claim_evidence_alignment, image_integrity | citation_or_related_work, clarity_or_presentation, method_or_experiment, reproducibility_or_code | 0.75 |
| 5 | 55 | technical_check_then_peer_review | Accept (Poster) | reporting_transparency, citation_integrity, citation_context, claim_evidence_alignment, image_integrity | claim_evidence_or_overclaim, clarity_or_presentation, method_or_experiment, reproducibility_or_code | 0.75 |
| 6 | 57 | technical_check_then_peer_review | Accept (Poster) | reporting_transparency, citation_context, claim_evidence_alignment, image_integrity | citation_or_related_work, claim_evidence_or_overclaim, method_or_experiment | 1.0 |
| 7 | 51 | technical_check_then_peer_review | Reject | effect_size_ci_coverage, reporting_transparency, citation_integrity, citation_context, claim_evidence_alignment, image_integrity | claim_evidence_or_overclaim, clarity_or_presentation, method_or_experiment, reproducibility_or_code, statistics_or_results | 0.8 |
| 8 | 57 | technical_check_then_peer_review | Reject | reporting_transparency, citation_context, claim_evidence_alignment, image_integrity | citation_or_related_work, claim_evidence_or_overclaim, clarity_or_presentation, method_or_experiment, statistics_or_results | 0.6 |
| 9 | 53 | technical_check_then_peer_review | Accept (Poster) | reporting_transparency, citation_integrity, citation_context, claim_evidence_alignment, image_integrity | citation_or_related_work, claim_evidence_or_overclaim, clarity_or_presentation, method_or_experiment, reproducibility_or_code | 0.8 |

## peersum

- Dataset: `oaimli/PeerSum` / split `train`
- Input mode: title-abstract-only
- Cases: 10 of 14993
- Fetch cache: enabled
- Mean score: 62.4 (min 60, max 65)
- Mean coverage blockers: 4.0
- Mean claim count: 1.9
- Review concern overlap proxy: 0.62
- Routes: {"technical_check_then_peer_review": 10}
- Readiness: {"ai_review_with_coverage_blockers": 10}
- Active findings: {"citation_context": 6, "claim_evidence_alignment": 10, "reporting_transparency": 10}

| Row | Score | Route | Decision | Active findings | Review concerns | Overlap |
| ---: | ---: | --- | --- | --- | --- | ---: |
| 0 | 60 | technical_check_then_peer_review | accepted-oral-papers | reporting_transparency, citation_context, claim_evidence_alignment | claim_evidence_or_overclaim, clarity_or_presentation, method_or_experiment, reproducibility_or_code, statistics_or_results | 0.6 |
| 1 | 61 | technical_check_then_peer_review | accepted-oral-papers | reporting_transparency, citation_context, claim_evidence_alignment | citation_or_related_work, claim_evidence_or_overclaim, clarity_or_presentation, method_or_experiment | 0.75 |
| 2 | 62 | technical_check_then_peer_review | accepted-oral-papers | reporting_transparency, citation_context, claim_evidence_alignment | claim_evidence_or_overclaim, clarity_or_presentation, method_or_experiment, reproducibility_or_code | 0.75 |
| 3 | 64 | technical_check_then_peer_review | accepted-oral-papers | reporting_transparency, claim_evidence_alignment | citation_or_related_work, claim_evidence_or_overclaim, clarity_or_presentation, method_or_experiment, reproducibility_or_code, statistics_or_results | 0.5 |
| 4 | 65 | technical_check_then_peer_review | accepted-oral-papers | reporting_transparency, claim_evidence_alignment | citation_or_related_work, claim_evidence_or_overclaim, clarity_or_presentation, method_or_experiment, reproducibility_or_code, statistics_or_results | 0.5 |
| 5 | 65 | technical_check_then_peer_review | accepted-oral-papers | reporting_transparency, claim_evidence_alignment | citation_or_related_work, claim_evidence_or_overclaim, clarity_or_presentation, method_or_experiment, reproducibility_or_code | 0.6 |
| 6 | 65 | technical_check_then_peer_review | accepted-oral-papers | reporting_transparency, claim_evidence_alignment | citation_or_related_work, claim_evidence_or_overclaim, clarity_or_presentation, method_or_experiment, reproducibility_or_code, statistics_or_results | 0.5 |
| 7 | 60 | technical_check_then_peer_review | accepted-oral-papers | reporting_transparency, citation_context, claim_evidence_alignment | citation_or_related_work, clarity_or_presentation, method_or_experiment | 0.667 |
| 8 | 61 | technical_check_then_peer_review | accepted-oral-papers | reporting_transparency, citation_context, claim_evidence_alignment | citation_or_related_work, claim_evidence_or_overclaim, clarity_or_presentation, method_or_experiment, reproducibility_or_code, statistics_or_results | 0.667 |
| 9 | 61 | technical_check_then_peer_review | accepted-oral-papers | reporting_transparency, citation_context, claim_evidence_alignment | citation_or_related_work, claim_evidence_or_overclaim, clarity_or_presentation, method_or_experiment, reproducibility_or_code, statistics_or_results | 0.667 |
