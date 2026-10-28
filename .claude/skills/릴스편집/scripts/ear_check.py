#!/usr/bin/env python3
"""귀 검수 도구 — 검수 에이전트는 소리를 못 들으니 숫자로 대신 듣는다.

사용법
 ear_check.py loudness <영상> 전체 음량(LUFS)·최고 음량(dBTP)
 ear_check.py edges <영상> <컷시간들.json|0.0,1.2,...> 컷 앞뒤 0.3초 소리 확인
 ear_check.py spikes <영상> [--jump 8] [--min-gap 0.25] 소리가 갑자기 커지는 지점

결과는 전부 JSON으로 출력한다. ffmpeg만 쓴다(추가 설치 없음).
"""
import array
import json
import os
import math
import re
import statistics
import subprocess
import sys

SR = 16000          # 분석용 샘플레이트 (mono)
WIN = 0.02          # 20ms 창


def decode_mono(path, start=None, dur=None):
    cmd = ["ffmpeg", "-v", "error"]
    if start is not None:
        cmd += ["-ss", f"{max(0.0, start):.3f}"]
    if dur is not None:
        cmd += ["-t", f"{dur:.3f}"]
    cmd += ["-i", path, "-vn", "-ac", "1", "-ar", str(SR), "-f", "s16le", "-"]
    raw = subprocess.run(cmd, capture_output=True, check=True).stdout
    a = array.array("h")
    a.frombytes(raw[: len(raw) // 2 * 2])
    return a


def db(rms):
    return 20 * math.log10(rms / 32768) if rms > 0 else -120.0


def rms_of(samples):
    if not samples:
        return 0.0
    return math.sqrt(sum(s * s for s in samples) / len(samples))


def window_db(samples, win=WIN):
    n = int(SR * win)
    return [db(rms_of(samples[i:i + n])) for i in range(0, len(samples) - n + 1, n)]


def cmd_loudness(path):
    p = subprocess.run(
        ["ffmpeg", "-nostats", "-i", path, "-af", "ebur128=peak=true", "-f", "null", "-"],
        capture_output=True, text=True)
    tail = p.stderr[p.stderr.rfind("Summary:"):]
    i = re.search(r"I:\s+(-?[\d.]+) LUFS", tail)
    lra = re.search(r"LRA:\s+(-?[\d.]+) LU", tail)
    tp = re.search(r"Peak:\s+(-?[\d.]+) dBFS", tail)
    out = {
        "file": path,
        "lufs": float(i.group(1)) if i else None,
        "true_peak_dbtp": float(tp.group(1)) if tp else None,
        "lra": float(lra.group(1)) if lra else None,
    }
    tgt = -12.0  # 업로드용 목표 음량(공용 규칙 -12, 계정이 바꾸려면 presets/음량.txt)
    try:
        tgt = float(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "presets", "음량.txt")).read().strip())
    except Exception:
        pass
    out["target_lufs"] = tgt
    out["ok_lufs"] = out["lufs"] is not None and abs(out["lufs"] - tgt) <= 1.0
    out["ok_peak"] = out["true_peak_dbtp"] is not None and out["true_peak_dbtp"] <= -1.0
    return out


def cmd_edges(path, times, span=0.3, edge=0.03):
    """컷마다: 직전 0.3초·직후 0.3초 평균 음량, 경계 30ms 음량, 경계 전후 차이.
    - 경계 30ms가 크면(말소리 수준) → 말이 잘렸을 가능성
    - 경계 전후 차이가 크면 → '툭' 튀는 소리 가능성
    """
    res = []
    for t in times:
        seg = decode_mono(path, t - span, span * 2)
        mid = min(len(seg), int(SR * span))
        before, after = seg[:mid], seg[mid:]
        e = int(SR * edge)
        b_edge, a_edge = db(rms_of(before[-e:])), db(rms_of(after[:e]))
        item = {
            "t": round(t, 3),
            "before_db": round(db(rms_of(before)), 1),
            "after_db": round(db(rms_of(after)), 1),
            "edge_before_db": round(b_edge, 1),
            "edge_after_db": round(a_edge, 1),
            "jump_db": round(a_edge - b_edge, 1),
        }
        flags = []
        if b_edge > -30:
            flags.append("컷 직전에 말소리가 크게 남아 있음(말끝 잘림 의심)")
        if a_edge > -30:
            flags.append("컷 직후 바로 큰 소리로 시작(말머리 잘림 의심)")
        if abs(item["jump_db"]) > 18:
            flags.append("컷 앞뒤 소리 크기 차이가 큼(툭 튐 의심)")
        item["flags"] = flags
        res.append(item)
    return {"file": path, "cuts": res, "flagged": sum(1 for r in res if r["flags"])}


def cmd_spikes(path, jump=8.0, min_gap=0.25, floor=-45.0):
    """직전 0.3초 중앙값보다 jump dB 이상 갑자기 커지는 20ms 창을 찾는다.
    효과음(쿵·띠링·우쉬)과 강하게 치고 들어오는 소리를 잡는 용도."""
    w = window_db(decode_mono(path))
    look = int(0.3 / WIN)
    out, last = [], -1e9
    for i in range(look, len(w)):
        base = statistics.median(w[i - look:i])
        if w[i] > floor and w[i] - base >= jump:
            t = i * WIN
            if t - last >= min_gap:
                out.append({"t": round(t, 2), "db": round(w[i], 1), "rise_db": round(w[i] - base, 1)})
                last = t
    dur = len(w) * WIN
    return {"file": path, "duration": round(dur, 2), "count": len(out),
            "per_sec": round(len(out) / dur, 3) if dur else 0, "spikes": out}


def parse_times(arg):
    if arg.endswith(".json"):
        data = json.load(open(arg, encoding="utf-8"))
        if isinstance(data, dict):
            data = data.get("cuts") or data.get("times") or []
        return [float(x["t"] if isinstance(x, dict) else x) for x in data]
    return [float(x) for x in arg.split(",") if x.strip()]


def opt(args, name, default):
    if name in args:
        return float(args[args.index(name) + 1])
    return default


def main(argv):
    if len(argv) < 3:
        print(__doc__)
        return 2
    cmd, path = argv[1], argv[2]
    if cmd == "loudness":
        out = cmd_loudness(path)
    elif cmd == "edges":
        out = cmd_edges(path, parse_times(argv[3]))
    elif cmd == "spikes":
        out = cmd_spikes(path, jump=opt(argv, "--jump", 8.0), min_gap=opt(argv, "--min-gap", 0.25))
    else:
        print(__doc__)
        return 2
    print(json.dumps(out, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
