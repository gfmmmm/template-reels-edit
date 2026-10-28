#!/usr/bin/env python3
"""효과음 다시 등록 — 꾸러미로 받은 효과음 파일(sfx/files/NN.mp3)을 이 컴퓨터 CapCut 팔레트 프로젝트에 넣고, 템플릿을 다시 뜬다.

왜: sfx/templates/*.json 은 소리 파일의 절대 경로를 담고 있어 다른 컴퓨터로 옮기면 깨진다(doctor.sh 가 ❌로 잡는다).
 이 스크립트를 한 번 돌리면 템플릿이 이 컴퓨터의 파일을 가리키게 된다. 카탈로그 번호·이름(sfx-catalog.md)은 그대로다.

사용법: sfx_register.py [--sfx <sfx 폴더>] [--project <팔레트 프로젝트 이름>] [--out-templates <폴더>] [--keep-project]
 --sfx 기본: 스킬의 sfx/
 --project 기본: 환경.md 의 [효과음팔레트] (없으면 "효과음팔레트"). 프로젝트가 없으면 capcut init 으로 만든다
 --out-templates 시험용: 템플릿과 palette_heard.json 사본을 이 폴더에 쓰고 스킬의 sfx/ 는 건드리지 않는다
동작: CapCut 꺼짐 확인 → 프로젝트 준비 → 소리마다 add-audio(번호 순서로 5초 간격, 팔레트 볼륨 그대로) → register --materials --apply
 → 소리마다 save-template → palette_heard.json 의 seg_id·src·template 갱신
윈도우 분기는 실제 윈도우에서 아직 시험하지 않았다.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import platform_util as pu  # noqa: E402

SKILL = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GAP = 5.0  # 소리 사이 간격(초)


def cli(*args, check=True):
    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
    with open(tmp, "w") as fh:  # 파이프는 64KB에서 잘린다
        p = subprocess.run(["capcut", *args], stdout=fh, stderr=subprocess.PIPE, text=True)
    txt = open(tmp, encoding="utf-8").read()
    os.unlink(tmp)
    if check and p.returncode not in (0, 1):
        sys.exit(f"capcut {args[0]} 실패: {txt[-300:]} {p.stderr[-300:]}")
    try:
        return json.loads(txt)
    except json.JSONDecodeError:
        return {"raw": txt, "rc": p.returncode, "err": p.stderr}


def arg(name, default=None):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


def main():
    sfx = os.path.abspath(arg("--sfx", os.path.join(SKILL, "sfx")))
    name = arg("--project") or pu.env_value("[효과음팔레트]") or "효과음팔레트"
    out_dir = arg("--out-templates")
    rows = json.load(open(os.path.join(sfx, "palette_heard.json"), encoding="utf-8"))
    rows.sort(key=lambda r: r["no"])
    if pu.capcut_running():
        sys.exit("CapCut이 켜져 있어요. CapCut을 완전히 끈 뒤 다시 돌려 주세요.")

    drafts = pu.capcut_drafts_dir()
    proj = os.path.join(drafts, name)
    if not os.path.isdir(proj):
        r = cli("init", name, "--ratio", "9:16")
        proj = r.get("draft_dir") or r.get("path") or r.get("dir") or proj
        if not os.path.isdir(proj):
            sys.exit(f"팔레트 프로젝트를 만들지 못했어요: {r}")
        print(f"팔레트 프로젝트 새로 만듦: {proj}")
    else:
        print(f"팔레트 프로젝트: {proj}")

 # 이미 들어 있는 소리(같은 파일 이름)는 건너뛴다
    have = {}
    segs = cli("segments", proj, "--track", "audio")
    segs = segs if isinstance(segs, list) else segs.get("segments", [])
    for s in segs:
        d = cli("segment", proj, s["id"])
        m = d.get("_material") or {}
        have[os.path.basename(m.get("path", ""))] = d
    end = max([(s.get("start_us", 0) + s.get("duration_us", 0)) / 1e6 for s in segs], default=0.0)
    t = (int(end / GAP) + 1) * GAP if segs else 0.0

    added = {}
    for r in rows:
        src = os.path.join(sfx, "files", os.path.basename(r.get("copy") or f"{r['no']:02d}.mp3"))
        if not os.path.exists(src):
            cand = [f for f in os.listdir(os.path.join(sfx, "files")) if f.startswith(f"{r['no']:02d}.")]
            if not cand:
                print(f"⚠️ {r['no']:02d} {r.get('ko_name')} 소리 파일이 없어 건너뜀")
                continue
            src = os.path.join(sfx, "files", cand[0])
        if os.path.basename(src) in have:
            added[r["no"]] = have[os.path.basename(src)]
            continue
        res = cli("add-audio", proj, src, f"{t:.3f}", "--volume", str(r.get("volume", 1)), "--track-name", "효과음")
        sid = res.get("segment_id") or res.get("id") or (res.get("segment") or {}).get("id")
        if not sid:
            print(f"⚠️ {r['no']:02d} add-audio 결과를 못 읽음: {str(res)[:200]}")
            continue
        added[r["no"]] = cli("segment", proj, sid)
        t += GAP
    cli("register", proj, "--materials", "--apply", check=False)

    tdir = out_dir or os.path.join(sfx, "templates")
    os.makedirs(tdir, exist_ok=True)
    n_ok = 0
    for r in rows:
        d = added.get(r["no"])
        if not d:
            continue
        fn = f"{r['no']:02d}_{r['ko_name']}"
        out = os.path.join(tdir, f"{fn}.json")
        p = subprocess.run(["capcut", "save-template", proj, d["id"][:8], fn, "--out", out], capture_output=True, text=True)
        if p.returncode:
            print(f"⚠️ 템플릿 실패: {fn} {p.stdout[:150]} {p.stderr[:150]}")
            continue
        r["seg_id"] = d["id"]
        r["src"] = (d.get("_material") or {}).get("path", r.get("src"))
        r["template"] = f"templates/{fn}.json"
        n_ok += 1
    heard_out = os.path.join(out_dir, "palette_heard.json") if out_dir else os.path.join(sfx, "palette_heard.json")
    json.dump(rows, open(heard_out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"효과음 {n_ok}/{len(rows)}개 등록 → 템플릿 {tdir}" + (" (시험용 출력)" if out_dir else ""))
    print("CapCut에서 팔레트 프로젝트를 한 번 열어 소리가 나는지 확인해 주세요." if not out_dir else "")


if __name__ == "__main__":
    main()
