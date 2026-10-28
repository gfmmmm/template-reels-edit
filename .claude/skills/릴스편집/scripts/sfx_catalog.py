#!/usr/bin/env python3
"""효과음 템플릿 만들기 + 목록 파일 다시 쓰기.

사용법: sfx_catalog.py <팔레트 프로젝트> <sfx 폴더> [새로 들은 결과.json]
- 새로 들은 결과(sfx_listen.py 출력)가 있으면 palette_heard.json에 합친다.
- 템플릿이 없는 소리만 capcut save-template (프로젝트는 읽기만).
- sfx-catalog.md를 전체 목록으로 다시 쓴다.
"""
import json
import os
import subprocess
import sys


def main(proj, sfx, new_path=None):
    heard_path = f"{sfx}/palette_heard.json"
    rows = json.load(open(heard_path)) if os.path.exists(heard_path) else []
    if new_path:
        have = {r["seg_id"] for r in rows}
        rows += [r for r in json.load(open(new_path)) if r["seg_id"] not in have]
    os.makedirs(f"{sfx}/templates", exist_ok=True)
    for r in rows:
        if r.get("template") and os.path.exists(f"{sfx}/{r['template']}"):
            continue
        fn = f"{r['no']:02d}_{r['ko_name']}"
        out = f"templates/{fn}.json"
        p = subprocess.run(["capcut", "save-template", proj, r["seg_id"][:8], fn, "--out", f"{sfx}/{out}"],
                           capture_output=True, text=True)
        r["template"] = out if p.returncode == 0 else None
        if p.returncode:
            print("템플릿 실패:", fn, p.stdout[:200], p.stderr[:200])
    rows.sort(key=lambda r: r["no"])
    json.dump(rows, open(heard_path, "w"), ensure_ascii=False, indent=1)

    L = ["# 효과음 목록 (sfx-catalog)", "",
         "효과음팔레트에서 떠낸 소리. 이름은 Gemini가 실제로 듣고 붙인 이름이다(원래 CapCut 이름은 외국어·모호한 게 많음).",
         "볼륨은 사용자가 팔레트에서 맞춘 값(1 = 원래 크기). 사본은 files/, 템플릿은 templates/.", "",
         "| 번호 | 이름 | 이럴 때 쓴다 | 피할 때 | 들리는 소리 | 느낌 | 길이(초) | 볼륨 | 가장 큰 시점(초) | 원래 CapCut 이름 |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        L.append(f"| {r['no']:02d} | {r.get('ko_name','')} | {r.get('use_when','')} | {r.get('avoid','')} | "
                 f"{r.get('sounds_like','')} | {r.get('mood','')} | {r['dur']} | {round(r['volume'], 2)} | "
                 f"{r.get('loudest_at')} | {r['name']} |")
    L += ["", "가장 큰 시점: 소리가 시작하고 몇 초 뒤에 가장 커지는지. 화면 전환에 맞출 때 이 값만큼 먼저 놓는다."]
    open(f"{sfx}/sfx-catalog.md", "w").write("\n".join(L) + "\n")
    print(f"{len(rows)}개 → {sfx}/sfx-catalog.md")


if __name__ == "__main__":
    main(*sys.argv[1:4])
