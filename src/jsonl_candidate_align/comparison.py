"""Existing pure functions, extracted unchanged; local candidate only."""
from __future__ import annotations
from decimal import Decimal


def compare_one(obj, old, new, traces, known, *, base_admitted_ids=(), allowed_context_ids=()):
    """Compare ranked outputs with exact Decimal equality and explicit proofs.

    base_admitted_ids must be verified using the base scorer/eligibility path.
    allowed_context_ids must be verified against the frozen admission scope.
    Neither proof is inferred from a score tie or from the new output alone.
    """
    old = sorted(old, key=lambda r: int(r['rank']))
    new = sorted(new, key=lambda r: int(r['rank']))
    oi = [r['holdout_unit_id'] for r in old]
    ni = [r['holdout_unit_id'] for r in new]
    os = {r['holdout_unit_id']: Decimal(str(r['score'])) for r in old}
    ns = {r['holdout_unit_id']: Decimal(str(r['score'])) for r in new}
    added = sorted(set(ni) - set(oi))
    dropped = sorted(set(oi) - set(ni))
    trace_ids = {r['holdout_unit_id'] for r in traces}
    verified_context = trace_ids & set(allowed_context_ids)
    invalid_context = sorted(trace_ids - set(allowed_context_ids))
    legal_added = set(base_admitted_ids) | verified_context
    unverified_added = sorted(set(added) - legal_added)
    drift = sorted(k for k in os.keys() & ns.keys() if os[k] != ns[k])
    finite = all(s.is_finite() for s in list(os.values()) + list(ns.values()))
    scores = [ns[k] for k in ni]
    descending = finite and scores == sorted(scores, reverse=True)
    positions = {k: i for i, k in enumerate(ni)}
    shared = [k for k in oi if k in ns]
    non_tie_changes, tie_changes = [], []
    for i, one in enumerate(shared):
        for two in shared[i + 1:]:
            if positions[one] > positions[two]:
                (tie_changes if os[one] == os[two] else non_tie_changes).append([one, two])

    # An exemption is restricted to full K=8 lists and the *same cutoff score*.
    boundary = bool(dropped and added and len(old) == len(new) == 8
                    and len(dropped) == len(added) and not drift
                    and not invalid_context and not unverified_added and descending)
    if boundary:
        cutoff = min(os.values())
        boundary = (cutoff == min(ns.values())
                    and all(os[k] == cutoff for k in dropped)
                    and all(ns[k] == cutoff for k in added))
    real_drops = [] if boundary else dropped
    # New base members without a cutoff substitution cannot be excused merely
    # because they pass lexical eligibility; ordinary recall drift stays FAIL.
    unexpected_set_change = bool(unverified_added or
                                 (set(added) - verified_context and not boundary))
    oldtop = oi[0] if oi else None
    newtop = ni[0] if ni else None
    top_changed = oldtop != newtop
    tie_top = bool(top_changed and oldtop is not None and newtop is not None
                   and finite and os[oldtop] == ns[newtop]
                   and os[oldtop] == max(os.values()) == max(ns.values()))
    context_top = bool(newtop in verified_context and newtop in added and descending)
    top_bad = top_changed and not (tie_top or context_top)
    duplicate = len(ni) - len(set(ni))
    ranks = [r['rank'] for r in new]
    gap = ranks != list(range(1, len(new) + 1)) or any(type(v) is not int for v in ranks)
    unknown = sorted({k for k in ni if not k or k not in known})
    ranking_bad = bool(non_tie_changes or not descending)
    failures = []
    for flag, label in [(not finite, 'INVALID_SCORE'), (drift, 'SCORE_DRIFT'),
                        (ranking_bad, 'NON_TIE_ORDER_CHANGE'),
                        (real_drops, 'REAL_LEGACY_DROP'),
                        (invalid_context, 'REAL_UNEXPECTED_CONTEXT_ADMISSION'),
                        (unexpected_set_change, 'UNEXPLAINED_CANDIDATE_SET_CHANGE'),
                        (top_bad, 'UNEXPECTED_TOP1_CHANGE'),
                        (len(new) > 8 or duplicate or gap or unknown, 'CAPACITY_OR_UNIQUENESS_ERROR')]:
        if flag:
            failures.append(label)
    permitted = []
    if boundary:
        permitted.append('TIE_EQUIVALENT_BOUNDARY_SUBSTITUTION')
    if tie_top:
        permitted.append('TIE_EQUIVALENT_TOP1_CHANGE')
    if tie_changes:
        permitted.append('TIE_EQUIVALENT_ORDER_CHANGE')
    if added and set(added) <= verified_context:
        permitted.append('EXPECTED_PATCH_ADDITION')
    classes = failures + permitted or ['NO_CHANGE']
    return {'blind_id': obj, 'status': 'FAIL' if failures else 'PASS',
            'difference_class': classes[0], 'difference_classes': classes,
            'legacy_candidate_ids': oi, 'replay_candidate_ids': ni,
            'newly_admitted_ids': added, 'dropped_legacy_ids': dropped,
            'real_legacy_drop_ids': real_drops,
            'legacy_top1': oldtop, 'replay_top1': newtop, 'top1_changed': top_changed,
            'unexpected_top1_change': bool(top_bad),
            'score_drift_candidate_ids': drift, 'ranking_drift': ranking_bad,
            'non_tie_order_changed_pairs': non_tie_changes, 'tie_order_changed_pairs': tie_changes,
            'tie_equivalent_boundary_substitution': bool(boundary),
            'tie_equivalent_top1_change': tie_top,
            'unexpected_context_admission': bool(invalid_context),
            'invalid_context_ids': invalid_context,
            'unverified_added_ids': unverified_added,
            'capacity_violation': len(new) > 8, 'duplicate_candidate_count': duplicate,
            'rank_gap': gap, 'unknown_holdout_ids': unknown, 'context_trace': traces}

