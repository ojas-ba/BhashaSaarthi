"""Record real adapter calls, resource failures and hardware without test doubles."""
import json
import platform
import time
import sys
from pathlib import Path
import psutil
from dotenv import load_dotenv
load_dotenv()
from src.config import Settings
from src.models.adapters import get_models

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    settings = Settings()
    xlit, param, trans, pool = get_models(settings)
    report = {'date':'2026-11-05', 'hardware':{'platform':platform.platform(), 'python':platform.python_version(), 'ram_bytes':psutil.virtual_memory().total,'available_ram_bytes':psutil.virtual_memory().available},'calls':[]}
    tasks = [('IndicXlit', lambda: xlit.candidates(['mujhe','nahi','jana'])),('Param1',lambda: param.rewrite('मुझे कल कॉलेज जाना है','मुझे कल कॉलेज जाना है','Apply minimal correction without changing modality.')),('IndicTrans2',lambda: trans.translate('मुझे घर जाना है।'))]
    for name, fn in tasks:
        start = time.perf_counter()
        try:
            output = fn()
            row = {'model':name,'status':'inference_completed','output':output}
        except Exception as exc:
            row = {'model':name,'status':'blocked','error':f'{type(exc).__name__}: {exc}'}
        row['elapsed_seconds'] = time.perf_counter() - start
        report['calls'].append(row)
    report['cold_load_seconds'] = pool.loads
    Path('reports/integration_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__ == '__main__': main()
