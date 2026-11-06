import re
import unicodedata

def normalize_metric(text):
    """NFC, casefold Latin, collapse whitespace. Retain punctuation and Hindi marks."""
    return re.sub(r'\s+', ' ', unicodedata.normalize('NFC', text).casefold()).strip()

def distance(a, b):
    previous = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        current = [i]
        for j, y in enumerate(b, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j-1] + (x != y)))
        previous = current
    return previous[-1]

def reference_metrics(prediction, references):
    p = normalize_metric(prediction)
    refs = [normalize_metric(r) for r in references]
    if not refs:
        return {'cer': None, 'wer': None, 'exact_match': None}
    return {'cer': min(distance(p, r) / max(1, len(r)) for r in refs),
            'wer': min(distance(p.split(), r.split()) / max(1, len(r.split())) for r in refs),
            'exact_match': float(p in refs)}
