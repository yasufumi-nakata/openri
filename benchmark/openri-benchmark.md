# OpenRI benchmark summary

- Cases: 8
- Recall proxy: 1.0
- Precision proxy: 0.467
- Coverage blockers: 31

| Case | Score | Route | Expected hits | Active findings |
| --- | ---: | --- | --- | --- |
| borderline_rounding | 73 | route_to_peer_review | - | effect_size_ci_coverage |
| clean_transparent | 75 | route_to_peer_review | - | claim_evidence_alignment, effect_size_ci_coverage |
| missing_transparency | 70 | technical_check_then_peer_review | reporting_transparency | reporting_transparency |
| p_value_mismatch | 69 | statistics_editor_screen | statistical_consistency | statistical_consistency |
| placeholder_citation | 62 | technical_check_then_peer_review | citation_context, citation_integrity | citation_context, citation_integrity, claim_evidence_alignment |
| prompt_injection | 57 | integrity_hold_before_peer_review | prompt_injection | prompt_injection, reporting_transparency |
| ruleset_omission | 60 | technical_check_then_peer_review | ruleset_coverage | reporting_transparency, ruleset_coverage |
| unsupported_causal_claim | 60 | technical_check_then_peer_review | citation_context | citation_context, claim_evidence_alignment, reporting_transparency |
