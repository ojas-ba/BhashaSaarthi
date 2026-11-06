import re
from collections import Counter

def numbers(text):
    return Counter(re.findall(r'\d+(?:[/:.,-]\d+)*', text))

def validate(original, output, spans=(), target='hi'):
    errors = []
    if not output.strip():
        errors.append('Empty model output.')
    if len(output) > max(150, len(original) * 3):
        errors.append('Unexpected output expansion.')
    if numbers(original) != numbers(output):
        errors.append('Numbers changed.')
    for value in set(spans):
        if output.count(value) < original.count(value):
            errors.append(f'Protected content missing: {value}')
    expects_hindi = re.search(r'[\u0900-\u097f]|\b(?:mujhe|muje|mujhey|jana|nahi|nahin|chahiye)\b', original, re.I)
    if target == 'hi' and expects_hindi and not re.search(r'[\u0900-\u097f]', output):
        errors.append('Expected Hindi script missing.')
    if target == 'en' and re.search(r'[\u0900-\u097f]', output):
        errors.append('Hindi script remains in English translation.')
    # Conservative warning: cross-lingual negation/tense equivalence still needs human review.
    neg = r'\b(?:nahi|nahin|mat|never|not)\b|नहीं|मत\b'
    if re.search(neg, original, re.I) and not re.search(neg + r"|\bno\b|n't", output, re.I):
        errors.append('Possible negation loss.')
    return errors
