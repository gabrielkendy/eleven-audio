import json
from pathlib import Path
import httpx
import re
import unicodedata

def palavras(texto):
    normal = unicodedata.normalize('NFKD', texto.casefold())
    return re.findall(r'\w+', ''.join(c for c in normal if not unicodedata.combining(c)))

def distancia(a, b):
    row = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        new = [i]
        for j, y in enumerate(b, 1):
            new.append(min(new[-1] + 1, row[j] + 1, row[j-1] + (x != y)))
        row = new
    return row[-1]

root = Path(__file__).resolve().parents[2]
folder = root / 'saidas/audio/qualidade-v2'
manifest = json.loads((folder / 'manifesto.json').read_text('utf-8'))
referencia = palavras(manifest['texto'])
for item in manifest['amostras']:
    if not item['id'].startswith('chatterbox'): continue
    with (folder / (item['id'] + '.wav')).open('rb') as audio:
        r = httpx.post('http://127.0.0.1:3900/transcribe', data={'language':'pt','model':'large-v3'}, files={'audio':(item['id']+'.wav',audio,'audio/wav')}, timeout=300)
        r.raise_for_status()
        dado = r.json()
        texto = dado.get('text', dado.get('transcription',''))
        item['wer_percentual'] = round(distancia(referencia,palavras(texto))/len(referencia)*100,2)
        item['transcricao'] = texto
        print(json.dumps(item,ensure_ascii=False),flush=True)
(folder/'manifesto.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),'utf-8')
