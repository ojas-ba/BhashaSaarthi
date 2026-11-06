"""Local, real IndicTrans2 inference; token comes from ignored .env, never logs."""
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / '.env')
from src.config import Settings
from src.models.adapters import IndicTrans2, ModelPool

def main():
    import torch
    from IndicTransToolkit.processor import IndicProcessor
    torch.set_num_threads(4)
    settings = Settings()
    pool = ModelPool(settings)
    translator = IndicTrans2(settings, pool)
    pool.load('trans')
    # Construct preprocessing now, so readiness also verifies its dependencies.
    IndicProcessor(inference=True)
    identity = {'model':settings.trans_model, 'revision':settings.trans_revision}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args): pass
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-Type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(dict(identity, ready=True, cold_load_seconds=pool.loads)).encode())
        def do_POST(self):
            result = dict(identity)
            try:
                if self.path != '/translate': raise ValueError('Unknown route')
                size = int(self.headers.get('Content-Length', 0))
                if not 0 < size <= settings.max_chars * 8 + 1024: raise ValueError('Invalid request size')
                text = json.loads(self.rfile.read(size))['text']
                if not isinstance(text, str) or not text.strip() or len(text) > settings.max_chars: raise ValueError('Invalid text length')
                result['translation'] = translator.translate(text)
            except Exception as exc:
                result['error'] = f'{type(exc).__name__}: {exc}'
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(result, ensure_ascii=False).encode('utf-8'))
    print('IndicTrans2 ready at http://127.0.0.1:8766', flush=True)
    HTTPServer(('127.0.0.1', 8766), Handler).serve_forever()

if __name__ == '__main__': main()
