"""Record public-example translation using the real local model, never doubles."""
import json
import sys
from pathlib import Path
from time import perf_counter
import requests
from dotenv import load_dotenv
load_dotenv()
from src.config import Settings
from src.models.adapters import get_models
from src.pipeline import Pipeline

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    settings = Settings()
    response = requests.get(settings.trans_url, timeout=10)
    response.raise_for_status()
    health = response.json()
    xlit, param, trans, pool = get_models(settings)
    pipeline = Pipeline(settings, xlit, param, trans)
    cases = ['मुझे घर जाना है।','मैंने अपना असाइनमेंट जमा नहीं किया है।','कृपया समय पर आना।','Naman ने 12 November को रिपोर्ट भेजी थी।','`print(12)` को मत बदलना।']
    rows = []
    for text in cases:
        start = perf_counter()
        result = pipeline.run(text, action='translate')
        rows.append({'input':text,'result':result.to_dict(),'seconds':perf_counter()-start})
        print(json.dumps({'input':text,'english':result.english,'errors':result.errors,'validation_failures':result.validation_failures},ensure_ascii=False))
    report = {'date':'2026-11-06','worker':health,'cases':rows,'note':'Real pretrained model output. Public examples only; semantic adequacy has not been human-reviewed.'}
    if '--ui' in sys.argv:
        from streamlit.testing.v1 import AppTest
        app = AppTest.from_file('app.py').run(timeout=60)
        app.text_area[0].set_value(cases[0])
        next(b for b in app.button if b.label == 'Translate to English').click().run(timeout=180)
        assert not app.exception
        ui_result = app.session_state['result']
        assert ui_result.english and not ui_result.errors and not ui_result.validation_failures
        report['ui_check'] = {'passed':True, 'result':ui_result.to_dict()}
    Path('reports/translation_worker_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    if any(row['result']['errors'] for row in rows):
        raise SystemExit('One or more translation calls failed; see saved report.')

if __name__ == '__main__': main()
