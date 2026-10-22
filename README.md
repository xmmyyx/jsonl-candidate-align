# JSONL Candidate Align

Lexical candidate retrieval and exact-score validation for structured JSONL records. A personal open-source project by Qi Zheng, licensed under MIT.

[简体中文](README.zh-CN.md)

`jsonl-candidate-align` ranks candidate records using character-trigram and numeric overlap, then checks candidate output against the same lexical rules. The Python module is `jsonl_candidate_align`; the command is `jsonl-align`.

Inputs must already be structured and typed by the caller. The program does not parse PDF or Word files, perform OCR, extract requirement objects, determine semantic compliance, or make procurement decisions. Similar text and matching numbers are retrieval signals, not proof that a requirement is satisfied.

## Requirements and installation

Requires Python >=3.11. Runtime code uses only the Python standard library. Source builds require `setuptools>=77` and `wheel`.

From the source directory containing `pyproject.toml`:

```powershell
python -m pip install .
```

Installation requires access to the declared build tools. The installed command is `jsonl-align`; the equivalent module entry point is `python -m jsonl_candidate_align`. Use `--help` for usage or `--version` for the version.

## Quickstart

After installing this project, activate that Python environment and open a terminal in a new working directory. No data download is needed: the records, IDs and page number below are entirely synthetic.

Using a text editor, save these two files as UTF-8 in that working directory, with one JSON object on the only line of each file.

`queries.jsonl`:

```json
{"blind_id":"DEMO-Q1","blind_type":"SC","comparable_text":"cobalt sensor 314159"}
```

`candidates.jsonl`:

```json
{"holdout_unit_id":"DEMO-C1","holdout_unit_type":"M3_AUTO_KEEP","comparable_text":"cobalt sensor 314159","pages":[1]}
```

Run these commands in the Python environment where this project is installed. Both output directories must not already exist. For another run, use new output directory names and update `--actual` to point to the new alignment output.

```powershell
jsonl-align align --queries queries.jsonl --candidates candidates.jsonl --output-dir alignment-output
jsonl-align validate --queries queries.jsonl --candidates candidates.jsonl --actual alignment-output/candidate_alignment_rows.jsonl --output-dir validation-output
```

This example produces one candidate row in `alignment-output/candidate_alignment_rows.jsonl`. Both commands exit with code `0`; `validation-output/validation_summary.json` contains:

```json
{
  "status": "PASS",
  "queries_checked": 1,
  "candidate_rows_checked": 1,
  "failed_queries": [],
  "comparison_scope": "LEXICAL_CANDIDATE_OUTPUT_ONLY",
  "semantic_gold_or_external_accuracy_evaluated": false
}
```

`PASS` confirms agreement with the lexical contract for these inputs. It does not establish correct semantic matching, requirement satisfaction or procurement compliance.

## Technical walkthrough

[Why I Added a Validator to a Small JSONL Candidate Ranker](https://dev.to/xmmyyx/why-i-added-a-validator-to-a-small-jsonl-candidate-ranker-43c7) walks through the two CLI commands, a synthetic score-drift example, and the limits of validation.

## Usage

With your own `queries.jsonl` and `candidates.jsonl`:

```powershell
jsonl-align align --queries queries.jsonl --candidates candidates.jsonl --output-dir alignment-output
jsonl-align validate --queries queries.jsonl --candidates candidates.jsonl --actual alignment-output/candidate_alignment_rows.jsonl --output-dir validation-output
```

| Subcommand | Required options | Optional options | Files written under the output directory |
|---|---|---|---|
| `align` | `--queries`, `--candidates`, `--output-dir` | `--blind-ids` followed by one or more exact query IDs | `candidate_alignment_rows.jsonl`, `candidate_alignment_summary.json` |
| `validate` | `--queries`, `--candidates`, `--actual`, `--output-dir` | None | `object_comparison.jsonl`, `validation_summary.json` |

`--queries` and `--candidates` identify input JSONL files. `--actual` identifies candidate rows to check. Each `--output-dir` must name a new directory; existing directories are rejected. No input file may lie within that output directory. Relative paths are interpreted from the caller's working directory.

`validate` checks every query in the supplied query file. It has no `--blind-ids` option. To validate a subset, supply a query file containing that subset; partial output is not automatically complete for the original full query file.

Exit codes: `0` for successful alignment or passing validation; `1` for parsed output that fails validation; `2` for CLI, input or path errors.

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

Candidate types are `M3_AUTO_KEEP`, `M4_AUTO_KEEP`, `NARRATIVE_RESPONSE`, `TEMPLATE_COMMITMENT`, `MANUAL_RESOLVED_FACT`, `MANUAL_RESOLVED_BUNDLE` and `VISUAL_EVIDENCE`. These are compatibility labels; the program does not establish that they accurately describe a record. Any supplied `pages` field is checked for positive integer values, including when it occurs on a query object.

## Scoring rules

Text is normalized with Unicode NFKC, lowercasing, and removal of whitespace and selected punctuation. Character trigrams form a set; a nonempty string shorter than three characters forms a single token. Numeric tokens are extracted separately from the original text.

The scorer selects up to 80 records by shared-trigram count, requiring at least two shared trigrams. If this pre-pool is empty and the query has numeric tokens, it falls back to up to 40 type-compatible records with numeric overlap, in input order. The CLI uses lexical scoring without context additions.

For each candidate:

| Metric | Definition |
|---|---|
| `jaccard` | Shared trigrams divided by the union of the trigram sets |
| `containment` | Shared trigrams divided by the smaller trigram-set size |
| `number_overlap` | Shared numeric tokens divided by the smaller numeric-token-set size; zero if either set is empty |
| `score` | `0.35 * jaccard + 0.55 * containment + 0.10 * number_overlap` |

An admitted candidate must have a compatible type and at least one shared trigram, and satisfy at least one condition: `score >= 0.10`, `containment >= 0.16`, or both `number_overlap >= 0.50` and `containment >= 0.08`. These thresholds use unrounded values.

`SC` and `MRU` accept every candidate type except `VISUAL_EVIDENCE`. `SU` and `EI` accept every candidate type except `NARRATIVE_RESPONSE`.

Scores and overlap fractions are rounded to six decimal places for output. Up to eight candidates are returned per query, sorted by descending rounded score and then by persistent candidate ID for equal scores. Ranks start at one.

## Output and validation

Each alignment row contains 11 fields: `blind_id`, `blind_type`, `holdout_unit_id`, `holdout_unit_type`, `holdout_pages`, `score`, `jaccard`, `containment`, `number_overlap`, `shared_trigrams` and `rank`. Page values come from the caller's candidate record. Scores and overlap fractions are in [0,1]; `shared_trigrams` is a nonnegative integer.

The alignment summary contains `version`, `mode`, `blind_ids`, `candidate_alignment_rows`, `top_k`, `zero_candidate_blind_ids`, `semantic_gold_or_external_accuracy_evaluated`, `queries_sha256` and `candidates_sha256`.

Validation recomputes the lexical reference and independently checks every supplied candidate's metrics and eligibility. It requires finite numeric metrics, positive integer ranks, and IDs, types and page lists matching the inputs. It compares candidate sets and ranks using exact Decimal score equality, checks for duplicates and rank gaps, and enforces the eight-candidate limit.

Equal-score reorderings can pass when the other checks hold. A boundary substitution requires full lists of eight, the same cutoff score, equal numbers of additions and removals at that cutoff, independently verified added candidates, and no score drift. A score tie alone does not authorize an unknown or ineligible candidate.

The validation summary contains `status`, `queries_checked`, `candidate_rows_checked`, `failed_queries`, `comparison_scope` and `semantic_gold_or_external_accuracy_evaluated`. Per-query comparison records describe candidate-set changes, rank/score changes, tie equivalence, admission checks and metric mismatches.

A validation `PASS` means agreement with the lexical contract for the supplied inputs. It is not a semantic accuracy or procurement-compliance result. The summaries set `semantic_gold_or_external_accuracy_evaluated` to `false`.

## Known limitations and data handling

The pre-pool cutoff is not guaranteed to be stable across arbitrary input orders or Python hash seeds. The fixed limits of 80 pre-pool records, 40 numeric-fallback records and eight results can exclude relevant candidates. Inputs load into memory; large-corpus performance and hostile-input resource limits have not been established.

The runtime processes local JSONL and writes to the explicitly selected new directory. It does not require a network service, model or original document corpus. Outputs include supplied IDs, pages and metrics; errors can identify input filenames and IDs. Use inputs you are authorized to process, and handle inputs, outputs and logs according to their sensitivity.

## License

[MIT License](LICENSE). Copyright (c) 2026 Qi Zheng.
