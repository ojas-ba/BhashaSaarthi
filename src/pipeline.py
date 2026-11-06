import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from time import perf_counter
from src.preprocessing import normalize, protect, roman_tokens
from src.validation import validate
from src.models.interfaces import ModelUnavailable

ENGLISH = set(json.loads((Path(__file__).resolve().parents[1] / 'data/english_words.json').read_text(encoding='utf-8')))
AMBIGUOUS = {'is', 'to', 'me', 'main', 'kal'}

@dataclass
class Result:
    original: str
    converted: str = ''
    improved: str = ''
    english: str = ''
    raw_indicxlit: str = ''
    context_corrected: str = ''
    candidates: dict = field(default_factory=dict)
    models_used: list = field(default_factory=list)
    timings: dict = field(default_factory=dict)
    warnings: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    validation_failures: list = field(default_factory=list)
    basic_only: bool = False
    def to_dict(self):
        return asdict(self)

class Pipeline:
    def __init__(self, settings, xlit, param, translator):
        self.settings, self.xlit, self.param, self.translator = settings, xlit, param, translator

    def run(self, text, action='convert', style='Natural Hinglish', tone='Minimal correction', contextual=True, translate_source='converted', converted='', improved='', protected_terms=()):
        if not text.strip():
            raise ValueError('Enter some text first.')
        if len(text) > self.settings.max_chars:
            raise ValueError(f'Input exceeds {self.settings.max_chars} characters; nothing was truncated.')
        if action not in ('convert', 'improve', 'translate', 'full'):
            raise ValueError('Unknown action')
        if style not in ('Natural Hinglish', 'Natural Hindi') or tone not in ('Minimal correction', 'Formal', 'Casual'):
            raise ValueError('Unknown style or tone')
        original = normalize(text)
        result = Result(original=original)
        result.warnings.append('Deterministic checks cannot guarantee semantic equivalence. Review names, ambiguity, negation, tense and certainty.')
        start_all = perf_counter()

        def stage(name, model, function):
            start = perf_counter()
            pool = getattr(model, 'pool', None)
            before_load = getattr(pool, 'total_load_seconds', 0)
            try:
                value = function()
                if model.name not in result.models_used:
                    result.models_used.append(model.name)
                return value
            finally:
                elapsed = perf_counter() - start
                cold = getattr(pool, 'total_load_seconds', 0) - before_load
                result.timings[name] = result.timings.get(name, 0) + elapsed
                if pool is not None:
                    result.timings[name + '_cold_load'] = result.timings.get(name + '_cold_load', 0) + cold
                    result.timings[name + '_excluding_load'] = result.timings.get(name + '_excluding_load', 0) + max(0, elapsed - cold)

        def checked(source, candidate, spans, target='hi'):
            errors = validate(source, candidate, spans, target)
            if errors:
                result.validation_failures.extend(errors)
                result.warnings.extend(errors + ['Validation failed: retained the stage input.'])
                return source
            return candidate

        try:
            if action in ('convert', 'full'):
                protected = protect(original, protected_terms)
                words = roman_tokens(protected.text)
                candidates = stage('indicxlit', self.xlit, lambda: self.xlit.candidates(words)) if words else {}
                result.candidates = candidates
                raw = re.sub(r'ZXQ\d+QXZ|[A-Za-z]+(?:\x27[A-Za-z]+)?', lambda m: m.group() if m.group().startswith('ZXQ') else candidates[m.group()][0], protected.text)
                result.raw_indicxlit = protected.restore(raw)
                draft = re.sub(r'ZXQ\d+QXZ|[A-Za-z]+(?:\x27[A-Za-z]+)?', lambda m: m.group() if m.group().startswith('ZXQ') or m.group().lower() in AMBIGUOUS or (style == 'Natural Hinglish' and m.group().lower() in ENGLISH) else candidates[m.group()][0], protected.text)
                ambiguous = sorted(set(w.lower() for w in words) & AMBIGUOUS)
                if ambiguous:
                    result.warnings.append('Potentially ambiguous words: ' + ', '.join(ambiguous) + '. kal can mean yesterday/tomorrow; unresolved forms remain unchanged in basic mode.')
                result.converted = checked(original, protected.restore(draft), protected.spans.values())
                if contextual and (words or style == 'Natural Hindi'):
                    try:
                        instruction = ('Resolve Roman Hindi/English words using the original sentence and transliteration draft. Output Hindi words in Devanagari. ' + ('Keep clear English words in Latin script.' if style == 'Natural Hinglish' else 'Render fluent Hindi, translating English words where appropriate.'))
                        generated = stage('context_param1', self.param, lambda: self.param.rewrite(protected.text, draft, instruction))
                        result.context_corrected = protected.restore(generated)
                        result.converted = checked(original, result.context_corrected, protected.spans.values())
                    except ModelUnavailable as exc:
                        result.basic_only = True
                        result.warnings.append('BASIC TRANSLITERATION ONLY: ' + str(exc))
                else:
                    result.basic_only = bool(words)
                if result.basic_only and style == 'Natural Hindi':
                    result.warnings.append('Natural Hindi rendering requires Param1; this is only a basic script draft.')
            else:
                result.converted = converted
                result.improved = improved

            if action in ('improve', 'full'):
                source = result.converted if action == 'full' else original
                protected = protect(source, protected_terms)
                generated = stage('rewrite_param1', self.param, lambda: self.param.rewrite(protected.text, protected.text, f'Apply {tone.lower()} editing. Preserve the original level of obligation and certainty. Output Hindi script with clear English words retained.'))
                result.improved = checked(source, protected.restore(generated), protected.spans.values())

            if action in ('translate', 'full'):
                if translate_source not in ('converted', 'improved'):
                    raise ValueError('Unknown translation source')
                source = getattr(result, translate_source)
                if not source:
                    # Independent translation accepts Hindi input directly.
                    if action == 'translate' and re.search(r'[\u0900-\u097f]', original):
                        source = original
                    else:
                        raise ValueError('The selected Hindi result is unavailable. Run its action first, or enter Hindi text.')
                protected = protect(source, protected_terms)
                # Translate immutable spans separately to avoid NMT corrupting placeholder tokens.
                pieces = re.split(r'(ZXQ\d+QXZ)', protected.text)
                outputs = []
                for piece in pieces:
                    if piece in protected.spans or not piece.strip():
                        outputs.append(piece)
                    else:
                        output = stage('indictrans2', self.translator, lambda p=piece: self.translator.translate(p))
                        outputs.append((' ' if piece.startswith(' ') else '') + output.strip() + (' ' if piece.endswith(' ') else ''))
                translated = protected.restore(''.join(outputs))
                result.english = checked(source, translated, protected.spans.values(), 'en')
                result.warnings.append('Protected spans are translated around, which can reduce fluency. Latin names remain exact; Hindi names require explicit protection.')
        except Exception as exc:
            message = f'{type(exc).__name__}: {exc}'
            if 'out of memory' in str(exc).lower():
                message += ' Close other model processes, shorten input, or move to a device with more memory.'
            result.errors.append(message)
        result.timings['total'] = perf_counter() - start_all
        return result
