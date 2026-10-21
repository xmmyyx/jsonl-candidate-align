# JSONL Candidate Align

Local, nonpublic source candidate for version 0.1.0. The MIT copyright attribution is confirmed as Qi Zheng. Source-code rights review remains pending, and GitHub publication has not been authorized or carried out.

## Purpose

`jsonl-candidate-align` retrieves lexical candidates from already structured JSONL records and checks candidate output against the same lexical rules. The Python module is `jsonl_candidate_align`; the command is `jsonl-align`.

The input types are supplied by the caller. The program does not parse PDF or Word files, perform OCR, extract requirement objects, determine semantic compliance, or make procurement decisions. Similar text and matching numbers are retrieval signals, not proof that a requirement is satisfied.

## Environment and installation

Python >=3.11 is declared. No third-party runtime packages are declared; runtime code uses the Python standard library. Source builds require `setuptools>=77` and `wheel` through the declared build backend.

The documented source-install recipe below applies in the source directory containing `pyproject.toml` and `README.md`. Source-code rights review and authorization for any public distribution remain pending:

```powershell
python -m pip install .
```

This is a declared source-install procedure, not an installation result for the proposed source set. No public download URL or prebuilt archive is supplied by this draft. The command requires access to the declared build tools; it is not an offline-install guarantee.

The installed command is `jsonl-align`. The module entry point is `python -m jsonl_candidate_align`. Top-level help and version options are `--help` and `--version`.

## Command interface

Provide your own authorized input files. This proposed source scope includes no demonstration dataset or test fixtures. The table is an interface specification, not an executable demonstration or a record of execution.

| Subcommand | Required options | Optional options | Files written under the selected output directory |
|---|---|---|---|
| `align` | `--queries`, `--candidates`, `--output-dir` | `--blind-ids` followed by one or more exact query IDs | `candidate_alignment_rows.jsonl`, `candidate_alignment_summary.json` |
| `validate` | `--queries`, `--candidates`, `--actual`, `--output-dir` | None | `object_comparison.jsonl`, `validation_summary.json` |

The query and candidate options identify input JSONL files. `--actual` identifies candidate rows to check. `--output-dir` must name a new directory; existing directories are rejected. No input file may lie within that output directory. Relative paths are interpreted from the caller's working directory.

`validate` checks every query in the supplied query file. It has no `--blind-ids` option. A result generated for a selected subset is not automatically complete for the original full query file.

Exit codes: 0 for successful alignment or passing validation; 1 for parsed output that fails validation; 2 for CLI, input or path errors.

## Input contract

Use UTF-8 JSONL, optionally with a BOM, containing one JSON object per nonblank line. Duplicate object keys, duplicate record IDs and `NaN`/`Infinity` constants are rejected. IDs must be nonempty strings. The query file needs at least one object; the candidate file may be empty. `comparable_text` must be a string and may be empty.

| Input | Field | Requirement |
|---|---|---|
| Query | `blind_id` | Required unique query ID |
| Query | `blind_type` | Required: `SC`, `MRU`, `SU` or `EI` |
| Query | `comparable_text` | Required string |
| Candidate | `holdout_unit_id` | Required unique candidate ID |
| Candidate | `holdout_unit_type` | Required type from the list below |
| Candidate | `comparable_text` | Required string |
| Candidate | `pages` | Optional list of positive integers; defaults to an empty list |

Candidate types are `M3_AUTO_KEEP`, `M4_AUTO_KEEP`, `NARRATIVE_RESPONSE`, `TEMPLATE_COMMITMENT`, `MANUAL_RESOLVED_FACT`, `MANUAL_RESOLVED_BUNDLE` and `VISUAL_EVIDENCE`. These are compatibility labels; the program does not establish that they are true descriptions of a record. Any supplied `pages` field is checked for positive integer values, including when it occurs on a query object.

No sample input rows or expected result rows are included here.

## Output and validation

Each alignment row contains these 11 fields: `blind_id`, `blind_type`, `holdout_unit_id`, `holdout_unit_type`, `holdout_pages`, `score`, `jaccard`, `containment`, `number_overlap`, `shared_trigrams` and `rank`.

Ranks are one-based. Up to eight candidates are returned for each query. Final equal scores sort by persistent candidate ID. Page values come from the caller's candidate record. Scores and overlap fractions are in [0,1]; `shared_trigrams` is a nonnegative integer. Validation requires finite numeric metrics, positive integer ranks and matching input IDs, types and page lists.

The alignment summary contains `version`, `mode`, `blind_ids`, `candidate_alignment_rows`, `top_k`, `zero_candidate_blind_ids`, `semantic_gold_or_external_accuracy_evaluated`, `queries_sha256` and `candidates_sha256`.

Validation recomputes the lexical reference, independently checks supplied metrics and eligibility, and compares candidate sets and ranks using exact Decimal score equality. It can accept justified equal-score reorderings or full-capacity boundary substitutions. A score tie alone does not authorize an unknown candidate.

The validation summary contains `status`, `queries_checked`, `candidate_rows_checked`, `failed_queries`, `comparison_scope` and `semantic_gold_or_external_accuracy_evaluated`. Per-query comparison records describe candidate-set changes, rank/score changes, tie equivalence, admission checks and metric mismatches. A validation PASS means agreement with the lexical contract for the supplied inputs; it is not a semantic accuracy or procurement-compliance result.

## Limits and local data handling

The scorer uses a fixed 80-member character-trigram pre-pool, a numeric fallback of up to 40 and a final limit of eight. Arbitrary input-order or hash-seed stability at the pre-pool cutoff is not guaranteed. Inputs load into memory; large-corpus performance and hostile-input resource limits have not been established.

The runtime processes local JSONL and writes to the explicitly selected new directory. It does not require a network service, model or original document corpus. Outputs include supplied IDs, pages and metrics; errors can identify input filenames and IDs. Handle inputs, outputs and logs according to their sensitivity.

## Version and evidence boundary

An earlier nonpublic local candidate has historical technical acceptance. That acceptance is separate from this isolated local source candidate and these documents. This source set has been assembled in a separate local directory and reviewed statically; it has not been built, installed or executed, and no tests were run during this stage. Static dependency completeness does not establish installation success, platform acceptance or permission to publish.

## License and publication status

MIT is the selected license. The standard text in [LICENSE](LICENSE) states `Copyright (c) 2026 Qi Zheng`; the copyright attribution has been confirmed by the project initiator. Package metadata remains `license = "MIT"` and `license-files = ["LICENSE"]`. Relevant source-code rights, including third-party, contractual and notice obligations, still require review; the confirmed attribution does not establish final clearance of all such rights. GitHub publication has neither been authorized nor carried out.
