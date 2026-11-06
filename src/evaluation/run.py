"""Explicit, opt-in real inference evaluation. No fixture outputs enter predictions."""
import argparse
import json
import platform
import psutil
from collections import defaultdict
from pathlib import Path
from statistics import mean
from dotenv import load_dotenv
load_dotenv()
from src.config import Settings
from src.models.adapters import get_models
from src.pipeline import Pipeline
from src.preprocessing import protect
from src.validation import numbers
from src.evaluation.metrics import reference_metrics

def evaluate(cases, pipeline, outdir, variant='context'):
    outdir.mkdir(parents=True, exist_ok=True)
    predictions, groups, failures = [], defaultdict(list), []
    for case in cases:
        settings = dict(case['settings'])
        settings['contextual'] = variant != 'basic'
        action = 'full' if variant == 'rewrite' else case['action']
        result = pipeline.run(case['input'], action=action, protected_terms=case['protected_spans'], **settings)
        data = result.to_dict()
        output = result.improved if action == 'improve' else result.converted
        expected_stage = result.english if action in ('translate', 'full') else output
        success = bool(expected_stage) and not result.errors and not result.validation_failures and not (variant != 'basic' and result.basic_only)
        generated = bool(result.models_used)
        metrics = reference_metrics(output, case['hindi_references']) if success and generated and output and case['action'] != 'translate' else {'cer': None, 'wer': None, 'exact_match': None}
        metrics['chrf'] = None
        if success and result.english and case.get('english_references'):
            from sacrebleu.metrics import CHRF
            metrics['chrf'] = max(CHRF().sentence_score(result.english, [ref]).score for ref in case['english_references'])
        spans = list(protect(case['input'], case['protected_spans']).spans.values())
        metrics.update(success=success, protected_preserved=(all(expected_stage.count(s) >= case['input'].count(s) for s in spans) if success and generated and spans else None), numbers_preserved=(numbers(case['input']) == numbers(expected_stage) if success and generated and numbers(case['input']) else None))
        raw_metrics = reference_metrics(result.raw_indicxlit, case['hindi_references']) if result.raw_indicxlit and any('IndicXlit' in m for m in result.models_used) else None
        row = {'id': case['id'], 'category': case['category'], 'variant': variant, 'result': data, 'metrics': metrics, 'raw_indicxlit_metrics':raw_metrics, 'model_inference_completed':generated, 'human_review': {k: None for k in ['adequacy','fluency','meaning','grammar','tone','unsupported_additions','negation','tense','entities']}}
        predictions.append(row)
        groups[case['category']].append(metrics)
        if not success or metrics.get('exact_match') == 0:
            failures.append({'id':case['id'], 'input':case['input'], 'task':action, 'actual_output':expected_stage, 'expected':case['hindi_references'] or case.get('english_references'), 'category':'resource_or_validation' if not success else 'reference_mismatch_requires_review', 'evidence':result.errors + result.warnings, 'likely_cause':'See recorded errors; string mismatch alone does not establish semantic failure.', 'potential_improvement':'Resolve dependencies/access first; human-review actual outputs before prompt changes.'})
    def aggregate(rows):
        keys = ['cer','wer','exact_match','chrf','success','protected_preserved','numbers_preserved']
        return {key: mean(values) if (values := [r[key] for r in rows if r.get(key) is not None]) else None for key in keys}
    summary = {
        'variant': variant,
        'case_count': len(cases),
        'successful_cases': sum(r['metrics']['success'] for r in predictions),
        'model_inference_cases': sum(r['model_inference_completed'] for r in predictions),
        'scored_hindi_cases': sum(r['metrics']['cer'] is not None for r in predictions),
        'scored_english_cases': sum(r['metrics']['chrf'] is not None for r in predictions),
        'preservation_scored_cases': sum(r['metrics']['protected_preserved'] is not None for r in predictions),
        'numerical_scored_cases': sum(r['metrics']['numbers_preserved'] is not None for r in predictions),
        'raw_indicxlit_scored_cases': sum(r['raw_indicxlit_metrics'] is not None for r in predictions),
        'raw_indicxlit_metrics': aggregate([r['raw_indicxlit_metrics'] for r in predictions if r['raw_indicxlit_metrics'] is not None]),
        'hardware': {
            'os': platform.platform(), 'python': platform.python_version(),
            'ram_bytes': psutil.virtual_memory().total,
            'available_ram_bytes': psutil.virtual_memory().available,
            'processor': platform.processor(), 'device': pipeline.settings.device,
        },
        'metrics': aggregate([r['metrics'] for r in predictions]),
        'by_category': {key: aggregate(rows) for key, rows in groups.items()},
        'latency_seconds': {'per_case': [r['result']['timings'] for r in predictions]},
        'metric_note': 'Macro averages over successful generated cases only; best accepted reference per metric. References are AI-drafted and unreviewed. Scores are provisional; exact match is limited for free-form rewrites. Preservation denominators exclude unsuccessful/model-free outputs. Failed stage inputs and partial outputs are never quality-scored. Successful passthrough is processing coverage, not model quality.',
    }
    for name, obj in [('metrics.json', summary), ('failure_analysis.json', failures)]:
        (outdir / name).write_text(json.dumps(obj, ensure_ascii=False, indent=2), encoding='utf-8')
    (outdir / 'predictions.jsonl').write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in predictions), encoding='utf-8')
    return summary

def main():
    parser = argparse.ArgumentParser(description='Explicitly saves evaluation inputs and predictions to the requested output folder.')
    parser.add_argument('--cases', default='data/evaluation_cases.jsonl')
    parser.add_argument('--out', default='reports/evaluation')
    parser.add_argument('--variant', choices=['basic','context','rewrite'], default='context')
    args = parser.parse_args()
    xlit, param, trans, pool = get_models(Settings())
    cases = [json.loads(line) for line in Path(args.cases).read_text(encoding='utf-8').splitlines() if line.strip()]
    summary = evaluate(cases, Pipeline(Settings(), xlit, param, trans), Path(args.out), args.variant)
    summary['cold_load_seconds'] = pool.loads
    (Path(args.out) / 'metrics.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary['metrics'], indent=2))

if __name__ == '__main__':
    main()
