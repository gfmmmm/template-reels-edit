#!/usr/bin/env python3
"""2단계 ③ 수상한 곳 점검 — 받아쓰기가 반복을 한 단어로 합친 곳, 앞 테이크 꼬투리 조각 찾기.

사용법: suspect_check.py <결과폴더> <편집용 영상> (받아쓰기 엔진은 platform_util 이 고른다 — 아무 파이썬으로 실행해도 된다)
입력: takes.json, stt_chunks/chunks.json, timemap.json (cutplan.py 결과)
1. 긴 단어: 고른 테이크 안에서 글자 수에 비해 너무 오래 걸린 단어(0.8초 넘고 0.35초×글자+0.3초 넘음)
 — "예를 들어, 예를 들어"가 1.3초짜리 "예를" 하나로 찍힌 경우(한 편집 사례).
 다시 받아쓴 말은 믿지 않는다 — 받아쓰기는 같은 실수를 되풀이한다(IMG_0519 2026-10-24: "이렇게 받을 수 있는데"를
 두 번 말한 것이 1.76초짜리 "몰랐던" 하나로 찍혔고, 다시 받아써도 반복이 안 보여 "쉼"으로 넘겼다).
 그래서 원본 소리에서 그 단어 앞쪽(문장 시작~단어 끝) 안에 0.2초 넘게 조용한 틈이 있는지 잰다.
 틈이 있으면 "반복 의심(소리 틈)" — 틈 앞 말과 틈 뒤 말을 따로 받아써 앞 말이 뒤 말의 앞부분과 같으면 "반복 확정".
 확정이면 두 번째 말 시작(틈 끝)부터 쓰게 chunks.json 첫 단어 시작을 옮기고 cutplan 다시.
5. 숨 쉼 후보: 아직 남아 있는(잘리지 않은) 단어 경계의 숨·멈칫(0.2초 넘음)만 숨_후보.json으로 — 고른 것만 inner_cuts.json에 옮겨 cutplan 다시.
4. 문장 안 모든 쉼에서 "다시 시작" 확인 — 긴 단어가 아니어도("교통비를 환… 교통비를 환급받을", IMG_0519) 틈 앞뒤를
 따로 받아써 처음부터 다시 말했거나 끝 몇 글자를 더듬어 다시 말했으면 "반복 확정".
3. 문장별 다시 받아쓰기(필수): preview/컷_미리보기.mp4가 있으면 문장마다 잘라 따로 받아쓴다. 받아쓴 글자가 교정 문장보다
 3자 넘게 많으면 "문장 반복" — 영상 전체를 한 번에 받아쓰는 대조는 반복을 또 합쳐 통과시키므로 참고용일 뿐이다.
2. 꼬투리 조각: 앞 조각과 이어지지 않는 0.3초 미만 조각 — 잡소리·앞 반복의 첫소리일 때가 많다.
그 구간만 잘라 다시 받아써서 의심구간.json에 적는다. 고칠지·어떻게 고칠지는 AI가 판단한다
(두 번 말했으면 두 번째 말 시작부터 쓰게 chunks.json 그 단어 시작을 옮기고 cutplan 다시, 말이 아니면 조각 버림).
"""
import json
import os
import subprocess
import sys
import tempfile
from itertools import groupby
import re
import difflib

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import platform_util as pu  # noqa: E402


def retranscribe(video, a, b):
    wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{max(0, a):.3f}", "-to", f"{b:.3f}",
                    "-i", video, "-vn", "-ac", "1", "-ar", "16000", wav], check=True)
    r = pu.transcribe(wav, language="ko", word_timestamps=False, condition_on_previous_text=False)
    os.unlink(wav)
    return r["text"].strip()


def quiet_gaps(video, a, b, th=-45.0, min_len=0.2):
    """원본 [a, b] 안에서 th dB 아래가 min_len초 넘게 이어진 구간"""
    sr = 16000
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{max(0, a):.3f}", "-to", f"{b:.3f}", "-i", video,
                          "-vn", "-ac", "1", "-ar", str(sr), "-f", "s16le", "-"], capture_output=True).stdout
    x = np.frombuffer(raw, np.int16).astype(float) / 32768
    hop = int(sr * 0.02)
    n = len(x) // hop
    if n == 0:
        return []
    rms = 20 * np.log10(np.sqrt((x[: n * hop].reshape(n, hop) ** 2).mean(1)) + 1e-9)
    out, st = [], None
    for i, v in enumerate(list(rms) + [0.0]):
        if v < th and st is None:
            st = i
        elif v >= th and st is not None:
            if (i - st) * 0.02 >= min_len:
                out.append((round(a + st * 0.02, 2), round(a + i * 0.02, 2)))
            st = None
    return out


def norm(s):
    return re.sub(r"[^가-힣A-Za-z0-9]", "", s)


def main(res, video):
    takes = json.load(open(os.path.join(res, "takes.json")))
    chunks = json.load(open(os.path.join(res, "stt_chunks", "chunks.json")))
    tmap = json.load(open(os.path.join(res, "timemap.json")))
    out = []

    for t in takes:
        num, text, ci = t[0], t[1], t[2]
        words = chunks[ci]["words"]
        if len(t) > 3:
            words = words[t[3][0]:t[3][1] + 1]
        for w in words:
            n = len(w["w"].replace(" ", ""))
            d = w["e"] - w["s"]
            if d > 0.8 and d > 0.35 * n + 0.3:
                heard = retranscribe(video, w["s"] - 0.1, w["e"] + 0.1)
                item = {"종류": "긴 단어", "문장": num, "단어": w["w"], "원본": [w["s"], w["e"]],
                        "길이": round(d, 2), "다시 받아쓴 말": heard}
                gaps = quiet_gaps(video, words[0]["s"] + 0.05, w["e"] - 0.1)
                if gaps:
                    g = max(gaps, key=lambda x: x[1] - x[0])
                    before = retranscribe(video, words[0]["s"] - 0.05, g[0])
                    after = retranscribe(video, g[1], w["e"] + 0.6)
                    same = len(norm(before)) >= 2 and norm(after).startswith(norm(before)[:max(2, len(norm(before)) - 1)])
                    item.update({"종류": "반복 확정" if same else "반복 의심(소리 틈)", "소리 틈": g,
                                 "틈 앞 말": before, "틈 뒤 말": after,
                                 "고칠 곳": f"chunks.json 덩어리 {ci} 첫 단어 시작 → {g[1]}" if same else "AI가 듣고 판단"})
                out.append(item)

 # 4. 문장 안 모든 쉼에서 "다시 시작" 확인 ("교통비를 환… 교통비를 환급받을"을 못 잡음 — 단어가
 # 1.48초라 긴 단어 기준(1.7초)에 안 걸렸다). 고른 테이크 안의 0.2초 넘는 조용한 틈마다 틈 앞(문장 시작부터)과
 # 틈 뒤(1.6초)를 따로 받아써서 ① 틈 뒤가 문장 처음과 같게 시작(처음부터 다시) ② 틈 앞 끝 2자 이상이 틈 뒤 처음과
 # 같음(더듬어 다시) 이면 "반복 확정". 이미 긴 단어로 잡은 틈은 건너뛴다.
    done = {tuple(o.get("소리 틈", [])) for o in out}
    for t in takes:
        num, ci = t[0], t[2]
        words = chunks[ci]["words"]
        if len(t) > 3:
            words = words[t[3][0]:t[3][1] + 1]
        s0, e0 = words[0]["s"], words[-1]["e"]
        for g in quiet_gaps(video, s0 + 0.1, e0 - 0.1):
            if tuple(g) in done:
                continue
            before = norm(retranscribe(video, s0 - 0.05, g[0]))
            after = norm(retranscribe(video, g[1], min(g[1] + 1.6, e0 + 0.3)))
            if len(before) < 1 or len(after) < 2:
                continue
            k = max([j for j in range(2, min(len(before), len(after)) + 1) if before[-j:] == after[:j]] or [0])
            restart = len(before) >= 2 and after[:2] == before[:2]
            if restart or k >= 2:
                out.append({"종류": "반복 확정", "문장": num, "소리 틈": g, "틈 앞 말": before, "틈 뒤 말": after,
                            "어떻게": "처음부터 다시" if restart else f"끝 {k}자 더듬어 다시",
                            "고칠 곳": f"chunks.json 덩어리 {ci}: 틈 앞({s0:.2f}~{g[0]})을 버리고 {g[1]}부터" if restart
                            else f"덩어리 {ci}: 틈 앞 끝 '{before[-k:]}'가 반복 — 틈 앞 조각 끝을 그 말 시작 전으로"})

 # 5. 숨 쉼 후보("호흡 뜨는 곳 무음 제거"): 고른 테이크 안에서 숨·멈칫(-22dB 아래가 0.2초 넘고 — 0.16~0.18초는 'ㄱ·ㄷ' 받침 닫힘과 구별이 안 됐다(IMG_0519 국가·혜택도) 가장 낮은 곳 -30dB 아래)이
 # 받아쓰기 단어 경계(앞 단어 끝·다음 단어 시작 ±0.08초)에 걸친 것만. 단어 안(받침 닫힘)은 자르면 말이 씹힌다(IMG_0519).
 # 후보는 숨_후보.json(inner_cuts.json 꼴)로 — AI가 듣고 고른 것만 inner_cuts.json에 옮겨 cutplan 다시.
    breath = {}
    for t in takes:
        num, ci = t[0], t[2]
        words = chunks[ci]["words"]
        if len(t) > 3:
            words = words[t[3][0]:t[3][1] + 1]
        bounds = [(words[k]["e"], words[k + 1]["s"], words[k]["w"], words[k + 1]["w"]) for k in range(len(words) - 1)]
        kept = [(m["src_in"], m["src_out"]) for m in tmap if m["take"] == num]
        for g in quiet_gaps(video, words[0]["s"] + 0.1, words[-1]["e"] - 0.1, th=-22.0, min_len=0.20):
            if quiet_gaps(video, g[0], g[1], th=-30.0, min_len=0.04) == []:
                continue
            if not any(a <= g[0] and g[1] <= b for a, b in kept):  # 이미 잘려 나간 쉼
                continue
            hit = [bd for bd in bounds if g[0] - 0.08 <= bd[0] <= g[1] + 0.08 or g[0] - 0.08 <= bd[1] <= g[1] + 0.08]
            if hit:
                breath.setdefault(str(num), []).append([round(g[0] + 0.02, 3), round(g[1] - 0.02, 3)])
                out.append({"종류": "숨 쉼", "문장": num, "원본": g, "단어 사이": [hit[0][2], hit[0][3]]})
    json.dump(breath, open(os.path.join(res, "숨_후보.json"), "w"), ensure_ascii=False)

    for i, x in enumerate(tmap):
        joined = i > 0 and tmap[i - 1]["take"] == x["take"] and tmap[i - 1]["continues"]
        if x["duration"] < 0.3 and not joined:
            heard = retranscribe(video, x["src_in"] - 0.05, x["src_out"] + 0.05)
            out.append({"종류": "꼬투리 조각", "문장": x["take"], "편집본": round(x["start"], 2),
                        "원본": [round(x["src_in"], 3), round(x["src_out"], 3)],
                        "길이": round(x["duration"], 2), "다시 받아쓴 말": heard})

    prev = os.path.join(res, "preview", "컷_미리보기.mp4")
    if os.path.exists(prev):  # 문장별 다시 받아쓰기 — 반복은 문장 단위로만 드러난다
        texts = {t[0]: t[1] for t in takes}
        for num, g in groupby(tmap, key=lambda x: x["take"]):
            g = list(g)
            a, b = g[0]["start"], g[-1]["start"] + g[-1]["duration"]
            heard = retranscribe(prev, a, b)
            if len(norm(heard)) > len(norm(texts[num])) + 3:
                sm = difflib.SequenceMatcher(None, norm(texts[num]), norm(heard))
                extra = "".join(norm(heard)[j1:j2] for op, i1, i2, j1, j2 in sm.get_opcodes() if op in ("insert", "replace"))
                out.append({"종류": "문장 반복", "문장": num, "편집본": [round(a, 2), round(b, 2)],
                            "교정 문장": texts[num], "다시 받아쓴 말": heard, "더 들린 말": extra})

    json.dump(out, open(os.path.join(res, "의심구간.json"), "w"), ensure_ascii=False, indent=1)
    for o in out:
        print(json.dumps(o, ensure_ascii=False))
    print(f"의심 {len(out)}곳 → 의심구간.json")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
