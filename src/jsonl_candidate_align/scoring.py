"""Existing pure functions, extracted unchanged; local candidate only."""
from __future__ import annotations
import re, time, unicodedata
from collections import Counter, defaultdict


def norm(s):
    s = unicodedata.normalize("NFKC", str(s or "")).lower()
    s = re.sub(r"\s+", "", s)
    s = re.sub(
        r"[，,。；;：:、·•“”\"'‘’（）()\[\]【】<>《》_\-—]",
        "",
        s,
    )
    return s


def trigrams_from_norm(s):
    if not s:
        return set()
    if len(s) < 3:
        return {s}
    return {s[i : i + 3] for i in range(len(s) - 2)}


def numbers(s):
    return set(
        re.findall(
            r"\d+(?:\.\d+)?%?"
            r"|[A-Za-z]+[-_/]?\d+[A-Za-z0-9\-_/]*",
            str(s or ""),
        )
    )


def compatible(blind_type, h1_type):
    if blind_type in {"SC", "MRU"}:
        return h1_type in {
            "M3_AUTO_KEEP",
            "M4_AUTO_KEEP",
            "NARRATIVE_RESPONSE",
            "TEMPLATE_COMMITMENT",
            "MANUAL_RESOLVED_FACT",
            "MANUAL_RESOLVED_BUNDLE",
        }

    if blind_type in {"SU", "EI"}:
        return h1_type in {
            "M3_AUTO_KEEP",
            "M4_AUTO_KEEP",
            "MANUAL_RESOLVED_FACT",
            "MANUAL_RESOLVED_BUNDLE",
            "VISUAL_EVIDENCE",
            "TEMPLATE_COMMITMENT",
        }

    return True


def _feature_copy(rows):
    prepared = []
    for source in rows:
        x = dict(source)
        txt = x.get("comparable_text", "")
        n = norm(txt)
        x["_n"] = n
        x["_g"] = trigrams_from_norm(n)
        x["_nums"] = numbers(txt)
        prepared.append(x)
    return prepared


def generate_candidates(blind_rows, holdout_rows, *, recall_context=None):
    """Generate candidate rows while preserving the frozen lexical scorer.

    `recall_context=None` is the exact legacy path. A supplied context may only
    add traced candidate reachability; it never changes feature values, score,
    sort order, rank rule, or K=8.
    """
    blind = _feature_copy(blind_rows)
    h1 = _feature_copy(holdout_rows)

    inverted = defaultdict(set)
    for idx, x in enumerate(h1):
        for g in x["_g"]:
            inverted[g].add(idx)

    h1_index = {str(x["holdout_unit_id"]): i for i, x in enumerate(h1)}
    trace_map = (recall_context or {}).get("candidate_traces", {}) if recall_context else {}

    candidate_rows = []
    start_time = time.time()

    for bi, b in enumerate(blind, 1):
        bg = b["_g"]
        hit_counts = Counter()
        for g in bg:
            for hi in inverted.get(g, ()):
                hit_counts[hi] += 1

        pre_candidates = [
            hi for hi, cnt in hit_counts.most_common(80) if cnt >= 2
        ]

        if not pre_candidates and b["_nums"]:
            for hi, h in enumerate(h1):
                if not compatible(b["blind_type"], h["holdout_unit_type"]):
                    continue
                if b["_nums"] & h["_nums"]:
                    pre_candidates.append(hi)
                    if len(pre_candidates) >= 40:
                        break

        legacy_pre_candidates = list(pre_candidates)
        traced = {
            str(x["holdout_unit_id"]): x
            for x in trace_map.get(str(b["blind_id"]), [])
            if str(x.get("holdout_unit_id")) in h1_index
        }
        for holdout_id in traced:
            hi = h1_index[holdout_id]
            if hi not in pre_candidates:
                pre_candidates.append(hi)

        legacy_pre_set = set(legacy_pre_candidates)
        scored = []
        legacy_scored_ids = set()

        for hi in pre_candidates:
            h = h1[hi]
            holdout_id = str(h["holdout_unit_id"])
            context_eligible = holdout_id in traced
            normal_type_compatible = compatible(
                b["blind_type"], h["holdout_unit_type"]
            )
            if not normal_type_compatible and not context_eligible:
                continue

            hg = h["_g"]
            if (not bg or not hg) and not context_eligible:
                continue

            inter = len(bg & hg) if bg and hg else 0
            if inter == 0 and not context_eligible:
                continue

            union = len(bg | hg)
            jac = inter / union if union else 0.0
            contain = inter / min(len(bg), len(hg)) if bg and hg else 0.0

            bn = b["_nums"]
            hn = h["_nums"]
            if bn and hn:
                num_overlap = len(bn & hn) / min(len(bn), len(hn))
            else:
                num_overlap = 0.0

            score = (
                0.35 * jac
                + 0.55 * contain
                + 0.10 * num_overlap
            )

            normal_admitted = (
                normal_type_compatible
                and inter > 0
                and (
                    score >= 0.10
                    or contain >= 0.16
                    or (num_overlap >= 0.50 and contain >= 0.08)
                )
            )
            if not (normal_admitted or context_eligible):
                continue

            row = {
                "blind_id": b["blind_id"],
                "blind_type": b["blind_type"],
                "holdout_unit_id": h["holdout_unit_id"],
                "holdout_unit_type": h["holdout_unit_type"],
                "holdout_pages": h.get("pages", []),
                "score": round(score, 6),
                "jaccard": round(jac, 6),
                "containment": round(contain, 6),
                "number_overlap": round(num_overlap, 6),
                "shared_trigrams": inter,
            }
            scored.append(row)
            if normal_admitted and hi in legacy_pre_set:
                legacy_scored_ids.add(holdout_id)

        # Exact score ties carry no modeled semantic priority. The previous
        # x["containment"] / x["number_overlap"] tie weights are replaced by
        # the persistent HOLDOUT ID solely to make ordering reproducible.
        scored.sort(key=lambda x: (-x["score"], x["holdout_unit_id"]))

        context_scored_ids = {
            str(x["holdout_unit_id"])
            for x in scored
            if str(x["holdout_unit_id"]) in traced
        }
        new_context_count = len(context_scored_ids - legacy_scored_ids)
        if b["blind_type"] == "SU" and new_context_count > 4:
            raise ValueError(
                f"CU001 context additions exceed fail-closed limit for {b['blind_id']}: "
                f"{new_context_count} > 4"
            )
        if b["blind_type"] == "EI" and new_context_count > 6:
            raise ValueError(
                f"CU002 context additions exceed fail-closed limit for {b['blind_id']}: "
                f"{new_context_count} > 6"
            )

        top = scored[:8]
        top_ids = {str(x["holdout_unit_id"]) for x in top}
        dropped_legacy = legacy_scored_ids - top_ids
        if traced and dropped_legacy:
            raise ValueError(
                f"context recall would drop legacy candidates for {b['blind_id']}: "
                f"{sorted(dropped_legacy)}"
            )

        for rank, r in enumerate(top, 1):
            r["rank"] = rank
            candidate_rows.append(r)

        # Retain the original progress variable so the candidate function stays
        # behaviorally close to the historical loop without performing I/O.
        _ = (bi, start_time)

    return candidate_rows

