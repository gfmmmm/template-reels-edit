#!/usr/bin/env python3
"""덩어리별 받아쓰기 — Whisper가 반복 테이크를 한 줄로 숨기거나 같은 문장을 복사해 붙이는 문제를 막는다.

사용법: transcribe_chunks.py <영상> <출력폴더> [--gap 0.5]
1. capcut detect-silence(-35dB, gap초 이상 쉰 곳)로 말 덩어리를 나눈다.
2. 덩어리마다 따로 받아쓴다(앞 문장 이어 쓰기 끔). 이것이 "덩어리별 재인식".
 받아쓰기 엔진은 platform_util 이 고른다(맥 애플칩 mlx_whisper, 그 외 faster_whisper). 윈도우 분기는 실제 윈도우에서 아직 시험하지 않았다.
3. 결과: chunks.json(덩어리별 시작·끝·글자·단어 시간·1초당 글자 수), chunks.srt
 1초당 글자 수가 유난히 낮은 덩어리 = 반복 테이크·버벅임이 숨어 있을 가능성 → flag.
"""
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import platform_util as pu  # noqa: E402


def speech_chunks(video, gap):
    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
    with open(tmp, "w") as fh:  # 파이프는 64KB에서 잘린다
        subprocess.run(["capcut", "detect-silence", video, "--threshold-db", "-35",
                        "--min-silence", str(gap), "--pad", "0.1"], stdout=fh)
    keeps = json.load(open(tmp))["keeps"]
    os.unlink(tmp)
    return [(k["start"], k["end"]) for k in keeps if k["end"] - k["start"] >= 0.3]


def srt_time(t):
    h, r = divmod(t, 3600)
    m, s = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{int(s):02d},{int(round((s % 1) * 1000)):03d}"


def main(video, out, gap=0.5):
    os.makedirs(out, exist_ok=True)
    chunks = speech_chunks(video, gap)
    wav = os.path.join(out, "audio16k.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vn", "-ac", "1", "-ar", "16000", wav], check=True)
    res = []
    for i, (a, b) in enumerate(chunks):
        clip = os.path.join(out, "clip.wav")
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", wav, clip], check=True)
        r = pu.transcribe(clip, language="ko", word_timestamps=True, condition_on_previous_text=False)
        words = [{"w": w["word"].strip(), "s": round(a + w["start"], 3), "e": round(a + w["end"], 3)}
                 for s in r["segments"] for w in s.get("words", [])]
        text = " ".join(s["text"].strip() for s in r["segments"]).strip()
        dur = b - a
        cps = len(text.replace(" ", "")) / dur if dur else 0
        res.append({"i": i, "start": round(a, 3), "end": round(b, 3), "text": text,
                    "cps": round(cps, 2), "words": words})
        print(f"{i:3d} {a:7.2f}-{b:7.2f} ({cps:4.1f}자/초) {text}", flush=True)
    os.remove(os.path.join(out, "clip.wav"))
    cps_all = sorted(r["cps"] for r in res if r["text"])
    med = cps_all[len(cps_all) // 2] if cps_all else 0
    for r in res:
        r["flag_slow"] = bool(r["text"]) and r["cps"] < med * 0.6
    json.dump(res, open(os.path.join(out, "chunks.json"), "w"), ensure_ascii=False, indent=1)
    with open(os.path.join(out, "chunks.srt"), "w") as f:
        for n, r in enumerate([r for r in res if r["text"]], 1):
            f.write(f"{n}\n{srt_time(r['start'])} --> {srt_time(r['end'])}\n{r['text']}\n\n")
    print(f"덩어리 {len(res)}개, 1초당 글자 중앙값 {med}, 느린 덩어리 {sum(r['flag_slow'] for r in res)}개")


if __name__ == "__main__":
    gap = float(sys.argv[sys.argv.index("--gap") + 1]) if "--gap" in sys.argv else 0.5
    main(sys.argv[1], sys.argv[2], gap)
