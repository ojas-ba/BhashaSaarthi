"""Fetch public metadata and remote Python source for review; never downloads weights."""
import hashlib
import json
import platform
import os
import urllib.request
from pathlib import Path
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

MODELS = ['bharatgenai/Param-1-2.9B-Instruct', 'ai4bharat/indictrans2-indic-en-dist-200M']

def fetch(url):
    headers = {}
    if os.getenv('HF_TOKEN') and url.startswith('https://huggingface.co/'):
        headers['Authorization'] = 'Bearer ' + os.environ['HF_TOKEN']
    with urllib.request.urlopen(urllib.request.Request(url, headers=headers), timeout=40) as response:
        return response.read()

if __name__ == '__main__':
    report = {'python': platform.python_version(), 'os': platform.platform(), 'models': []}
    for model in MODELS:
        try:
            info = json.loads(fetch('https://huggingface.co/api/models/' + model))
        except Exception as exc:
            report['models'].append({'id': model, 'error': str(exc)})
            continue
        entry = {k: info.get(k) for k in ('id', 'sha', 'gated', 'cardData')}
        entry['files'] = [x['rfilename'] for x in info['siblings']]
        entry['review_sources'] = {}
        for filename in entry['files']:
            if filename.endswith('.py') or filename in ('config.json', 'LICENSE', 'requirements.txt'):
                try:
                    body = fetch(f'https://huggingface.co/{model}/resolve/{info["sha"]}/{filename}')
                except Exception as exc:
                    entry['review_sources'][filename] = {'error': str(exc)}
                    continue
                target = Path('reports/model_sources') / model.split('/')[1] / filename
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(body)
                entry['review_sources'][filename] = hashlib.sha256(body).hexdigest()
        report['models'].append(entry)
    try:
        data = json.loads(fetch('https://huggingface.co/api/datasets/ai4bharat/Aksharantar'))
        report['aksharantar'] = {k: data.get(k) for k in ('id','sha','gated','cardData','siblings')}
    except Exception as exc:
        report['aksharantar'] = {'error': str(exc)}
    Path('reports/model_metadata.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))
