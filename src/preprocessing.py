"""Conservative normalization and exact restoration of immutable user spans."""
import re
import unicodedata
from dataclasses import dataclass

PATTERN = re.compile(r'```[\s\S]*?```|`[^`\n]+`|https?://[^\s<>]+|[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}|#[\w\u0900-\u097f]+|\b\d+(?:[/:.,-]\d+)*\b|\b[A-Z][A-Z0-9]{1,}\b|\b[A-Z][a-z]+\b')

def normalize(text):
    return unicodedata.normalize('NFC', text.replace('\r\n', '\n').replace('\r', '\n'))

@dataclass
class Protected:
    text: str
    spans: dict

    def restore(self, output):
        for key, value in self.spans.items():
            if output.count(key) != 1:
                raise ValueError(f'Protected marker {key} missing or duplicated; output rejected.')
            output = output.replace(key, value)
        if re.search(r'ZXQ\d+QXZ', output):
            raise ValueError('Unexpected protected marker; output rejected.')
        return output

def protect(text, extra=()):
    if re.search(r'ZXQ\d+QXZ', text):
        raise ValueError('Reserved marker syntax in input. Remove ZXQ…QXZ markers.')
    ranges = [(m.start(), m.end()) for m in PATTERN.finditer(text)]
    for value in extra:
        if value:
            ranges.extend((m.start(), m.end()) for m in re.finditer(re.escape(value), text))
    merged = []
    for start, end in sorted(ranges):
        if merged and start < merged[-1][1]:
            merged[-1] = (merged[-1][0], max(end, merged[-1][1]))
        else:
            merged.append((start, end))
    spans, output, previous = {}, [], 0
    for i, (start, end) in enumerate(merged):
        key = f'ZXQ{i}QXZ'
        spans[key] = text[start:end]
        output.extend([text[previous:start], key])
        previous = end
    output.append(text[previous:])
    return Protected(''.join(output), spans)

def roman_tokens(text):
    return list(dict.fromkeys(m.group() for m in re.finditer(r'ZXQ\d+QXZ|[A-Za-z]+(?:\x27[A-Za-z]+)?', text) if not m.group().startswith('ZXQ')))
