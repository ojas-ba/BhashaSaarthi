"""Representative real-adapter attempts. Public inputs only; no test doubles."""
import json
import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
from src.config import Settings
from src.models.adapters import get_models
from src.pipeline import Pipeline

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    settings = Settings()
    xlit, param, trans, pool = get_models(settings)
    pipeline = Pipeline(settings, xlit, param, trans)
    cases = [
        ('straightforward', 'mujhe ghar jana hai', {'contextual':False}),
        ('mixed', 'kal meeting hai please time pe aana', {'contextual':True}),
        ('negation', 'maine assignment submit nahi kiya', {'contextual':False}),
        ('formal', 'मुझे कल कॉलेज जाना है', {'action':'improve','tone':'Formal'}),
        ('translation', 'मुझे घर जाना है।', {'action':'translate'}),
        ('names_numbers', 'Naman ne 12 November ko report bheji thi', {'contextual':False}),
        ('ambiguous', 'kal', {'contextual':False}),
        ('email', 'Please email mujhe test@example.com par bhejna', {'contextual':False}),
    ]
    results = [{'category':category,'result':pipeline.run(text, **options).to_dict()} for category,text,options in cases]
    Path('reports/end_to_end_examples.json').write_text(json.dumps(results,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps([{'category':row['category'],'models_used':row['result']['models_used'],'errors':row['result']['errors']} for row in results],ensure_ascii=False,indent=2))

if __name__ == '__main__': main()
