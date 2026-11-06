"""Unit tests use explicit test doubles only. They are not model quality evidence."""
import json
from pathlib import Path
import pytest
from src.config import Settings
from src.preprocessing import normalize, protect, roman_tokens
from src.validation import validate
from src.pipeline import Pipeline
from src.models.interfaces import ModelUnavailable
from src.evaluation.metrics import distance, reference_metrics

class XlitDouble:
    name = 'TEST DOUBLE xlit'
    def candidates(self, words):
        return {w: [{'mujhe':'मुझे', 'jana':'जाना', 'hai':'है', 'nahi':'नहीं'}.get(w, 'शब्द')] for w in words}

class ParamDouble:
    name = 'TEST DOUBLE param'
    def rewrite(self, original, draft, instruction): return draft

class UnavailableDouble:
    name = 'TEST DOUBLE unavailable'
    def rewrite(self, *args): raise ModelUnavailable('explicit unavailable test')
    def candidates(self, *args): raise ModelUnavailable('explicit unavailable test')

class TranslationDouble:
    name = 'TEST DOUBLE translation'
    def translate(self, text): return 'I have to go home.'

def pipeline(param=None):
    return Pipeline(Settings(), XlitDouble(), param or ParamDouble(), TranslationDouble())

def test_unicode_and_lines():
    assert normalize('a  b\r\nc\rd') == 'a  b\nc\nd'
    assert normalize('e\u0301') == 'é'

@pytest.mark.parametrize('text', ['Naman 12/11/2026 250.50', 'test@example.com https://example.com/a?q=2', '`x = 2`\n```python\nprint(1)\n```', 'IIT Delhi #hello', 'राम 22'])
def test_span_roundtrip(text):
    protected = protect(text, ['राम'])
    assert protected.restore(protected.text) == text

def test_missing_duplicate_marker_rejected():
    p = protect('Naman ne 12 kaha')
    with pytest.raises(ValueError): p.restore('changed')
    with pytest.raises(ValueError): p.restore(p.text + ' ZXQ0QXZ')

def test_reserved_marker():
    with pytest.raises(ValueError): protect('ZXQ0QXZ')

def test_extra_spans_merge():
    p = protect('New Delhi', ['New Delhi'])
    assert list(p.spans.values()) == ['New Delhi']

def test_marker_not_transliterated():
    assert roman_tokens('ZXQ0QXZ mujhe mujhe जाना') == ['mujhe']

def test_numerical_negation_validation():
    errors = validate('मुझे 12 नहीं चाहिए', 'मुझे 13 चाहिए')
    assert 'Numbers changed.' in errors
    assert 'Possible negation loss.' in errors

def test_devanagari_skips_xlit():
    p = Pipeline(Settings(), UnavailableDouble(), ParamDouble(), TranslationDouble())
    r = p.run('मुझे जाना है', contextual=False)
    assert r.converted == 'मुझे जाना है' and not r.models_used

def test_devanagari_does_not_need_context_model():
    r = pipeline(UnavailableDouble()).run('मुझे जाना है')
    assert r.converted == 'मुझे जाना है' and not r.errors and not r.basic_only

def test_invalid_generated_marker_retains_draft():
    class BrokenParam(ParamDouble):
        def rewrite(self, *args): return 'नाम बदल दिया'
    r = pipeline(BrokenParam()).run('Naman mujhe jana hai')
    assert r.errors and r.converted.startswith('Naman')

def test_rejected_rewrite_not_scored(tmp_path):
    from src.evaluation.run import evaluate
    case = {'id':'unit','category':'unit','input':'मुझे जाना है','action':'improve','settings':{},'protected_spans':[],'hindi_references':['मुझे जाना है'],'english_references':[]}
    summary = evaluate([case], pipeline(UnavailableDouble()), tmp_path)
    assert summary['metrics']['cer'] is None
    assert summary['successful_cases'] == 0

def test_preservation_denominators_exclude_vacuous_cases(tmp_path):
    from src.evaluation.run import evaluate
    cases = [dict(id=str(i),category='unit',input=text,action='convert',settings={},protected_spans=[],hindi_references=[reference],english_references=[]) for i,text,reference in [(1,'Naman mujhe jana hai','Naman मुझे जाना है'),(2,'mujhe jana hai','मुझे जाना है')]]
    summary = evaluate(cases, pipeline(), tmp_path, variant='basic')
    assert summary['preservation_scored_cases'] == 1
    assert summary['numerical_scored_cases'] == 0
    assert summary['metrics']['protected_preserved'] == 1
    assert summary['metrics']['numbers_preserved'] is None

@pytest.mark.parametrize('text', ['', ' ', 'a' * 1801])
def test_input_limits(text):
    with pytest.raises(ValueError): pipeline().run(text)

def test_basic_conversion():
    r = pipeline().run('mujhe meeting jana hai', contextual=False)
    assert r.converted == 'मुझे meeting जाना है'
    assert r.basic_only and not r.errors

def test_unavailable_context_explicit():
    r = pipeline(UnavailableDouble()).run('mujhe jana hai')
    assert r.basic_only and any('BASIC TRANSLITERATION' in w for w in r.warnings)

def test_unavailable_improvement_no_fake_output():
    r = pipeline(UnavailableDouble()).run('मुझे जाना है', action='improve')
    assert r.errors and not r.improved

def test_independent_translation():
    r = pipeline().run('मुझे घर जाना है।', action='translate')
    assert r.english == 'I have to go home.'
    assert r.models_used == ['TEST DOUBLE translation']

def test_translation_source_required():
    r = pipeline().run('mujhe jana hai', action='translate', translate_source='improved')
    assert r.errors and not r.english

def test_metric_known_distances():
    assert distance('kitten','sitting') == 3
    assert reference_metrics('a b',['a c']) == {'cer':1/3,'wer':0.5,'exact_match':0.0}
    assert reference_metrics('  HELLO\n',['hello'])['exact_match'] == 1
    assert reference_metrics('abc',['xyz','abc'])['cer'] == 0

def test_dataset_schema_counts():
    rows = [json.loads(x) for x in Path('data/evaluation_cases.jsonl').read_text(encoding='utf-8').splitlines()]
    from collections import Counter
    assert list(Counter(x['category'] for x in rows).values()) == [10,10,8,7,5,5,5]
    assert len(set(x['id'] for x in rows)) == 50
    assert all(x['human_review_status'] == 'unreviewed' for x in rows)

def test_translation_setup_error_is_actionable():
    from src.models.adapters import ModelPool
    with pytest.raises(ModelUnavailable) as caught:
        ModelPool(Settings(remote_code=False)).load('trans')
    message = str(caught.value)
    assert 'HF_TOKEN' in message
    assert 'requirements-models.txt' in message
    assert 'fully restart Streamlit' in message
    assert 'Changing the flag alone' in message

def test_local_translation_rejects_wrong_checkpoint(monkeypatch):
    from src.models.adapters import LocalTranslationWorker
    class Response:
        def raise_for_status(self): pass
        def json(self): return {'model':'different-model','revision':'wrong','translation':'Untrusted output'}
    monkeypatch.setattr('src.models.adapters.requests.post', lambda *args, **kwargs: Response())
    with pytest.raises(ModelUnavailable, match='model/revision differs'):
        LocalTranslationWorker(Settings(trans_url='http://127.0.0.1:8766')).translate('मुझे जाना है')

def test_param_memory_error_reports_actual_available_ram(monkeypatch):
    from types import SimpleNamespace
    from src.models.adapters import ModelPool
    monkeypatch.setattr('psutil.virtual_memory', lambda: SimpleNamespace(available=int(0.75 * 1024**3)))
    with pytest.raises(ModelUnavailable, match='0.75 GiB RAM') as caught:
        ModelPool(Settings(precision='float32')).load('param')
    assert 'conservative 13 GiB' in str(caught.value)
    assert 'quantized backend has not been verified' in str(caught.value)
