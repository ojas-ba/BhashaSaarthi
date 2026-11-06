"""Execute the real Streamlit script; do not pretend this exercises model quality."""
from streamlit.testing.v1 import AppTest

def test_ui_initial_render_and_empty_input():
    app = AppTest.from_file('app.py').run(timeout=60)
    assert not app.exception
    assert app.title[0].value == 'Hinglish Smart Writing Assistant'
    next(b for b in app.button if b.label == 'Convert to Hindi script').click().run(timeout=60)
    assert any('Enter some text' in e.value for e in app.error)

def test_ui_devanagari_basic_and_reset():
    app = AppTest.from_file('app.py').run(timeout=60)
    app.checkbox[0].uncheck()
    app.text_area[0].set_value('मुझे घर जाना है।')
    next(b for b in app.button if b.label == 'Convert to Hindi script').click().run(timeout=60)
    assert not app.exception
    assert app.session_state['result'].converted == 'मुझे घर जाना है।'
    next(b for b in app.button if b.label == 'Clear / reset').click().run(timeout=60)
    assert app.session_state['result'] is None
    assert app.text_area[0].value == ''
