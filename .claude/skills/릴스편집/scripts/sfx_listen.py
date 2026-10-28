#!/usr/bin/env python3
"""효과음 듣고 이름 붙이기 — CapCut 효과음 이름이 외국어·모호할 때 쓴다.

사용법: sfx_listen.py <palette_raw.json> <출력.json>
- palette_raw.json: 0_설치.md (2)에서 만든 목록(no, name, copy, volume, dur …)
- 각 파일을 ffmpeg로 재고(길이·최고 음량·소리가 가장 커지는 시점·밝기),
 Gemini에게 소리 파일을 직접 들려 한국어 이름·묘사·릴스 용도를 받는다.
- Gemini 키는 ~/.config/watch/.env 의 GEMINI_API_KEY (명령줄·파일에 키를 쓰지 않음)
"""
import base64
import json
import os
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

MODEL = os.environ.get("SFX_GEMINI_MODEL", "gemini-3.7-flash")


def key():
    for line in (Path.home() / ".config/watch/.env").read_text().splitlines():
        if line.startswith("GEMINI_API_KEY="):
            return line.split("=", 1)[1].strip().strip('"')
    sys.exit("GEMINI_API_KEY 없음")


def measure(path):
    p = subprocess.run(["ffmpeg", "-nostats", "-i", path, "-af",
                        "astats=metadata=1:reset=0,aspectralstats=measure=centroid,ametadata=print:file=-",
                        "-f", "null", "-"], capture_output=True, text=True)
    peak = re.findall(r"Peak level dB:\s*(-?[\d.]+)", p.stderr)
    cents = [float(x) for x in re.findall(r"centroid=([\d.]+)", p.stdout)]
 # 소리가 가장 커지는 시점(20ms 창)
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", path, "-ac", "1", "-ar", "8000",
                          "-f", "s16le", "-"], capture_output=True).stdout
    import array
    a = array.array("h"); a.frombytes(raw[: len(raw) // 2 * 2])
    n = 160
    env = [max((abs(x) for x in a[i:i + n]), default=0) for i in range(0, len(a), n)]
    top = env.index(max(env)) * 0.02 if env else 0
    return {
        "peak_db": float(peak[-1]) if peak else None,
        "loudest_at": round(top, 2),
        "brightness_hz": round(sum(cents) / len(cents)) if cents else None,
    }


def ask_gemini(rows):
    parts = [{"text": (
        "아래는 릴스 편집용 효과음 파일들이다. 순서대로 번호가 붙어 있다. 각 소리를 직접 듣고 "
        "JSON 배열만 출력해라. 항목: no, ko_name(어떤 소리인지 바로 아는 한국어 2~6자, 예: 휙_빠른, 띠링_알림), "
        "sounds_like(들리는 그대로 한 문장), mood(느낌 한두 단어), use_when(릴스에서 쓰기 좋은 순간 한 문장, "
        "예: 자료화면이 들어올 때, 숫자를 말할 때, 반전·펀치라인, 화면 클릭 시연), avoid(어울리지 않는 상황 한 구절). "
        "원래 이름은 참고만 하고 소리를 기준으로 판단해라."
    )}]
    for r in rows:
        mime = "audio/mpeg" if r["copy"].endswith(".mp3") else "audio/wav"
        parts.append({"text": f"[{r['no']}] 원래 이름: {r['name']}"})
        parts.append({"inline_data": {"mime_type": mime,
                                      "data": base64.b64encode(open(r["copy"], "rb").read()).decode()}})
    body = json.dumps({"contents": [{"parts": parts}],
                       "generationConfig": {"responseMimeType": "application/json"}}).encode()
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
        data=body, headers={"x-goog-api-key": key(), "Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        out = json.load(r)
    return json.loads(out["candidates"][0]["content"]["parts"][0]["text"])


def main():
    rows = json.load(open(sys.argv[1], encoding="utf-8"))
    rows = [r for r in rows if r.get("copy")]
    for r in rows:
        r.update(measure(r["copy"]))
    heard = {h["no"]: h for h in ask_gemini(rows)}
    for r in rows:
        r.update({k: v for k, v in heard.get(r["no"], {}).items() if k != "no"})
    json.dump(rows, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for r in rows:
        print(r["no"], r.get("ko_name"), "|", r.get("use_when"))


if __name__ == "__main__":
    main()
