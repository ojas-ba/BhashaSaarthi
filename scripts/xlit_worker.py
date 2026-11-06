"""Isolated legacy IndicXlit process; run with the requirements-xlit environment."""
import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer
from time import perf_counter
from pathlib import Path
import importlib.util
import importlib.metadata
import hashlib
import urllib.request
import zipfile
import logging

def load_direct_engine():
    """Use upstream's unmodified Fairseq class, bypassing unrelated Urdu imports."""
    import torch
    torch.set_num_threads(int(os.getenv('TORCH_NUM_THREADS', '4')))
    package = importlib.metadata.distribution('ai4bharat-transliteration')
    source = package.locate_file('ai4bharat/transliteration/transformer/custom_interactive.py')
    spec = importlib.util.spec_from_file_location('indicxlit_official_interactive', source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    logging.getLogger('fairseq').setLevel(logging.WARNING)
    cache = Path(os.getenv('XLIT_CACHE', str(Path.home() / '.cache' / 'hinglish-indicxlit-v1')))
    cache.mkdir(parents=True, exist_ok=True)
    checkpoint = cache / 'transformer/indicxlit.pt'
    archive = cache / 'indicxlit-en-indic-v1.0.zip'
    if not checkpoint.exists():
        url = 'https://github.com/AI4Bharat/IndicXlit/releases/download/v1.0/indicxlit-en-indic-v1.0.zip'
        print('Downloading official IndicXlit v1.0 weights…', flush=True)
        with urllib.request.urlopen(url, timeout=120) as response, archive.open('wb') as target:
            import shutil
            shutil.copyfileobj(response, target)
        digest = hashlib.sha256(archive.read_bytes()).hexdigest()
        (cache / 'archive.sha256').write_text(digest + '\n', encoding='ascii')
        with zipfile.ZipFile(archive) as z:
            for member in z.infolist():
                target = (cache / member.filename).resolve()
                if not target.is_relative_to(cache.resolve()):
                    raise ValueError('Unsafe archive path')
            z.extractall(cache)
    lang_file = package.locate_file('ai4bharat/transliteration/transformer/models/en2indic/lang_list.txt')
    languages = [line.strip() for line in lang_file.read_text().splitlines() if line.strip() and line.strip() != 'en']
    neural = module.Transliterator(str(cache / 'corpus-bin'), str(checkpoint), ','.join('en-' + lang for lang in languages), str(lang_file), beam=10, batch_size=32)
    for model in neural.models:
        model.eval()

    class Engine:
        def translit_word(self, word, topk=5):
            import torch
            # Exactly the upstream Roman-to-Hindi character/token preprocessing.
            source = '__hi__ ' + ' '.join(word.lower())
            with torch.inference_mode():
                result = neural.translate([source], nbest=topk)
            candidates = [line.split('\t', 2)[2].replace(' ', '') for line in result.splitlines() if line.startswith('H-')]
            if not candidates:
                raise RuntimeError('IndicXlit returned no candidates')
            return {'hi': candidates}
    return Engine()

def main():
    start = perf_counter()
    engine = load_direct_engine()
    startup_seconds = perf_counter() - start
    print(f'IndicXlit loaded in {startup_seconds:.3f}s (includes download if needed)', flush=True)

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass  # Do not log user text.

        def do_GET(self):
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({'ready':True, 'model':'IndicXlit-v1.0', 'startup_seconds_including_download':startup_seconds}).encode())

        def do_POST(self):
            try:
                if self.path != '/candidates':
                    raise ValueError('Unknown route')
                size = int(self.headers.get('Content-Length', 0))
                if not 0 < size <= 16000:
                    raise ValueError('Invalid request size')
                words = json.loads(self.rfile.read(size))['words']
                if not isinstance(words, list) or len(words) > 300 or not all(isinstance(w, str) and w.isascii() and w.replace("'", '').isalpha() and len(w) <= 80 for w in words):
                    raise ValueError('Expected at most 300 short Roman words')
                result = {word: engine.translit_word(word.lower(), topk=5)['hi'] for word in words}
                self.send_response(200)
            except Exception as exc:
                result = {'error': str(exc)}
                self.send_response(400)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))

    HTTPServer(('127.0.0.1', int(os.getenv('XLIT_PORT', '8765'))), Handler).serve_forever()

if __name__ == '__main__':
    main()
