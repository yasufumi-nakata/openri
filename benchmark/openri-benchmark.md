# OpenRI benchmark summary

- Cases: 8
- Recall proxy: 1.0
- Precision proxy: 0.583
- Coverage blockers: 31

| Case | Score | Route | Expected hits | Active findings |
| --- | ---: | --- | --- | --- |
| borderline_rounding | 74 | route_to_peer_review | - | effect_size_ci_coverage |
| clean_transparent | 77 | route_to_peer_review | - | effect_size_ci_coverage |
| missing_transparency | 69 | technical_check_then_peer_review | reporting_transparency | reporting_transparency |
| p_value_mismatch | 68 | statistics_editor_screen | statistical_consistency | statistical_consistency |
| placeholder_citation | 66 | route_to_peer_review | citation_context, citation_integrity | citation_context, citation_integrity |
| prompt_injection | 57 | integrity_hold_before_peer_review | prompt_injection | prompt_injection, reporting_transparency |
| ruleset_omission | 60 | technical_check_then_peer_review | ruleset_coverage | reporting_transparency, ruleset_coverage |
| unsupported_causal_claim | 64 | technical_check_then_peer_review | citation_context | citation_context, reporting_transparency |
