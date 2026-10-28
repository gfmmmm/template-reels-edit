#!/usr/bin/env python3
"""3단계 조립 설계도 — 컷(2단계) + 확대 + 자막 + 상단 제목 + 자료화면 카드 + 효과음을 compile 설계도 하나로.

사용법: build_spec.py <결과폴더> <zoom.json>
입력: timemap.json, captions.json, broll-plan.json(+cards/<id>.mov), sfx-plan.json, 진행 폴더의 title.txt
 zoom.json: {"scales": {"조각번호": 1.15}, "first_punch": [1.3, 0.27, 1.09], "punch_at": [[편집본 시각, 1.15], ...],
 "ramps": {"조각번호": [시작 배율, 끝 배율]}} (조각번호는 timemap 순서)
 - scales: 조각 전체 순간 확대(계단식은 이어지는 조각에 1.05·1.1·1.15)
 - first_punch: 첫 컷 [튀는 배율, 빠지는 시간, 컷 끝 배율(천천히 다시 다가감, 없으면 1.0 유지)]
 - ramps: 조각 처음→끝 천천히 확대·축소(나열 문장 1.0→1.2, 마무리 1.1→1.0)
템플릿: [스킬폴더]/presets/templates/자막_흰색·노랑·빨강.json (정답지에서 떠낸 자막 조각, 글자만 바꿔 넣는다)
출력: spec_full.json → capcut_fill.py로 채운다(spec 파일 이름을 인자로).
"""
import copy
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import platform_util as pu  # noqa: E402

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TPL = f"{SKILL}/presets/templates"


def probe(path):
    """카드 파일의 실제 길이 (렌더가 프레임 단위로 반올림해 계획보다 조금 짧을 수 있다)."""
    import subprocess
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", path],
                         capture_output=True, text=True).stdout
    return round(float(out) - 0.001, 3)


def title_template(res, text):
    """상단 제목: 노랑 자막 템플릿을 복사해 위치(세로 230~420px 가운데)와 줄 폭만 바꾼다."""
    t = json.load(open(f"{TPL}/자막_노랑.json"))
    t = copy.deepcopy(t)
    t["name"] = "상단제목"
    y_px = 325  # 230~420 가운데
    t["segment"]["clip"]["transform"]["y"] = round((960 - y_px) / 960, 4)
    d = t["material"]["data"]
    d["line_max_width"] = 0.95
    path = f"{res}/title_template.json"
    json.dump(t, open(path, "w"), ensure_ascii=False, indent=1)
    return path



def focus_anchor(zoom, faces):
    """zoom.json "focus": {"조각번호": [x, y]} — 얼굴 대신 손·제품 같은 부분을 확대할 때(디테일 확대, 2026-10-26 정답지 대조).
    그 점(0~1, 화면 비율)이 확대 뒤 화면 가운데로 오게 하는 기준점으로 바꿔 faces 를 덮는다(화면 밖이 보이지 않게 0~1로 자름)."""
    out = dict(faces)
    for i, (fx, fy) in zoom.get("focus", {}).items():
        s = float(zoom["scales"].get(str(i), 1.0))
        if s <= 1.0:
            continue
        cl = lambda v: max(0.0, min(1.0, v))
        out[str(i)] = [round(cl((fx * s - 0.5) / (s - 1)), 4), round(cl((fy * s - 0.5) / (s - 1)), 4)]
    return out

def main(res, zoom_path):
    segs = json.load(open(f"{res}/timemap.json"))
    zoom = json.load(open(zoom_path))
    caps = json.load(open(f"{res}/captions.json"))
    plan = json.load(open(f"{res}/broll-plan.json"))
    sfx = json.load(open(f"{res}/sfx-plan.json"))["keep"]
    media = json.load(open(f"{res}/spec.json"))["tracks"][0]["items"][0]["path"]
    end = segs[-1]["start"] + segs[-1]["duration"]

    main_items = []
    for i, s in enumerate(segs):
 # 다음 조각 시작 - 이 조각 시작을 길이로 써서 µs 반올림 틈(0ms 틈 경고, CapCut이 열 때 뒤 조각을 당김)을 없앤다
        nxt = segs[i + 1]["start"] if i + 1 < len(segs) else s["start"] + s["duration"]
        if s.get("hold"):  # 나레이션 정지 화면 = 원본 한 프레임 사진 조각 (narration_apply.py 가 만든 png)
            it = {"path": s["png"], "type": "photo", "start": round(s["start"], 6), "duration": round(nxt - s["start"], 6)}
        else:
            it = {"path": media, "start": round(s["start"], 6), "duration": round(nxt - s["start"], 6),
                  "sourceStart": s["src_in"], "speed": s["speed"]}
        sc = zoom["scales"].get(str(i))
        if sc:
            it["scale"] = sc
        it["ref"] = f"seg{i}"
        main_items.append(it)
    tracks = [{"type": "video", "name": "인물", "items": main_items}]
    by_kind = {}
    for c in plan["cards"]:
 # 길이는 계획 길이(프레임 단위, 끝 = 다음 클립 시작). 파일이 계획보다 짧을 때만 파일 길이 — 이음에서 인물이 비치지 않게
        real = probe(f"{res}/cards/{c['id']}.mov")
        plan_d = round(c["end"] - c["start"], 4)
        by_kind.setdefault(c["component"], []).append(
            {"path": f"{res}/cards/{c['id']}.mov", "start": c["start"], "duration": min(plan_d, real)})
 # 파일보다 길게 적으면 compile 이 "source range exceeds" 로 멈춘다(remap 뒤 0.014초 넘침) — 1프레임 안 차이는 CapCut 이 프레임으로 맞춘다
    for kind, items in by_kind.items():
        tracks.append({"type": "video", "name": f"자료_{kind}", "items": items})
    narr = pu.load_narration(res)  # 나레이션 소리는 따로 오디오 트랙으로 (없으면 트랙도 없다)
    if narr:
        tracks.append({"type": "audio", "name": "나레이션", "items": [
            {"path": n["wav"], "start": n["at"], "duration": n["dur"], "volume": 1} for n in narr]})

    ops = []

    def src_time(i, t):
 # CapCut 영상 키프레임 시간은 조각 기준이 아니라 "원본 영상의 시각"이다(정답지에서 확인).
 # 확대 키프레임은 정답지처럼 scale_x(KFTypeScaleX) 하나로 쓴다(CapCut 비율 고정 상태의 저장 방식).
        return round(segs[i]["src_in"] + (t - segs[i]["start"]) * segs[i]["speed"], 4)

    if zoom.get("first_punch"):
        fp = zoom["first_punch"]
        a, dur = fp[0], fp[1]
        ops += [{"op": "keyframe", "target": "seg0", "property": "scale_x", "time": src_time(0, 0), "value": float(a), "easing": "ease-out"},
                {"op": "keyframe", "target": "seg0", "property": "scale_x", "time": src_time(0, dur), "value": 1.0}]
        if len(fp) > 2:  # 빠진 뒤 컷 끝까지 천천히 다시 다가가기 (정답지 1.0→1.09)
            ops.append({"op": "keyframe", "target": "seg0", "property": "scale_x",
                        "time": src_time(0, segs[0]["start"] + segs[0]["duration"] - 1 / 30), "value": float(fp[2])})
    for i, (a, b) in zoom.get("ramps", {}).items():
        i = int(i)
        ops += [{"op": "keyframe", "target": f"seg{i}", "property": "scale_x", "time": src_time(i, segs[i]["start"]), "value": float(a)},
                {"op": "keyframe", "target": f"seg{i}", "property": "scale_x",
                 "time": src_time(i, segs[i]["start"] + segs[i]["duration"] - 1 / 30), "value": float(b)}]
 # 확대 기준점 = 얼굴(faces.json, face_anchor.py). 가운데 기준으로 확대하면 얼굴이 대각선으로 밀려 보인다.
 # 배율 s에서 얼굴이 제자리에 있으려면 위치를 -(s-1)×(얼굴과 화면 가운데의 거리)만큼 옮긴다(위치 단위 = 화면 절반, y 위 +).
    faces = json.load(open(f"{res}/faces.json")) if os.path.exists(f"{res}/faces.json") else {}
    faces = focus_anchor(zoom, faces)
    for i, sc in zoom["scales"].items():
        if str(i) not in faces or float(sc) == 1.0:
            continue
        fx, fy = faces[str(i)]
        k = float(sc) - 1
        t0 = src_time(int(i), segs[int(i)]["start"])
        ops += [{"op": "keyframe", "target": f"seg{i}", "property": "position_x", "time": t0, "value": round(-k * (fx - 0.5) * 2, 4)},
                {"op": "keyframe", "target": f"seg{i}", "property": "position_y", "time": t0, "value": round(-k * (0.5 - fy) * 2, 4)}]
 # 조각 중간 확대: 강조 단어가 나오는 순간 그대로 확대 (앞은 원래 배율 유지 → hold)
 # 한 조각 안에 여러 번(계단식)이면 이어서: 직전 배율 → 다음 배율
    by_seg = {}
    for t, sc in sorted(zoom.get("punch_at", [])):
        i = next(k for k, s in enumerate(segs) if s["start"] <= t < s["start"] + s["duration"])
        by_seg.setdefault(i, []).append((t, sc))
    for i, pts in by_seg.items():
        prev = zoom["scales"].get(str(i), 1.0)
 # hold는 compile에서 적용되지 않는다 → 확대 직전 프레임에 원래 배율 키프레임을 직접 넣어 순간 확대로 만든다
        ops.append({"op": "keyframe", "target": f"seg{i}", "property": "scale_x", "time": src_time(i, segs[i]["start"]), "value": float(prev)})
        for t, sc in pts:
            ops += [{"op": "keyframe", "target": f"seg{i}", "property": "scale_x", "time": src_time(i, t - 1 / 30), "value": float(prev)},
                    {"op": "keyframe", "target": f"seg{i}", "property": "scale_x", "time": src_time(i, t), "value": float(sc)}]
            prev = sc
    tpl = {"white": "자막_흰색", "yellow": "자막_노랑", "red": "자막_빨강"}
 # 자막 높이 옮기기(공용 규칙): 값은 [결과폴더]/caption_dy.txt 한 곳(px, +면 아래로).
 # 확인본(overlay_props captionTop = 1120 + dy)도 같은 값을 쓴다 — 한쪽만 고치면 승인본과 CapCut이 달라진다. preview_match.py가 대조.
    dy = float(open(f"{res}/caption_dy.txt").read()) if os.path.exists(f"{res}/caption_dy.txt") else 0.0
    def cap_tpl(name, extra=0.0):
        d = dy + extra  # extra = 자막마다 높이(caption_place.py 가 장면별로 적은 captions.json "dy")
        if not d:
            return f"{TPL}/{name}.json"
        os.makedirs(f"{res}/overlay_tpl", exist_ok=True)
        out = f"{res}/overlay_tpl/{name}_dy{int(d)}.json"
        t = json.load(open(f"{TPL}/{name}.json"))
        t["segment"]["clip"]["transform"]["y"] = round(t["segment"]["clip"]["transform"]["y"] - d / 960, 4)
        json.dump(t, open(out, "w"), ensure_ascii=False)
        return out
    for c in caps:
        if c.get("hidden"):  # 라벨이 대신 나오는 구간
            continue
 # 크게(약 2배)는 정답지 "특히" 조각 템플릿. 색·부분 칠하기는 compile 뒤 capcut_finish가 text-ranges로
        name = "자막_크게" if c.get("big") else tpl[c["color"]]
        ops.append({"op": "template", "path": cap_tpl(name, float(c.get("dy", 0))), "start": c["start"],
                    "duration": round(c["end"] - c["start"], 3), "text": c["text"]})
 # 이모지·라벨·메모: 정답지에서 떠낸 템플릿(흔들림 포함)의 위치만 바꾼 사본으로 compile에 넣는다.
 # apply-template은 트랙을 고르지 못해 자막 트랙에 겹쳐 넣는다(lint caption-overlap) → compile이 템플릿 이름별 트랙을 만든다.
    if os.path.exists(f"{res}/overlays.json"):
        kind_tpl = {"emoji": "이모지_흔들림", "label": "라벨_흔들림", "memo": "메모_노랑"}
        os.makedirs(f"{res}/overlay_tpl", exist_ok=True)
        for k, o in enumerate(json.load(open(f"{res}/overlays.json"))):
 # 계정마다 메모·라벨·리액션 글자 모양이 여러 가지일 수 있다 → "tpl"(presets/templates 안 이름)로 고르고,
 # "scale"(배율)·"color"(#RRGGBB)로 덮는다. 없으면 kind 기본 틀 그대로(한 생활용품 계정 시험: 흰 메모·크기 다른 리액션 글자)
            t = json.load(open(f"{TPL}/{o.get('tpl') or kind_tpl[o['kind']]}.json"))
            t["segment"]["clip"]["transform"] = {"x": o["x"], "y": o["y"]}
            if o.get("scale"):
                t["segment"]["clip"]["scale"] = {"x": float(o["scale"]), "y": float(o["scale"])}
            if o.get("color"):
                hx = o["color"].lstrip("#")
                rgb = [int(hx[k:k + 2], 16) / 255 for k in (0, 2, 4)]
                t["material"]["data"]["text_color"] = "#" + hx.lower()
                c = json.loads(t["material"]["data"]["content"])
                for st in c.get("styles", []):
                    if "fill" in st:
                        st["fill"]["content"]["solid"]["color"] = rgb
                t["material"]["data"]["content"] = json.dumps(c, ensure_ascii=False, separators=(",", ":"))
 # 공용 규칙: 이모지·라벨·메모는 CapCut "일반 글자"(text) 종류 — 자막(subtitle) 종류면
 # CapCut이 자막 하나를 옮길 때 모든 자막을 같이 옮겨 이모지와 자막이 함께 움직인다. 틀(presets)은 계정마다 다르므로 여기서 강제한다.
            t["material"]["data"]["type"] = "text"
            if o["kind"] == "emoji":  # 이모지 뒤 검정 그림자(셔츠·손 위에서 묻히지 않게)
                c = json.loads(t["material"]["data"]["content"])
                for st in c.get("styles", []):
                    st["shadows"] = [{"thickness_projection_distance": 0, "diffuse": 0.18, "angle": -90, "thickness_projection_enable": False,
                                      "content": {"solid": {"color": [0, 0, 0]}, "render_type": "solid"}, "distance": 0.04,
                                      "thickness_projection_angle": -45, "alpha": 0.7}]
                t["material"]["data"]["content"] = json.dumps(c, ensure_ascii=False, separators=(",", ":"))
                t["material"]["data"]["has_shadow"] = True
            path = f"{res}/overlay_tpl/{k:02d}_{o['kind']}.json"
            json.dump(t, open(path, "w"), ensure_ascii=False)
            ops.append({"op": "template", "path": path, "start": o["start"], "duration": round(o["end"] - o["start"], 3), "text": o["text"]})
 # 상단 제목은 자막과 다른 트랙이어야 해서 compile 뒤에 add-text(--track-name 상단제목, presets/제목_노랑.json)로 넣는다
    for k in sfx:
        ops.append({"op": "template", "path": k["template"], "start": k["place"], "duration": k["dur"], "ref": f"sfx_{k['place']}"})
    spec = {"name": os.path.basename(os.path.abspath(res)), "width": 1080, "height": 1920, "fps": 30, "ratio": "9:16",
            "tracks": tracks, "operations": ops}
    json.dump(spec, open(f"{res}/spec_full.json", "w"), ensure_ascii=False, indent=1)
 # 효과음 크기는 compile 뒤에 조각별로 맞춘다 (capcut volume)
    json.dump([{"start": k["place"], "volume": k["volume"], "sfx": k["sfx"]} for k in sfx],
              open(f"{res}/sfx_volumes.json", "w"), ensure_ascii=False, indent=1)
    print(f"트랙 {len(tracks)}개(인물 + 자료화면 {len(by_kind)}종), 자막 {sum(not c.get('hidden') for c in caps)}개, "
          f"효과음 {len(sfx)}개, 확대 {len(zoom['scales'])}곳 + 천천히 {len(zoom.get('ramps', {}))}곳")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
