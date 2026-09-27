"""Audita integridade de texto com distância de edição, não palavras presentes."""
from pathlib import Path
import json
import re
import unicodedata
import httpx

ROOT = Path(__file__).resolve().parent

def tokens(text):
    text = ''.join(c for c in unicodedata.normalize('NFKD', text.lower()) if not unicodedata.combining(c))
    return re.findall(r'\w+', text)

def distance(a, b):
    last = list(range(len(b)+1))
    for i, x in enumerate(a, 1):
        row = [i]
        for j, y in enumerate(b, 1):
            row.append(min(row[-1]+1, last[j]+1, last[j-1]+(x != y)))
        last = row
    return last[-1]

if __name__ == '__main__':
    report = json.loads((ROOT/'benchmark.json').read_text(encoding='utf-8'))
    target = tokens(report['texto'])
    for item in report['resultados']:
        if 'arquivo' not in item:
            continue
        try:
            with Path(item['arquivo']).open('rb') as audio:
                response = httpx.post('http://127.0.0.1:3900/transcribe', files={'audio': (Path(item['arquivo']).name, audio, 'audio/wav')}, data={'language': 'pt', 'mode': 'reference', 'refine': 'false'}, timeout=240)
                response.raise_for_status()
            result = response.json()
            item['transcricao'] = result['text']
            item['motor_asr'] = result.get('engine')
            item['wer_normalizado'] = distance(target, tokens(result['text'])) / len(target)
        except Exception as error:
            item['erro_asr'] = str(error)
        (ROOT/'avaliacao-texto.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps(item,ensure_ascii=False),flush=True)
