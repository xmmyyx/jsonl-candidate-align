# JSONL Candidate Align

**Rank text records from JSONL, then check that saved scores and rankings still agree with the original inputs.**

[简体中文](README.zh-CN.md)

Have a query such as `cobalt sensor 314159` and a pool of text records to review? `jsonl-align align` returns up to eight candidates per query using shared character sequences and numbers. If a later script edits or transforms the saved result, `jsonl-align validate` recomputes the reference from the original inputs and reports mismatched scores, candidates or ranks.

| Step | You supply | You get |
|---|---|---|
| `align` | Query JSONL + candidate-pool JSONL | Ranked candidate rows with IDs, scores and supplied page references |
| `validate` | The same inputs + saved candidate rows | PASS/FAIL summary, per-query differences and an exit code |

**Before using your own data:** records must already have IDs, text and one of the fixed type labels. This is a lexical shortlist and output-checking tool: it does not understand meaning, parse PDF/Word, perform OCR, extract requirement objects, determine semantic compliance or make procurement decisions. Similar text and matching numbers do not prove that a requirement is satisfied. See [Input contract](#input-contract) before mapping your data.

The synthetic demo below gives `PASS` for the generated row, then `FAIL` / `SCORE_DRIFT` after only its saved score changes from `1.0` to `0.5`. Generation and validation share the scoring implementation; PASS confirms agreement with that lexical contract, not semantic correctness or a defect-free algorithm.

Personal open-source project by Qi Zheng · MIT License. Python module: `jsonl_candidate_align`; command: `jsonl-align`.

## Requirements and installation

Requires Python >=3.11. Runtime code uses only the Python standard library. Source builds require `setuptools>=77` and `wheel`.

In a terminal, get the source and enter the directory containing `pyproject.toml` (skip the first two commands if you already have a checkout):

```powershell
git clone https://github.com/xmmyyx/jsonl-candidate-align.git
cd jsonl-candidate-align
python -m venv .venv
```

Activate the environment: `.\.venv\Scripts\Activate.ps1` in PowerShell, or `source .venv/bin/activate` in a POSIX shell. Then install:

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

### Fail: detect a changed score even when rank stays the same

For this single identical-text pair, the generated row has `score: 1.0` and `rank: 1`. Save the following as `change_demo_score.py` in the same working directory. It writes a separate synthetic copy with only `score` changed to `0.5`; the inputs, original output, IDs and rank stay unchanged. The helper file `candidate_alignment_rows_modified.jsonl` is overwritten if this helper runs again.

```python
import json
from pathlib import Path

source = Path("alignment-output/candidate_alignment_rows.jsonl")
rows = [json.loads(line) for line in source.read_text(encoding="utf-8").splitlines() if line.strip()]
assert len(rows) == 1 and rows[0]["score"] == 1.0
rows[0]["score"] = 0.5
Path("candidate_alignment_rows_modified.jsonl").write_text(
    "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows),
    encoding="utf-8",
)
```

Run it, then validate the modified copy. `validation-fail-output` must not already exist:

```powershell
python change_demo_score.py
jsonl-align validate --queries queries.jsonl --candidates candidates.jsonl --actual candidate_alignment_rows_modified.jsonl --output-dir validation-fail-output
```

The validation command intentionally exits with code `1`. Its `validation_summary.json` has `status: "FAIL"` and `failed_queries: ["DEMO-Q1"]`. In `validation-fail-output/object_comparison.jsonl`, the query's `difference_classes` includes both `SCORE_DRIFT` and `LEXICAL_METRIC_OR_ELIGIBILITY_MISMATCH`; `score_drift_candidate_ids` is `["DEMO-C1"]`.

| Saved result for DEMO-C1 | Rank | Validation | Exit code |
|---|---|---|---|
| Generated `score: 1.0` | 1 | `PASS` | 0 |
| Copied row, `score: 0.5` | 1 | `FAIL`, including `SCORE_DRIFT` | 1 |

`SCORE_DRIFT` identifies a shared candidate whose saved score differs from the recomputed reference. It can catch a score altered by a downstream transformation even when IDs and rank still look right; it does not identify the cause or detect changes in meaning. This controlled failure is a synthetic contract demonstration, not an external accuracy test. Scoring uses floating-point arithmetic and rounds output to six decimals; validation uses exact Decimal comparisons of the saved numeric values and recomputed output.

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

### What the field names and type labels mean for integration

Here, a **query** is the text you want to look up; a **candidate** is a record in the pool you want to search. `blind_id` is your query ID and `holdout_unit_id` is your candidate ID. These are fixed schema names; you supply the identifiers and `comparable_text` yourself. JSONL is a text format with one JSON object on each nonblank line, not a JSON array. The minimal files above are the starting template.

The accepted type labels are specific to this schema, not arbitrary Python types or a general business taxonomy. The CLI does not infer types, accept custom labels or offer a flag to disable type filtering. Choose a mapping deliberately before using this with another dataset:

| Query labels | Candidate labels excluded by type compatibility |
|---|---|
| `SC`, `MRU` | `VISUAL_EVIDENCE` |
| `SU`, `EI` | `NARRATIVE_RESPONSE` |

Compatibility alone does not admit a candidate; the lexical rules below still apply. The demo uses the compatible pair `SC` / `M3_AUTO_KEEP` solely to exercise the CLI, not as a universal mapping recommendation. `AUTO_KEEP` does not trigger an automatic approval, and `VISUAL_EVIDENCE` does not enable image analysis: scoring still uses `comparable_text`. Adapting your data to these labels is your responsibility; the program does not verify that the labels describe its meaning.

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
