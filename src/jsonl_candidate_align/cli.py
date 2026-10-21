"""Portable filesystem adapter. Existing pure scoring/comparison is unchanged."""
import argparse
from collections import defaultdict
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import sys

from . import __version__
from .scoring import generate_candidates
from .comparison import compare_one

QUERY_TYPES={'SC','MRU','SU','EI'}
CANDIDATE_TYPES={'M3_AUTO_KEEP','M4_AUTO_KEEP','NARRATIVE_RESPONSE',
                 'TEMPLATE_COMMITMENT','MANUAL_RESOLVED_FACT',
                 'MANUAL_RESOLVED_BUNDLE','VISUAL_EVIDENCE'}
METRICS=('score','jaccard','containment','number_overlap','shared_trigrams')

def _pairs(items):
    result={}
    for key,value in items:
        if key in result:raise ValueError(f'duplicate JSON key: {key}')
        result[key]=value
    return result

def _constant(value):
    raise ValueError(f'nonfinite JSON number: {value}')

def read_jsonl(path):
    result=[]
    with Path(path).open(encoding='utf-8-sig') as stream:
        for line_number,line in enumerate(stream,1):
            if not line.strip():continue
            try:
                value=json.loads(line,object_pairs_hook=_pairs,parse_constant=_constant)
                if not isinstance(value,dict):raise ValueError('each row must be a JSON object')
            except ValueError as exc:
                raise ValueError(f'{Path(path).name}: line {line_number}: {exc}') from exc
            result.append(value)
    return result

def _string(row,key):
    value=row.get(key)
    if not isinstance(value,str) or not value.strip():raise ValueError(f'{key} must be a nonempty string')
    return value

def validate_inputs(queries,candidates):
    for data,id_key,type_key,types in [(queries,'blind_id','blind_type',QUERY_TYPES),
                                      (candidates,'holdout_unit_id','holdout_unit_type',CANDIDATE_TYPES)]:
        ids=set()
        for row in data:
            identifier=_string(row,id_key)
            if identifier in ids:raise ValueError(f'duplicate {id_key}: {identifier}')
            ids.add(identifier)
            if row.get(type_key) not in types:raise ValueError(f'{type_key} must be one of {sorted(types)}')
            if not isinstance(row.get('comparable_text'),str):raise ValueError('comparable_text must be a string')
            if 'pages' in row and (not isinstance(row['pages'],list) or any(type(p) is not int or p<1 for p in row['pages'])):
                raise ValueError('pages must be a list of positive integers')
    if not queries:raise ValueError('queries must contain at least one object')

def validate_actual_schema(actual,queries,candidates):
    qb={r['blind_id']:r for r in queries};cb={r['holdout_unit_id']:r for r in candidates}
    for row in actual:
        q=_string(row,'blind_id');c=_string(row,'holdout_unit_id')
        if q not in qb or c not in cb:raise ValueError('actual row references an unknown query/candidate ID')
        if row.get('blind_type')!=qb[q]['blind_type'] or row.get('holdout_unit_type')!=cb[c]['holdout_unit_type']:
            raise ValueError('actual row type does not match its input ID')
        if type(row.get('rank')) is not int or row['rank']<1:raise ValueError('rank must be a positive integer')
        for name in METRICS:
            value=row.get(name)
            if type(value) not in (int,float) or not math.isfinite(value):raise ValueError(f'{name} must be a finite JSON number')
            if name=='shared_trigrams':
                if type(value) is not int or value<0:raise ValueError('shared_trigrams must be a nonnegative integer')
            elif not 0<=value<=1:raise ValueError(f'{name} must be between 0 and 1')
        if row.get('holdout_pages')!=cb[c].get('pages',[]):raise ValueError('holdout_pages must match candidate pages')

def validate_output(queries,candidates,actual):
    """Recompute lexical reference and verify every supplied candidate independently."""
    validate_actual_schema(actual,queries,candidates)
    expected=generate_candidates(queries,candidates)
    old=defaultdict(list);new=defaultdict(list)
    for row in expected:old[row['blind_id']].append(row)
    for row in actual:new[row['blind_id']].append(row)
    cb={r['holdout_unit_id']:r for r in candidates}
    comparisons=[]
    for query in queries:
        qid=query['blind_id'];admitted=set();metric_errors=[]
        for row in new[qid]:
            point=generate_candidates([query],[cb[row['holdout_unit_id']]])
            valid=bool(point and all(Decimal(str(point[0][k]))==Decimal(str(row[k])) for k in METRICS))
            if valid:admitted.add(row['holdout_unit_id'])
            else:metric_errors.append(row['holdout_unit_id'])
        result=compare_one(qid,old[qid],new[qid],[],set(cb),base_admitted_ids=admitted)
        result['metric_mismatch_ids']=sorted(set(metric_errors))
        if metric_errors:
            result['status']='FAIL';result['difference_classes'].append('LEXICAL_METRIC_OR_ELIGIBILITY_MISMATCH')
        comparisons.append(result)
    summary={'status':'PASS' if all(r['status']=='PASS' for r in comparisons) else 'FAIL',
             'queries_checked':len(queries),'candidate_rows_checked':len(actual),
             'failed_queries':[r['blind_id'] for r in comparisons if r['status']=='FAIL'],
             'comparison_scope':'LEXICAL_CANDIDATE_OUTPUT_ONLY',
             'semantic_gold_or_external_accuracy_evaluated':False}
    return comparisons,summary

def _json(path,value):
    with path.open('w',encoding='utf-8',newline='\n') as stream:
        stream.write(json.dumps(value,ensure_ascii=False,indent=2,allow_nan=False)+'\n')

def _jsonl(path,values):
    with path.open('w',encoding='utf-8',newline='\n') as stream:
        for row in values:stream.write(json.dumps(row,ensure_ascii=False,sort_keys=True,allow_nan=False)+'\n')

def _output(path,inputs):
    target=Path(path).resolve()
    if target.exists():raise ValueError('output-dir must be a new directory; existing output is never overwritten')
    if any(p==target or target in p.parents for p in map(lambda p:Path(p).resolve(),inputs)):
        raise ValueError('output-dir must not contain an input file')
    return target

def _digest(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def main(argv=None):
    parser=argparse.ArgumentParser(description='JSONL lexical candidate alignment (local candidate; no document parser)')
    parser.add_argument('--version',action='version',version=__version__)
    sub=parser.add_subparsers(dest='command',required=True)
    for name in ['align','validate']:
        child=sub.add_parser(name)
        child.add_argument('--queries',required=True,help='UTF-8 JSONL: blind_id, blind_type, comparable_text')
        child.add_argument('--candidates',required=True,help='UTF-8 JSONL: holdout_unit_id, holdout_unit_type, comparable_text, optional pages')
        child.add_argument('--output-dir',required=True,help='new directory; never overwrite existing paths')
        if name=='align':child.add_argument('--blind-ids',nargs='+',help='optional exact query ID subset')
        else:child.add_argument('--actual',required=True,help='candidate_alignment_rows.jsonl to validate')
    args=parser.parse_args(argv)
    try:
        inputs=[args.queries,args.candidates]+([args.actual] if args.command=='validate' else [])
        target=_output(args.output_dir,inputs)
        queries=read_jsonl(args.queries);candidates=read_jsonl(args.candidates)
        validate_inputs(queries,candidates)
        if args.command=='align' and args.blind_ids:
            ids=set(args.blind_ids);unknown=ids-{r['blind_id'] for r in queries}
            if unknown:raise ValueError(f'unknown blind IDs: {sorted(unknown)}')
            queries=[r for r in queries if r['blind_id'] in ids]
        if args.command=='align':
            result=generate_candidates(queries,candidates)
            found={r['blind_id'] for r in result}
            summary={'version':__version__,'mode':'LEXICAL_ONLY_CONTEXT_DISABLED',
                     'blind_ids':[q['blind_id'] for q in queries],
                     'candidate_alignment_rows':len(result),'top_k':8,
                     'zero_candidate_blind_ids':[q['blind_id'] for q in queries if q['blind_id'] not in found],
                     'semantic_gold_or_external_accuracy_evaluated':False,
                     'queries_sha256':_digest(args.queries),'candidates_sha256':_digest(args.candidates)}
            target.mkdir(parents=True,exist_ok=False)
            _jsonl(target/'candidate_alignment_rows.jsonl',result)
            _json(target/'candidate_alignment_summary.json',summary)
            print(json.dumps(summary,ensure_ascii=False));return 0
        actual=read_jsonl(args.actual)
        comparison,summary=validate_output(queries,candidates,actual)
        target.mkdir(parents=True,exist_ok=False)
        _jsonl(target/'object_comparison.jsonl',comparison)
        _json(target/'validation_summary.json',summary)
        print(json.dumps(summary,ensure_ascii=False));return 0 if summary['status']=='PASS' else 1
    except (ValueError,OSError,TypeError,KeyError) as exc:
        print(f'error: {exc}',file=sys.stderr);return 2

if __name__=='__main__':raise SystemExit(main())
