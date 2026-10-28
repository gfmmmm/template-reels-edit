#!/usr/bin/env python3
"""3단계 ③-B 화면녹화 장면 — 사용자 화면 기록에서 보여 줄 곳을 잘라 세로 화면 클립으로 만든다(메뉴얼 3번 "화면녹화 자리").

사용법: screen_clip.py <결과폴더> [screens.json]
입력: [결과폴더]/screens.json
 [{"id": "s01-report", "src": "<화면 기록.mov>", "in": 21.0, "out": 27.0, "dur": 2.4,
 "layout": "full" | "top", "crop": [[x, y, w], [x, y, w]], "bg": "#FFFFFF"}, ...]
 - in~out(원본 초)을 dur(편집본 초)에 맞춰 빨리/느리게. dur을 빼면 원래 속도.
 - crop: 보여 줄 곳의 왼쪽 위(x, y)와 폭 w(원본 px). 두 개면 시작→끝으로 천천히 이동(문서를 내리며 짚기). 폭은 같게.
 높이는 화면 비율로 정해진다(full 1080×1920, top 1080×860). 원본보다 길면 남는 곳은 bg 색.
 - full: 틀 없이 화면 전체(자막은 CapCut에서 그 위에 얹힌다). top: 위쪽(세로 220~1080px)에만 얹고 아래는 투명 → 얼굴 위를 덮는 짧은 한 장.
 레이어 방식(CapCut 변환 그대로 — 정답지처럼 확대·위치 키프레임으로 한 방향으로 천천히 짚기, 여러 장 겹치기):
 {"id", "start", "end", "bg": "#FFFFFF" | null(투명), "group": {"scale": [a, b], "pos": [[x, y], [x, y]]},
 "layers": [{"src", "in", "speed": 1.0, "freeze": false, "from": 0, "dur": null,
 "scale": [s0, s1], "pos": [[x0, y0], [x1, y1]]}]}
 - scale·pos는 CapCut 값 그대로: 화면에 맞춘(fit) 크기 대비 배율, 위치는 화면 절반 단위(x 오른쪽 +, y 위쪽 +).
 시작→끝 값을 한 방향으로만 바꾼다(위아래로 왔다 갔다 하면 어색하다 — 사용자). 원본 녹화 속 스크롤이 오르내리는 구간은 피한다.
 - freeze: 그 시각 한 장면을 멈춰 쓴다(정답지 0.1배 정지 화면). png 이미지도 된다. 나중 레이어가 위.
 - 길이는 프레임 단위(끝 = 다음 클립 시작)로 맞춘다 — 이음에서 인물이 한 프레임 비치는 일을 막는다.
출력: [결과폴더]/cards/<id>.mov (불투명은 H.264, 투명은 ProRes 4444) — broll-plan.json에 component "Screen"으로 넣으면
 build_spec·render_check가 다른 카드처럼 다룬다.
"""
import json
import re
import os
import subprocess
import sys


def size(p):
    out = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=width,height",
                          "-of", "csv=p=0", p], capture_output=True, text=True).stdout.strip().strip(",")
    w, h = out.split(",")[:2]
 # 아이폰 세로 영상은 가로로 저장되고 회전 정보(-90)가 붙는다. ffmpeg 는 자동으로 세워서 읽으므로
 # 크기도 세운 기준으로 돌려준다(안 그러면 full 방식 자르기가 가로 기준으로 계산돼 실패한다 — 한 생활용품 계정 시험).
    rot = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                          "stream_side_data=rotation:stream_tags=rotate", "-of", "csv=p=0", p],
                         capture_output=True, text=True).stdout
    nums = [abs(int(float(x))) for x in re.findall(r"-?\d+(?:\.\d+)?", rot)]
    if any(n % 180 == 90 for n in nums):
        w, h = h, w
    return int(w), int(h)


def lerp(a, b, f):
    return f"({a}+({b}-({a}))*{f})"


def layered(res, s):
    """CapCut 변환(fit 대비 배율·화면 절반 단위 위치)을 ffmpeg로 그대로 그린다."""
    n = int(round(s["end"] * 30)) - int(round(s["start"] * 30))
    D = n / 30
    g = s.get("group", {})
    ga, gb = g.get("scale", [1, 1])
    (gx0, gy0), (gx1, gy1) = g.get("pos", [[0, 0], [0, 0]])
    G = lerp(ga, gb, f"(t/{D:.4f})")
    transparent = s.get("bg") is None
    inputs, fc = [], []
    canvas = "black@0" if transparent else s["bg"].replace("#", "0x")
    fc.append(f"color=c={canvas}:s=1080x1920:r=30:d={D:.4f},format={'yuva444p10le' if transparent else 'yuv420p'}[c0]")
    last = "c0"
    for k, L in enumerate(s["layers"]):
        W, H = size(L["src"])
        base = min(1080 / W, 1920 / H)
        frm = L.get("from", 0)
        ld = L.get("dur") or (D - frm)
        sp = L.get("speed", 1.0)
        img = L["src"].lower().endswith((".png", ".jpg", ".jpeg"))
        if img:
            inputs += ["-loop", "1", "-t", f"{D:.4f}", "-i", L["src"]]
            src = f"[{k}:v]fps=30,trim=duration={ld:.4f},setpts=PTS-STARTPTS+{frm}/TB"
        elif L.get("freeze"):
            inputs += ["-ss", str(L["in"]), "-i", L["src"]]
            src = (f"[{k}:v]trim=end_frame=1,loop=loop={int(ld * 30) + 2}:size=1,setpts=N/30/TB,fps=30,"
                   f"trim=duration={ld:.4f},setpts=PTS-STARTPTS+{frm}/TB")
        else:
            inputs += ["-i", L["src"]]
            src = (f"[{k}:v]trim={L['in']}:{L['in'] + ld * sp + 0.1},setpts=(PTS-STARTPTS)/{sp},fps=30,"
                   f"trim=duration={ld:.4f},setpts=PTS-STARTPTS+{frm}/TB")
        s0, s1 = L.get("scale", [1, 1])
        (x0, y0), (x1, y1) = L.get("pos", [[0, 0], [0, 0]])
        f = f"(min(max((t-{frm})/{ld:.4f},0),1))"
        S = f"({lerp(s0, s1, f)}*{G})"
        fc.append(f"{src},scale=w='trunc({W}*{base:.6f}*{S}/2)*2':h=-2:eval=frame:flags=bicubic,format=yuva444p10le[l{k}]")
        X = f"(540+({lerp(x0, x1, f)}*{G}+{lerp(gx0, gx1, f'(t/{D:.4f})')})*540-overlay_w/2)"
        Y = f"(960-({lerp(y0, y1, f)}*{G}+{lerp(gy0, gy1, f'(t/{D:.4f})')})*960-overlay_h/2)"
        fc.append(f"[{last}][l{k}]overlay=x='{X}':y='{Y}':eval=frame:enable='between(t,{frm},{frm + ld})'[o{k}]")
        last = f"o{k}"
    fc.append(f"[{last}]trim=duration={D:.4f}[v]")
    out = f"{res}/cards/{s['id']}.mov"
    enc = (["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le"] if transparent
           else ["-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p"])
    script = f"{res}/cards/.{s['id']}.txt"
    open(script, "w").write(";\n".join(fc))
    subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-/filter_complex", script, "-map", "[v]", "-an",
                    "-frames:v", str(n), *enc, out], check=True)
    os.remove(script)
    print(f"{s['id']}: {D:.3f}초({n}프레임), 레이어 {len(s['layers'])}, {'투명' if transparent else s['bg']} → {out}")


def main(res, spec_name="screens.json"):
    items = json.load(open(f"{res}/{spec_name}"))
    os.makedirs(f"{res}/cards", exist_ok=True)
    for s in items:
        if "layers" in s:
            layered(res, s)
            continue
        W, H = size(s["src"])
        dur = s.get("dur") or (s["out"] - s["in"])
        sp = (s["out"] - s["in"]) / dur
        full = s.get("layout", "full") == "full"
        oh = 1920 if full else 860
        (x0, y0, w), (x1, y1, _) = (s["crop"] + s["crop"])[:2] if len(s["crop"]) == 1 else s["crop"][:2]
        h = min(int(w * oh / 1080), H)
        h -= h % 2
        w -= w % 2
        clampx = lambda e: f"max(0,min({W - w},{e}))"
        clampy = lambda e: f"max(0,min({H - h},{e}))"
        f = f"(t/{dur:.4f})"
        crop = (f"crop={w}:{h}:x='{clampx(f'{x0}+({x1}-{x0})*{f}')}':y='{clampy(f'{y0}+({y1}-{y0})*{f}')}'")
        bg = s.get("bg", "#FFFFFF").replace("#", "0x")
        base = (f"[0:v]trim={s['in']}:{s['out']},setpts=(PTS-STARTPTS)/{sp:.5f},fps=30,{crop},"
                f"scale=1080:-2:flags=lanczos")
        out = f"{res}/cards/{s['id']}.mov"
        if full:
            fc = base + f",pad=1080:1920:0:(oh-ih)/2:color={bg},trim=duration={dur},setsar=1,format=yuv420p[v]"
            enc = ["-c:v", "libx264", "-crf", "16", "-preset", "medium", "-pix_fmt", "yuv420p"]
        else:
            fc = (base + f",pad=1080:{oh}:0:0:color={bg},format=yuva444p10le[s];"
                  f"color=c=black@0:s=1080x1920:r=30:d={dur},format=yuva444p10le[b];"
                  f"[b][s]overlay=0:220:shortest=1,trim=duration={dur}[v]")
            enc = ["-c:v", "prores_ks", "-profile:v", "4444", "-pix_fmt", "yuva444p10le"]
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", s["src"], "-filter_complex", fc, "-map", "[v]", "-an", *enc, out],
                       check=True)
        print(f"{s['id']}: {dur:.2f}초, {sp:.2f}배, {s.get('layout', 'full')}, crop {w}x{h} → {out}")


if __name__ == "__main__":
    main(*sys.argv[1:3])
