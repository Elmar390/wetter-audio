#!/usr/bin/env python3
# scripts/generate_tts.py
import os, requests, sys
from bs4 import BeautifulSoup
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

# Konfiguration (kann bleiben)
SRC_URL = "https://wetter.provinz.bz.it/"
OUT_PATH = "docs/wetter.mp3"
OPENAI_KEY = os.environ.get("OPENAI_API_KEY")
ELEVEN_KEY = os.environ.get("ELEVENLABS_API_KEY")
# Beispiel-voice_id — du kannst später mit ElevenLabs GET /v1/voices andere Stimmen wählen
VOICE_ID = "pNInz6obpgDQGcFmaJgB"  

if not OPENAI_KEY or not ELEVEN_KEY:
    print("ERROR: OPENAI_API_KEY and ELEVENLABS_API_KEY must be set in environment")
    sys.exit(2)

def fetch_weather_text(url):
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    # Suche Überschrift "Das Wetter heute"
    header = soup.find(lambda tag: tag.name in ["h1","h2","h3","h4"] and "Das Wetter heute" in tag.get_text())
    if header:
        # nächstes <p> Element holen
        p = header.find_next_sibling()
        # Schleife, bis wir ein Tag mit Text finden
        while p and (getattr(p,'get_text', lambda **k: "")().strip() == ""):
            p = p.find_next_sibling()
        if p:
            return p.get_text(separator=" ", strip=True)
    # Fallback: suche Textblock im Gesamttext
    full = soup.get_text(separator="\n")
    idx = full.find("Das Wetter heute")
    if idx != -1:
        snippet = full[idx: idx+2000]
        lines = [l.strip() for l in snippet.splitlines() if l.strip()]
        if len(lines) >= 2:
            return " ".join(lines[1:4])
    return None

def summarize_with_openai(text):
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {OPENAI_KEY}", "Content-Type": "application/json"}
    prompt_system = ("Du bist ein Assistent, der kurze, natürlich klingende Wetteransagen auf Deutsch formuliert. "
                     "Gib eine prägnante, gesprochene Version (1-2 Sätze), freundlich, geeignet für Audio.")
    data = {
        "model": "gpt-3.5-turbo",
        "messages": [
            {"role":"system","content": prompt_system},
            {"role":"user","content": text}
        ],
        "max_tokens": 120,
        "temperature": 0.25
    }
    resp = requests.post(url, headers=headers, json=data, timeout=20)
    resp.raise_for_status()
    j = resp.json()
    return j["choices"][0]["message"]["content"].strip()

def tts_elevenlabs(text, out_path):
    eleven = ElevenLabs(api_key=ELEVEN_KEY)
    # convert liefert Chunk-Iterator — wir schreiben in Datei
    response = eleven.text_to_speech.convert(
        voice_id=VOICE_ID,
        output_format="mp3_22050_32",
        text=text,
        model_id="eleven_multilingual_v2"
    )
    with open(out_path, "wb") as f:
        for chunk in response:
            if chunk:
                f.write(chunk)
    print("Saved:", out_path)

def main():
    print("Fetching weather text...")
    txt = fetch_weather_text(SRC_URL)
    if not txt:
        print("Kein Wettertext gefunden.")
        sys.exit(0)
    print("Original text:", txt[:200])
    print("Summarizing with OpenAI...")
    summary = summarize_with_openai(txt)
    print("Summary:", summary)
    print("Generating TTS with ElevenLabs...")
    os.makedirs(os.path.dirname(OUT_PATH) or ".", exist_ok=True)
    tts_elevenlabs(summary, OUT_PATH)
    print("Done.")

if __name__ == "__main__":
    main()

