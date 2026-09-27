"""Comparação controlada dos motores existentes. Base não modificada."""
from pathlib import Path
import io
import json
import time
import urllib.request
import urllib.parse
import wave

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'audios'
OUT.mkdir(parents=True, exist_ok=True)
TEXT = 'Hoje eu vou mostrar como transformar uma ideia em um projeto de verdade. Sem complicar, sem pular etapas. Primeiro a gente testa, depois compara e só então escolhe o que funciona melhor.'
CASES = [
    ('omni_anterior_broadcast', 'omnivoice', {'effect_preset': 'broadcast', 'num_step': 32}),
    ('omni_natural_32', 'omnivoice', {'effect_preset': 'raw', 'num_step': 32, 'denoise': 'false', 'postprocess_output': 'false'}),
    ('omni_natural_64', 'omnivoice', {'effect_preset': 'raw', 'num_step': 64, 'denoise': 'false', 'postprocess_output': 'false', 'position_temperature': 3.0}),
    ('voxcpm_natural', 'voxcpm2', {'effect_preset': 'raw', 'denoise': 'false', 'postprocess_output': 'false'}),
]
report = {'texto': TEXT, 'perfil_base': '165a614c', 'referencia': 'Gabriel original 12.9s, consentimento registrado', 'seed': 2026, 'resultados': [], 'limite': 'Não mede nem afirma equivalência perceptiva ao ElevenLabs.'}
for label, engine, settings in CASES:
    payload = {'text': TEXT, 'engine': engine, 'profile_id': '165a614c', 'language': 'pt', 'speed': 1, 'seed': 2026, 'stream': 'false', **settings}
    start = time.perf_counter()
    try:
        request = urllib.request.Request('http://127.0.0.1:3900/generate', data=urllib.parse.urlencode(payload).encode(), method='POST')
        with urllib.request.urlopen(request, timeout=360) as response:
            audio = response.read()
        elapsed = time.perf_counter() - start
        with wave.open(io.BytesIO(audio)) as wav:
            duration = wav.getnframes() / wav.getframerate()
            rate = wav.getframerate()
        path = OUT / f'{label}.wav'
        path.write_bytes(audio)
        result = {'caso': label, 'arquivo': str(path), 'segundos_geracao': elapsed, 'duracao_audio': duration, 'taxa': rate, 'rtf': elapsed / duration, 'pedido': payload}
    except Exception as exc:
        result = {'caso': label, 'erro': str(exc), 'segundos': time.perf_counter() - start}
    report['resultados'].append(result)
    (ROOT / 'benchmark.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(result, ensure_ascii=False), flush=True)
