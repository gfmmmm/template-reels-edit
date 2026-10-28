#!/usr/bin/env python3
"""효과음팔레트에서 소리 목록 뽑기 — 이미 뽑은 조각은 건너뛰고 새 조각만 번호를 이어 붙인다.

사용법: sfx_extract.py <팔레트 프로젝트> <sfx 폴더>
결과: <sfx 폴더>/palette_raw.json (전체 목록), files/NN.확장자 (소리 사본)
이어서: sfx_listen.py → save-template → sfx-catalog.md (0_설치.md (2)-3)
프로젝트는 읽기만 한다.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile


def cli(*args):
 # capcut-cli는 파이프로 받으면 64KB에서 잘린다 → 파일로 받는다
    tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False).name
    with open(tmp, "w") as fh:
        subprocess.run(["capcut", *args], stdout=fh)
    out = json.load(open(tmp))
    os.unlink(tmp)
    return out


def main(proj, sfx):
    sfx = os.path.abspath(sfx)  # 목록에 절대 경로로 남겨야 다른 폴더에서 돌려도 찾는다
    raw_path = f"{sfx}/palette_raw.json"
    rows = json.load(open(raw_path)) if os.path.exists(raw_path) else []
    seen = {r["seg_id"] for r in rows}
    nxt = max([r["no"] for r in rows], default=0) + 1
    segs = cli("segments", proj, "--track", "audio")
    if isinstance(segs, dict):
        segs = segs.get("segments", [])
    os.makedirs(f"{sfx}/files", exist_ok=True)
    new = []
    for s in sorted(segs, key=lambda x: x.get("start", 0)):
        d = cli("segment", proj, s["id"])
        if d["id"] in seen:
            continue
        m = d["_material"]
        src = m["path"]
        dst = f"{sfx}/files/{nxt:02d}{os.path.splitext(src)[1]}"
        ok = os.path.exists(src)
        if ok:
            shutil.copy2(src, dst)
        r = {"no": nxt, "seg_id": d["id"], "name": m["name"], "volume": d["volume"],
             "dur": round(d["target_timerange"]["duration"] / 1e6, 2),
             "start": round(d["target_timerange"]["start"] / 1e6, 2),
             "src": src, "copy": dst if ok else None, "effect_id": m.get("effect_id")}
        rows.append(r)
        new.append(r)
        nxt += 1
    json.dump(rows, open(raw_path, "w"), ensure_ascii=False, indent=1)
    json.dump(new, open(f"{sfx}/palette_new.json", "w"), ensure_ascii=False, indent=1)
    for r in new:
        print(r["no"], r["name"], "vol", round(r["volume"], 2), r["dur"], "s", "OK" if r["copy"] else "파일없음")
    print(f"새 소리 {len(new)}개 → {sfx}/palette_new.json")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
