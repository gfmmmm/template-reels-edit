#!/usr/bin/env python3
"""2단계 ③ 문장 앞뒤 끝을 실제 소리에 붙인다 — 받아쓰기 단어 시각은 앞뒤로 0.1~0.3초씩 틀려서
그대로 쓰면 말끝이 잘리거나(넉넉히 잡으면) 문장 사이에 무음이 뜬다(한 생활용품 계정 시험: 틈 0.2~0.28초가
열 곳 넘게 → 편집자 정답지는 중앙 0.07초, 대부분 0.1초 이하).

사용법: edge_snap.py <결과폴더> <편집용 영상> [--th -38] [--lead 0.03] [--tail 0.05] [--keep 1,4]
입력: takes.json, timemap.json(cutplan 결과 — 무음 감지로 찾은 조각 경계를 기준점으로 쓴다. 받아쓰기 시각은 1초까지 틀린 적이 있다)
출력: edge_fix.json (문장마다 start·end 를 소리 기준으로. 이미 있는 값은 덮는다 — --keep 문장 번호는 그대로 둔다)
규칙: 기준점 = 그 문장 첫 조각 시작·마지막 조각 끝(timemap). 시작은 기준점이 소리 안이면 그 소리 덩어리 시작까지
 (0.25초 안), 무음이면 다음 소리 시작으로 - lead. 끝은 기준점이 소리 안이면 소리가 끝날 때까지(0.5초 안),
 무음이면 직전 소리 끝으로 + tail. 원본에서 바로 이어지는 다음 문장 시작은 넘지 않는다.
 바로 앞·뒤에 뺀 단어(군말·맞장구·녹화 혼잣말)가 붙어 있으면 소리를 따라가지 않고 그 사이 가장 조용한
 곳에서 자른다 — 소리를 따라가면 뺀 단어 첫머리가 딸려 들어온다(맞장구 뒤 혼잣말 0.4초).
 이때 끝·첫 단어 안의 음절 사이 골은 자리로 삼지 않고, 고른 자리 바로 옆에 같은 단어의 음절이 이어지면 그 끝까지 넓힌다
 (받아쓰기 단어 끝 시각이 실제보다 일러 끝 음절이 통째로 빠졌다 — follow_tail·follow_head, 공용 76).
끝나면 cutplan.py 를 다시 돌린다. 화자가 바뀌는 곳에도 숨을 따로 더 두지 않는다 — 틈 기준은 편집메뉴얼 12번.
"""
import json
import os
import re
import subprocess
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import platform_util as pu  # noqa: E402


def arg(n, d):
    return type(d)(sys.argv[sys.argv.index(n) + 1]) if n in sys.argv else d


def env(video, a, b, hop=0.01, af=None):
    """a~b 소리 크기(dB) 곡선. af 를 주면 그 필터를 거친 소리로(예: "highpass=f=2500" — ㅅ·ㅊ 같은 마찰음은 전체 크기로는 작아도 높은 소리 띠에 뚜렷하다)"""
    a = max(0.0, a)
    out = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{a:.3f}", "-t", f"{b - a:.3f}", "-i", video,
                          "-vn", "-ac", "1", "-ar", "16000", *(["-af", af] if af else []), "-f", "s16le", "-"], capture_output=True).stdout
    x = np.frombuffer(out, np.int16).astype(float) / 32768
    n = int(16000 * hop)
    db = [20 * np.log10(np.sqrt((x[i:i + n] ** 2).mean()) + 1e-9) for i in range(0, max(0, len(x) - n), n)]
    return a, hop, db


def norm(t):
    return re.sub(r"[^0-9A-Za-z가-힣]", "", t or "")


def heard(video, a, b):
    """a~b 구간을 받아써 글자만 남긴다(뺀 단어 옆 자르는 자리 확인용)."""
    wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-ss", f"{max(0, a):.3f}", "-t", f"{b - a:.3f}", "-i", video,
                    "-vn", "-ac", "1", "-ar", "16000", wav])
    try:
        return norm(pu.transcribe(wav, word_timestamps=False)["text"])
    finally:
        os.unlink(wav)


def level(video, a, b):
    """그 문장 말소리 기준 크기(위 10% - 15dB)."""
    _, _, db = env(video, a, b)
    sp = [x for x in db if x > -50]
    return sorted(sp)[int(len(sp) * 0.9)] - 15 if len(sp) >= 10 else -35.0


def follow_tail(video, end, lvl, limit=None):
    """자른 자리 바로 뒤(0.12초 안)에 같은 단어의 남은 음절이 이어지면 그 끝까지 늘린다 — 받아쓰기 단어 끝 시각은 실제보다 일러서
    '끝 단어 안 골'을 막는 것만으로는 부족했다(2026-10-28 블라인드 시험: 끝 음절이 받아쓰기 끝 0.04초 뒤까지 이어졌다).
    이어지는 소리가 0.45초 넘거나 limit(뺀 다음 단어 시작) 넘어까지 가면 다른 말이라 그대로 둔다."""
    _, hop, de = env(video, end, end + 0.6)
    run = [j for j in range(len(de) - 3) if min(de[j:j + 4]) > lvl]
    if run and run[0] * hop <= 0.12:
        k = run[0]
        while k < len(de) - 1 and de[k + 1] > lvl - 6:
            k += 1
        new = end + (k + 1) * hop + 0.03
        if (k + 1) * hop <= 0.45 and (limit is None or new <= limit + 0.05):
            return round(new, 3)
    return end


def follow_head(video, start, lvl, limit=None):
    """자른 자리 바로 앞(0.1초 안)에서 같은 단어 첫 음절이 끝나면 그 시작까지 당긴다(0.25초 넘으면 다른 말)."""
    s0, hop, ds = env(video, start - 0.4, start)
    m = len(ds)
    voiced = [j for j in range(m - 3) if min(ds[j:j + 4]) > lvl]
    if voiced and (m - 1 - voiced[-1]) * hop <= 0.1:
        j = voiced[-1]
        while j > 0 and ds[j - 1] > lvl - 6:
            j -= 1
        new = start - (m - j) * hop - 0.02
        if (m - j) * hop <= 0.25 and (limit is None or new >= limit - 0.05):
            return round(new, 3)
    return start


def dips(db, th):
    """조용해지는 골(앞뒤보다 낮고 th 아래)들의 번호."""
    return [j for j in range(1, len(db) - 1) if db[j] <= db[j - 1] and db[j] <= db[j + 1] and db[j] < th]


def main(res, video):
    th, lead, tail = arg("--th", -38.0), arg("--lead", 0.03), arg("--tail", 0.05)
    keep = {int(k) for k in arg("--keep", "").split(",") if k.strip()}
    takes = json.load(open(f"{res}/takes.json"))
    tm = json.load(open(f"{res}/timemap.json"))
    span = {}
    for p in tm:
        a, b = span.get(p["take"], (1e9, -1))
        span[p["take"]] = (min(a, p["src_in"]), max(b, p["src_out"]))
    try:
        fix = json.load(open(f"{res}/edge_fix.json"))
    except FileNotFoundError:
        fix = {}
    order = [tk[0] for tk in takes]
    nocut = set()
    if os.path.exists(f"{res}/nocut.json"):  # 작게 녹음된 통화·스피커 문장 — 소리 기준으로 자르지 않는다
        nc = json.load(open(f"{res}/nocut.json"))
        nocut = {int(k) for k in (nc if isinstance(nc, list) else nc.keys())}
    last_take = order[-1] if order else None
    try:
        chunks = json.load(open(f"{res}/stt_chunks/chunks.json"))
    except FileNotFoundError:
        chunks = []
    used = {(tk[2], w) for tk in takes if len(tk) > 3 for w in range(tk[3][0], tk[3][1] + 1)}

    def dropped(tk, side):
 # 이 문장 바로 앞(side=-1)·뒤(+1) 단어가 같은 덩어리에 있는데 어느 문장에도 안 쓰였나
        if len(tk) < 4 or not (0 <= tk[2] < len(chunks)):
            return False
        w = tk[3][0] - 1 if side < 0 else tk[3][1] + 1
        return 0 <= w < len(chunks[tk[2]].get("words", [])) and (tk[2], w) not in used

    report = []
    for i, n in enumerate(order):
        if n in keep or n not in span or n in nocut:
            continue
        a_src, b_src = span[n]
        nxt = span.get(order[i + 1], (None,))[0] if i + 1 < len(order) else None
        if nxt is not None and not (b_src - 0.05 <= nxt <= b_src + 1.0):
            nxt = None  # 원본에서 바로 이어지는 다음 문장만 경계로 본다
        prv = span.get(order[i - 1], (None, None))[1] if i > 0 else None
        if prv is not None and not (a_src - 1.0 <= prv <= a_src + 0.05):
            prv = None
        tk = takes[i]
        t0, hop, db = env(video, a_src - 0.25, a_src + 0.25)
        k = min(len(db) - 1, int(0.25 / hop)) if db else 0
        start = None
        if dropped(tk, -1):
 # 바로 앞 단어를 뺐다: 소리를 따라가면 그 단어 꼬리가 딸려 온다. 조용한 골을 늦은 것부터 하나씩 대 보고
 # 받아쓰기가 첫 단어로 시작하고 뺀 단어로 시작하지 않는 첫 자리에서 자른다(받아쓰기 시각은 0.3초씩 틀려서 소리로만은 못 정한다)
            W = chunks[tk[2]]["words"]
            w0 = max(a_src, W[tk[3][0]]["s"])
            first, gone = norm(W[tk[3][0]]["w"]), norm(W[tk[3][0] - 1]["w"])
            t0, hop, db = env(video, w0 - 0.45, w0 + 0.12)
            cand = sorted(dips(db, th + 12), reverse=True) or [len(db) - 1]
            start = None
            ws = W[tk[3][0]]["s"]
            for j in cand:
                c = t0 + j * hop
                if c > ws + 0.12:  # 첫 단어 안쪽 골(음절 사이)은 자르는 자리가 아니다 — 받아쓰기는 잘린 첫소리를 채워 듣는다
                    continue
                h = heard(video, c, b_src)
                if h.startswith(first[:2]) and not h.startswith(gone[:2]):
                    start = c + lead
                    break
            if start is None:
                start = t0 + min(range(len(db)), key=lambda j: db[j]) * hop + lead
            start = follow_head(video, start, level(video, a_src, b_src), W[tk[3][0] - 1]["e"])
        elif db:
            if db[k] > th:
                while k > 0 and db[k - 1] > th:
                    k -= 1
                start = t0 + k * hop
            else:
                up = next((j for j in range(k, len(db)) if db[j] > th), None)
                start = t0 + up * hop if up is not None else None
        if start is not None:
            start = round(max(start - lead, prv if prv is not None else -1), 3)
        t0, hop, db = env(video, b_src - 0.25, b_src + 0.5)
        k = min(len(db) - 1, int(0.25 / hop)) if db else 0
        end = None
        if dropped(tk, 1):
 # 바로 뒤 단어를 뺐다: 조용한 골을 이른 것부터 대 보고, 받아쓰기가 끝 단어로 끝나고 뺀 단어로 끝나지 않는 첫 자리
 # (처음 조용해지는 곳만 보면 말끝이 잘리고, 가장 조용한 곳만 보면 뺀 혼잣말이 딸려 왔다)
            W = chunks[tk[2]]["words"]
            w1 = min(b_src, W[tk[3][1]]["e"])
            last, gone = norm(W[tk[3][1]]["w"]), norm(W[tk[3][1] + 1]["w"])
            t0, hop, db = env(video, w1 - 0.1, w1 + 0.5)
            cand = sorted(dips(db, th + 12)) or [len(db) - 1]
            end = None
            we = W[tk[3][1]]["e"]
            for j in cand:
                c = t0 + j * hop
                if c < we - 0.12:  # 끝 단어 안쪽 골(음절 사이)은 자르는 자리가 아니다(2026-10-28: 끝 단어를 음절 사이 0.08초 골에서
                    continue       # 잘라 끝 음절이 빠졌다 — 받아쓰기가 잘린 끝소리를 채워 들어 통과했다)
                h = heard(video, a_src, c)
                if h.endswith(last[-2:]) and not h.endswith(gone[-2:]):
                    end = round(c, 3)
                    break
            if end is None:
                end = round(t0 + min(range(len(db)), key=lambda j: db[j]) * hop, 3)
            end = follow_tail(video, end, level(video, a_src, b_src), W[tk[3][1] + 1]["s"])
        elif db:
            if db[k] > th:
                while k < len(db) - 1 and db[k + 1] > th:
                    k += 1
            else:
                while k > 0 and db[k] <= th:
                    k -= 1
            end = round(t0 + (k + 1) * hop + tail, 3)
        if end is not None and nxt is not None:
            end = min(end, round(nxt, 3))
        if n == last_take:
            end = None  # 영상 마지막 말은 cutplan --last-tail 여유를 그대로(공용 18) — 덮어쓰면 끝소리 여유가 사라진다
        f = fix.get(str(n), {})
        if start is not None:
            f["start"] = start
        if end is not None:
            f["end"] = end
        fix[str(n)] = f
        report.append((n, start, end))
    json.dump(fix, open(f"{res}/edge_fix.json", "w"), indent=0)
    for r in report:
        print(*r)
    print(f"edge_fix.json 문장 {len(report)}개 — cutplan.py 를 다시 돌린다")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
