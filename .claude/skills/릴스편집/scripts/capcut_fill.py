#!/usr/bin/env python3
"""2단계 ③ CapCut 프로젝트 채우기 + 함정 점검을 한 번에.

사용법: capcut_fill.py <결과폴더> <빈 CapCut 프로젝트 폴더> [설계도 파일 이름, 기본 spec.json]
순서: CapCut 꺼짐 확인 → compile --into --check → compile --into
 → 배속 다시 맞추기(compile이 배속 정보를 1배로 남기는 함정: lint speed-material-mismatch)
 → register(소재 등록) → 조각마다 원본 시작·편집본 시작·배속을 timemap.json과 대조
- capcut init으로 만든 프로젝트는 Timelines 폴더가 없어 --active-timeline을 붙이면 거부된다.
 CapCut 앱이 만든 프로젝트(Timelines 있음)일 때만 --active-timeline을 붙인다.
- capcut-cli 결과는 파이프로 받으면 64KB에서 잘리므로 파일로 받는다.
"""
import json
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import platform_util as pu  # noqa: E402


def run(args, check=True):
    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
    with open(tmp, "w") as fh:
        p = subprocess.run(["capcut", *args], stdout=fh, stderr=subprocess.PIPE, text=True)
    txt = open(tmp).read()
    os.unlink(tmp)
    if check and p.returncode not in (0, 1):
        sys.exit(f"capcut {args[0]} 실패: {txt[-500:]} {p.stderr[-500:]}")
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        return {"raw": txt}


def main(res, proj, spec_name="spec.json"):
    if pu.capcut_running():
        sys.exit("CapCut이 켜져 있다. 꺼 달라고 요청하고 멈춘다.")
    spec = f"{res}/{spec_name}"
    extra = ["--active-timeline"] if os.path.isdir(f"{proj}/Timelines") else []
    c = run(["compile", spec, "--into", proj, *extra, "--check"])
    if not c.get("checked"):
        sys.exit(f"점검 실패: {str(c)[:500]}")
    run(["compile", spec, "--into", proj, *extra])
    lint = run(["lint", proj], check=False)
    fixed = 0
    for i in lint.get("issues", []):
        if i["code"] == "speed-material-mismatch":
            cmd = i["suggested_command"].split("#")[0].split()
            run(["speed", proj, cmd[-2], cmd[-1], "-q"])
            fixed += 1
 # lint --fix는 쓰지 않는다: 프로젝트 밖 소재(2GB 변환본·카드)를 프로젝트 폴더로 복사하는 정리까지 같이 한다.
 # 0ms 틈 경고는 프레임 단위로 맞춘 결과라 무해하다. 대신 소재를 등록해 CapCut 9에서 '파일 없음'을 막는다.
    run(["register", proj, "--materials", "--apply"], check=False)
    lint = run(["lint", proj], check=False)
    plan = [s for s in json.load(open(f"{res}/timemap.json")) if not s.get("hold")]  # 나레이션 정지 화면(사진)은 인물 조각 대조에서 뺀다
    segs = run(["segments", proj, "--track", "video"])
    segs = segs if isinstance(segs, list) else segs.get("segments", [])
    media = os.path.basename(json.load(open(spec))["tracks"][0]["items"][0]["path"])
    segs = [s for s in segs if os.path.splitext(media)[0] in (s.get("label") or s.get("name") or str(s))]  # 인물 트랙만 대조
    bad = []
    for p, s in zip(plan, segs):
        d = run(["segment", proj, s["id"]])
        si, st, sp = d["source_timerange"]["start"] / 1e6, d["target_timerange"]["start"] / 1e6, d["speed"]
        if abs(si - p["src_in"]) > 0.034 or abs(st - p["start"]) > 0.034 or abs(sp - p["speed"]) > 0.001:
            bad.append((round(p["start"], 2), si, p["src_in"], sp))
    out = {"segments": len(segs), "planned": len(plan), "speed_resynced": fixed,
           "lint": lint.get("summary"),
           "lint_codes": sorted({i["code"] for i in lint.get("issues", []) if i.get("severity") != "info"}),
           "mismatch": bad}
    json.dump(out, open(f"{res}/capcut_채우기_결과.json", "w"), ensure_ascii=False, indent=1)
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main(*sys.argv[1:4])
