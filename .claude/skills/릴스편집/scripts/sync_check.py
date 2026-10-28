#!/usr/bin/env python3
"""③-E 싱크·끝말 검사 — CapCut에서 내보낸 영상을 다시 받아써서 편집본_단어시간.json과 단어 시작 시각을 맞춰 본다.

사용법: sync_check.py <결과폴더> <내보낸 영상> [--tol 0.25]
- 받아쓰기 엔진은 platform_util 이 고른다(맥 애플칩 mlx_whisper, 그 외 faster_whisper). 아무 파이썬으로 실행해도 된다.
- 같은 단어끼리 순서대로 짝지어(difflib) 시작 시각 차이의 중간값·최대값을 낸다. 최대가 tol(초)을 넘으면 실패.
- 영상 마지막 단어가 계획의 마지막 단어와 같은지(끝말 잘림) 확인.
출력: 한 줄 요약 + 종료 코드(0 통과, 1 실패)
"""
import difflib
import json
import os
import statistics
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import platform_util as pu  # noqa: E402


def main(res, video, tol=0.25):
    wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", video, "-vn", "-ac", "1", "-ar", "16000", wav], check=True)
    r = pu.transcribe(wav, language="ko", word_timestamps=True, condition_on_previous_text=False)
    os.unlink(wav)
    got = [(w["word"].strip().rstrip(".,!?"), w["start"]) for s in r["segments"] for w in s["words"]]
    plan = json.load(open(f"{res}/편집본_단어시간.json"))
    a = [x["w"].rstrip(".,!?") for x in plan]
    b = [w for w, _ in got]
    d = []
    for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(blk.size):
            d.append(got[blk.b + k][1] - plan[blk.a + k]["s"])
    if not d:
        sys.exit("단어를 하나도 맞추지 못했다 — 소리가 없거나 다른 영상.")
    worst = max(abs(x) for x in d)
    end_ok = bool(b) and b[-1] == a[-1]
    ok = worst <= tol and end_ok
    print(f"싱크 {'통과' if ok else '실패'}: 단어 {len(d)}/{len(a)}개 맞춤, 차이 중간값 {statistics.median(d):+.3f}초, 최대 {worst:.3f}초"
          f" / 끝말 {'정상' if end_ok else '잘림 의심'} (계획 '{a[-1]}', 실물 '{b[-1] if b else ''}')")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    tol = float(sys.argv[sys.argv.index("--tol") + 1]) if "--tol" in sys.argv else 0.25
    main(sys.argv[1], sys.argv[2], tol)
