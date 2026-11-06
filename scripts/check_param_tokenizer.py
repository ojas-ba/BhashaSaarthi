"""Real checkpoint tokenizer and source-class checks, not pretrained inference."""
import json
import sys
from pathlib import Path
import time

def main():
    sys.stdout.reconfigure(encoding='utf-8')
    report = {'pretrained_weights_loaded':False}
    start = time.perf_counter()
    try:
        from transformers import AutoTokenizer
        model = 'bharatgenai/Param-1-2.9B-Instruct'
        revision = 'f9b32a727458727ff515fea5d82df00ae9b7ad56'
        tokenizer = AutoTokenizer.from_pretrained(model, revision=revision, trust_remote_code=False)
        ids = tokenizer.apply_chat_template([{'role':'system','content':'Edit Hindi without changing meaning.'},{'role':'user','content':'मुझे घर जाना है।'}], add_generation_prompt=True)
        report.update(tokenizer_loaded=True, chat_template_token_count=len(ids), eos_token_id=tokenizer.eos_token_id)
    except Exception as exc:
        report.update(tokenizer_loaded=False, error=f'{type(exc).__name__}: {exc}')
    report['seconds'] = time.perf_counter() - start
    Path('reports/param_tokenizer_check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__ == '__main__': main()
