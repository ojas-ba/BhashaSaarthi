"""Session-only Streamlit interface. No input is written to logs or disk."""
from dotenv import load_dotenv
load_dotenv()
import json
import platform
import importlib.util
import psutil
import requests
import streamlit as st
from src.config import Settings
from src.models.adapters import get_models
from src.pipeline import Pipeline

st.set_page_config(page_title='Hinglish Smart Writing Assistant', page_icon='✍️', layout='wide')
st.markdown('''<style>
.stApp {background: #f8faf9;} h1,h2,h3 {color:#133e38;}
textarea {font-family:'Nirmala UI','Mangal',sans-serif!important;font-size:18px!important;line-height:1.7!important;}
code {font-family:'Nirmala UI','Mangal',monospace!important;}
.block-container {padding-top:2.5rem;max-width:1320px;}
</style>''', unsafe_allow_html=True)
st.caption('CS3235 · UNDERGRADUATE LLM PROJECT')
st.title('Hinglish Smart Writing Assistant')
st.write('Turn Roman Hindi into Devanagari, refine your phrasing, and translate Hindi into English.')
settings = Settings()

@st.cache_resource
def resources(settings):
    xlit, param, trans, pool = get_models(settings)
    return Pipeline(settings, xlit, param, trans), pool

pipeline, pool = resources(settings)
for key, default in [('text', ''), ('history', []), ('result', None), ('fingerprint', None)]:
    if key not in st.session_state:
        st.session_state[key] = default

with st.sidebar:
    st.header('Writing preferences')
    style = st.selectbox('Output style', ['Natural Hinglish', 'Natural Hindi'])
    tone = st.selectbox('Phrasing tone', ['Minimal correction', 'Formal', 'Casual'])
    contextual = st.checkbox('Use Param1 for contextual conversion', value=True)
    source_label = st.radio('Translate this result', ['Script-converted result', 'Improved result'])
    source = 'converted' if source_label == 'Script-converted result' else 'improved'
    terms = st.text_input('Protect additional names / terms', placeholder='नाम, organization, custom term', help='Comma-separated exact text. Capitalized Latin words, acronyms, digits, links, email and inline/fenced code are detected automatically. Lowercase and Hindi names need explicit protection.')
    st.divider()
    st.subheader('Runtime readiness')
    st.write(f'{platform.system()} · Python {platform.python_version()}')
    st.write(f'Device configured: {settings.device} · {settings.precision}')
    st.write(f'Available RAM: {psutil.virtual_memory().available / 1024**3:.1f} GB')
    st.caption('Configured models are not necessarily loaded. Successful calls appear in Processing details.')
    st.write('IndicXlit: separate worker required')
    if st.button('Check worker connection'):
        try:
            response = requests.get(settings.xlit_url, timeout=(2, 4))
            response.raise_for_status()
            health = response.json()
            if health.get('ready') is not True or health.get('model') != 'IndicXlit-v1.0':
                raise ValueError('Unexpected worker readiness response')
            st.session_state.worker_health = health
        except Exception as exc:
            st.session_state.worker_health = {'error':str(exc)}
    if health := st.session_state.get('worker_health'):
        if health.get('ready'):
            st.success('IndicXlit weights loaded · worker ready')
            st.caption(f'Worker startup: {health.get("startup_seconds_including_download", "not reported")} seconds (includes any download).')
        else:
            st.error('Worker unavailable: ' + health['error'])
    st.write('Param1: ' + ('resident' if pool.key == 'param' else 'not loaded'))
    param_guard_gib = 13 if settings.precision == 'float32' else 7
    if pool.key != 'param' and psutil.virtual_memory().available / 1024**3 < param_guard_gib:
        st.caption(f'Phrasing unavailable at current free RAM. Param1 allocation guard: {param_guard_gib} GiB available; quantization is not configured.')
    st.write('IndicTrans2: ' + ('local WSL worker configured' if settings.trans_url else ('resident' if pool.key == 'trans' else 'not loaded; model access required')))
    if settings.trans_url and st.button('Check translation worker'):
        try:
            response = requests.get(settings.trans_url, timeout=(2, 4))
            response.raise_for_status()
            health = response.json()
            if health.get('ready') is not True or health.get('model') != settings.trans_model or health.get('revision') != settings.trans_revision:
                raise ValueError('Worker is not ready with the configured checkpoint')
            st.success('IndicTrans2 weights loaded · translator ready')
        except Exception as exc:
            st.error('Translation worker unavailable. Start scripts/setup_translation.sh in WSL. ' + str(exc))
    st.write('Remote code: ' + ('enabled' if settings.remote_code else 'disabled'))
    st.caption('Recent results remain in this browser session only. Clear removes session results. Model libraries may download weights to their external caches.')

examples = ['mujhe kal college jana hai', 'kal meeting hai please time pe aana', 'maine assignment submit nahi kiya', 'sir mujhe deadline extend karwani hai', 'Naman ne 12 November ko report bheji thi', 'Please email mujhe test@example.com par bhejna']
example = st.selectbox('Try an example', ['Choose an input…'] + examples)
def use_example():
    if example in examples:
        st.session_state.text = example
def clear():
    st.session_state.update(text='', history=[], result=None, fingerprint=None)
e1, e2, _ = st.columns([1, 1, 5])
e1.button('Use example', on_click=use_example)
e2.button('Clear / reset', on_click=clear)
left, right = st.columns(2, gap='large')
with left:
    st.subheader('Your words')
    text = st.text_area('Roman Hinglish, mixed script, or Hindi', key='text', height=270, max_chars=settings.max_chars)
    st.caption(f'{len(text)} / {settings.max_chars} characters · Input is treated as content to edit.')
    a, b = st.columns(2)
    c, d = st.columns(2)
    action = None
    if a.button('Convert to Hindi script', use_container_width=True): action = 'convert'
    if b.button('Improve phrasing', use_container_width=True): action = 'improve'
    if c.button('Translate to English', use_container_width=True): action = 'translate'
    if d.button('Run full pipeline', type='primary', use_container_width=True): action = 'full'
    st.caption('Improve edits the input independently. Translate uses the selected result, or Hindi input if no result exists.')

fingerprint = (text, style, tone, contextual, terms)
if action:
    previous = st.session_state.result if st.session_state.fingerprint == fingerprint else None
    try:
        with st.spinner('Running requested model stages… First loads can take several minutes.'):
            result = pipeline.run(text, action, style, tone, contextual, source,
                converted=previous.converted if previous else '', improved=previous.improved if previous else '',
                protected_terms=[x.strip() for x in terms.split(',') if x.strip()])
        st.session_state.result = result
        st.session_state.fingerprint = fingerprint
        st.session_state.history = [result.to_dict()] + st.session_state.history[:4]
    except ValueError as exc:
        st.error(str(exc))

with right:
    st.subheader('A clearer expression')
    result = st.session_state.result
    if result:
        if result.basic_only:
            st.warning('Basic transliteration only. Contextual mixed-language conversion has not completed.')
        for error in result.errors:
            st.error(error)
        tabs = st.tabs(['Hindi script', 'Improved', 'English', 'Original'])
        for tab, value in zip(tabs, [result.converted, result.improved, result.english, result.original]):
            with tab:
                if value:
                    st.code(value, language=None)  # Native display includes a copy button.
                else:
                    st.info('This stage has not produced a result.')
        st.download_button('Download UTF-8 text', '\n\n'.join(f'{key}\n{getattr(result, key)}' for key in ['original','converted','improved','english']).encode('utf-8'), 'hinglish-result.txt', 'text/plain; charset=utf-8')
        st.download_button('Download structured JSON', json.dumps(result.to_dict(), ensure_ascii=False, indent=2).encode('utf-8'), 'hinglish-result.json', 'application/json')
    else:
        st.info('Your results will appear here. Choose one action or run the complete pipeline.')
        st.markdown('**Natural Hinglish** retains clear English words. **Natural Hindi** asks Param1 for a fluent Hindi rendering; it includes contextual rewriting and translation.')

if result:
    with st.expander('Processing details · models, candidates, timing & validation'):
        st.json(result.to_dict())
        st.write('Latest cold model load seconds:', pool.loads)
        for warning in result.warnings:
            st.warning(warning)
with st.expander('Recent results · this session only'):
    for i, item in enumerate(st.session_state.history):
        st.write(f'{i + 1}. {item["original"][:100]}')
        st.code(item.get('english') or item.get('improved') or item.get('converted') or 'No output', language=None)
