"""Real-model Streamlit script check; requires the loaded local IndicXlit worker."""
import json
from pathlib import Path
from streamlit.testing.v1 import AppTest

def main():
    app = AppTest.from_file('app.py').run(timeout=60)
    next(b for b in app.button if b.label == 'Check worker connection').click().run(timeout=60)
    assert app.session_state['worker_health']['ready'] is True
    app.checkbox[0].uncheck()
    app.text_area[0].set_value('mujhe ghar jana hai')
    next(b for b in app.button if b.label == 'Convert to Hindi script').click().run(timeout=120)
    assert not app.exception
    result = app.session_state['result']
    assert not result.errors and result.converted == 'मुझे घर जाना है'
    assert any('IndicXlit' in name for name in result.models_used)
    Path('reports/live_ui_check.json').write_text(json.dumps({'check':'Streamlit AppTest with real local IndicXlit (no test doubles)','passed':True,'worker_readiness':app.session_state['worker_health'],'result':result.to_dict()},ensure_ascii=False,indent=2),encoding='utf-8')
    print('Real IndicXlit UI action passed.')

if __name__ == '__main__': main()
