#!/usr/bin/env python3
"""AI 나레이션 — 사용자 본인 목소리 모델(Fish Audio)로 문장을 읽어 wav를 만든다.

사용법:
 narration.py say "<문장>" <out.wav> [--engine fish|say] [--voice <목소리 id>]
 문장 하나 → wav (48kHz·2채널·-14 LUFS 근처, 앞뒤 0.15초 여유. 편집본과 같은 규격)
 narration.py plan <결과폴더> [--engine fish|say]
 <결과폴더>/narration.json 의 항목마다 wav 를 만들고 길이(dur)·파일(wav)·단어 시간(words)을 채워 되쓴다.
 이미 같은 글·같은 엔진으로 만든 항목은 건너뛴다.

narration.json 형식 (AI 가 3단계 시작 질문 뒤에 쓴다):
 [{"id": "n1", "text": "읽을 문장", "after_sentence": 3, "mode": "hold" | "over"}, ...]
 - after_sentence: takes.json 문장 번호. 그 문장이 끝난 자리에 들어간다
 - mode: hold = 인물 영상을 그 자리에서 멈추고(정지 화면) 나레이션 길이만큼 기다린다(영상이 길어진다)
 over = 영상을 멈추지 않고 그 시점 위에 얹는다(그 구간에 원래 목소리가 없을 때만)
 - 채워지는 것: dur(초), wav(파일), words([{w, s, e}] — wav 안에서의 시간, 자막용), engine, text_done
 배치(타임라인 반영)는 narration_apply.py 가 한다.

엔진:
 fish (기본) — Fish Audio API. 키는 ~/.config/reels-edit/.env 의 FISH_API_KEY= 줄.
 목소리 id 는 환경.md 표의 `| [나레이션 목소리] | <id> |` 행, 없으면 같은 .env 의 FISH_VOICE_ID.
 키가 없으면 멈추고 안내한다(사용자 목소리가 아니면 의미가 없으므로 다른 엔진으로 바꾸지 않는다).
 say — 맥 기본 음성(시험용). 사용자 목소리가 아니다. 흐름을 시험할 때만 --engine say 로 쓴다.
키 값은 화면·로그에 찍지 않는다.
"""
import json
import os
import subprocess
import sys
import tempfile
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import platform_util as pu  # noqa: E402

ENV_FILE = os.path.expanduser("~/.config/reels-edit/.env")
FISH_URL = "https://api.fish.audio/v1/tts"
FISH_MODEL = "s2.1-pro"
PAD = 0.15  # 앞뒤 여유(초)


def read_env():
    out = {}
    if os.path.exists(ENV_FILE):
        for line in open(ENV_FILE, encoding="utf-8"):
            line = line.strip()
            if "=" in line and not line.startswith("#"):
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def fish_key():
    k = read_env().get("FISH_API_KEY") or os.environ.get("FISH_API_KEY")
    if not k:
        sys.exit("❌ Fish Audio 키가 없어요. 터미널에서 직접 한 줄로 넣어 주세요(채팅에 키를 붙이지 않게):\n"
                 "   mkdir -p ~/.config/reels-edit && chmod 700 ~/.config/reels-edit && "
                 "(umask 077; echo 'FISH_API_KEY=여기에키' >> ~/.config/reels-edit/.env)")
    return k


def voice_id(given=None):
    v = given or pu.env_value("[나레이션 목소리]") or read_env().get("FISH_VOICE_ID") or os.environ.get("FISH_VOICE_ID")
    if not v or v in ("(채울 것)", "미정", "없음"):
        sys.exit("❌ 나레이션 목소리 id 가 없어요. fish.audio 에서 본인 목소리 모델을 만들고, 그 id 를 환경.md 의 "
                 "`| [나레이션 목소리] | <id> |` 행에 적어 주세요.")
    return v


def synth_fish(text, raw_out, voice):
    body = json.dumps({"text": text, "reference_id": voice, "format": "wav", "sample_rate": 44100,
                       "latency": "normal", "chunk_length": 300, "language": "ko"}).encode("utf-8")
    req = urllib.request.Request(FISH_URL, data=body, method="POST", headers={
        "Authorization": f"Bearer {fish_key()}", "Content-Type": "application/json", "model": FISH_MODEL})
    try:
        with urllib.request.urlopen(req, timeout=120) as r, open(raw_out, "wb") as f:
            while True:
                chunk = r.read(65536)
                if not chunk:
                    break
                f.write(chunk)
    except urllib.error.HTTPError as e:
        msg = ""
        try:
            msg = json.loads(e.read().decode("utf-8", "replace")).get("message", "")
        except Exception:
            pass
        hint = {401: "키가 틀렸거나 만료됐어요", 402: "Fish Audio 크레딧이 부족해요", 503: "Fish Audio 서버가 잠시 바빠요 — 조금 뒤 다시"}.get(e.code, "")
        sys.exit(f"❌ Fish Audio 오류 {e.code} {hint} {msg}".strip())
    except urllib.error.URLError as e:
        sys.exit(f"❌ Fish Audio 에 연결하지 못했어요 — 인터넷 연결을 확인해 주세요 ({e.reason})")
    if os.path.getsize(raw_out) < 1000:
        sys.exit("❌ Fish Audio 가 빈 소리를 보냈어요 — 문장·목소리 id 를 확인해 주세요")


def synth_say(text, raw_out, voice=None):
    if pu.os_kind() != "mac":
        sys.exit("❌ say 엔진은 맥에서만 돼요(시험용). 실제 나레이션은 --engine fish.")
    aiff = raw_out + ".aiff"
    subprocess.run(["say", "-v", voice or "Yuna", "-o", aiff, text], check=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", aiff, raw_out], check=True)
    os.unlink(aiff)


def finish(raw, out):
    """앞뒤 여유 + 음량 두 번 재서 -14 LUFS(최고 -2 dBTP) + 48kHz 2채널 wav (편집본 규격)."""
    ms = int(PAD * 1000)
    pre = f"aformat=channel_layouts=stereo,adelay={ms}|{ms},apad=pad_dur={PAD}"
    m = subprocess.run(["ffmpeg", "-nostats", "-i", raw, "-vn", "-af", f"{pre},loudnorm=I=-14:TP=-2:LRA=11:print_format=json",
                        "-f", "null", "-"], capture_output=True, text=True).stderr
    j = json.loads(m[m.rfind("{"):m.rfind("}") + 1])
    ln = (f"loudnorm=I=-14:TP=-2:LRA=11:measured_I={j['input_i']}:measured_TP={j['input_tp']}:measured_LRA={j['input_lra']}:"
          f"measured_thresh={j['input_thresh']}:offset={j['target_offset']}:linear=true")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", raw, "-vn", "-af", f"{pre},{ln},aresample=48000",
                    "-ac", "2", "-ar", "48000", "-c:a", "pcm_s16le", out], check=True)


def duration(path):
    o = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                       capture_output=True, text=True).stdout.strip()
    return round(float(o), 3)


def words_of(wav):
    """wav 를 받아써 단어 시간(wav 안 기준)을 얻는다 — 자막용."""
    w16 = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", wav, "-vn", "-ac", "1", "-ar", "16000", w16], check=True)
    r = pu.transcribe(w16, language="ko", word_timestamps=True, condition_on_previous_text=False)
    os.unlink(w16)
    return [{"w": w["word"].strip(), "s": round(w["start"], 3), "e": round(w["end"], 3)}
            for s in r["segments"] for w in s.get("words", []) if w["word"].strip()]


def say_one(text, out, engine, voice=None):
    raw = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    if engine == "fish":
        synth_fish(text, raw, voice_id(voice))
    elif engine == "say":
        synth_say(text, raw, voice)
    else:
        sys.exit(f"❌ 모르는 엔진: {engine} (fish | say)")
    finish(raw, out)
    os.unlink(raw)
    return duration(out)


def plan(res, engine):
    p = os.path.join(res, "narration.json")
    if not os.path.exists(p):
        sys.exit(f"narration.json 이 없어요: {p}")
    items = json.load(open(p, encoding="utf-8"))
    os.makedirs(os.path.join(res, "narration"), exist_ok=True)
    made = 0
    for it in items:
        for k in ("id", "text", "after_sentence", "mode"):
            if k not in it:
                sys.exit(f"❌ narration.json 항목에 {k} 가 없어요: {it}")
        if it["mode"] not in ("hold", "over"):
            sys.exit(f"❌ mode 는 hold 또는 over: {it['id']}")
        wav = os.path.join(res, "narration", f"{it['id']}.wav")
        fresh = os.path.exists(wav) and it.get("text_done") == it["text"] and it.get("engine") == engine
        if not fresh:
            say_one(it["text"], wav, engine)
            it["words"] = words_of(wav)
            it["text_done"], it["engine"] = it["text"], engine
            made += 1
        it["wav"] = wav
        it["dur"] = duration(wav)
        print(f"{it['id']:>4} {it['mode']:<4} {it['dur']:5.2f}초 문장 {it['after_sentence']} 뒤 — {it['text']}")
    json.dump(items, open(p, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"나레이션 {len(items)}개 (새로 만든 것 {made}개, 엔진 {engine}). 다음: narration_apply.py {res}")


if __name__ == "__main__":
    a = [x for x in sys.argv[1:] if not x.startswith("--")]
    eng = sys.argv[sys.argv.index("--engine") + 1] if "--engine" in sys.argv else "fish"
    vo = sys.argv[sys.argv.index("--voice") + 1] if "--voice" in sys.argv else None
    a = [x for x in a if x not in (eng, vo)]
    if not a:
        sys.exit(__doc__)
    if a[0] == "say" and len(a) >= 3:
        d = say_one(a[1], a[2], eng, vo)
        print(f"{a[2]} ({d:.2f}초, 엔진 {eng})")
    elif a[0] == "plan" and len(a) >= 2:
        plan(os.path.abspath(a[1]), eng)
    else:
        sys.exit(__doc__)
