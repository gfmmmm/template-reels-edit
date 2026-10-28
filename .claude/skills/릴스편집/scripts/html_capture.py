#!/usr/bin/env python3
"""실제 자료(HTML 보고서 등)를 영상용으로 캡처하고, 짚을 요소의 위치를 잰다 (IMG_0519).

사용법: html_capture.py <html> <out.png> [--width 900] [--height 9000] [--scale 2] [--css "<style>…</style>"] [--select ".card"]
출력: <out.png>(원본 픽셀 = CSS px × scale), <out>.json — --select 요소마다 {key: data-k 또는 첫 줄 글, box:[x,y,w,h](원본 픽셀), rows:[{text, box}]}
쓰는 법(3_효과.md ③-A2 "실제 자료 화면"):
 - 사용자 자료를 그대로 쓰지 말고 영상용 요약 HTML을 따로 만든다: 소제목은 한 줄(약 30px), 내용은 대상·혜택·마감처럼 핵심 줄만,
 찾는 법·신청·주의·서류·추천 이유 같은 줄은 뺀다. 가릴 것은 사용자 기준(편집메뉴얼)대로 — HTML 안에서 문장을 지우거나 blur.
 - 결과 위치로 ReportFocusScene items(view·mark)와 PolicyIntroScene reportShot(views·box)을 채운다.
브라우저: 맥 Google Chrome(헤드리스). 윈도우는 chrome.exe 경로를 CHROME 환경변수로.
"""
import html as H
import json
import os
import re
import subprocess
import sys


def arg(n, d):
    return sys.argv[sys.argv.index(n) + 1] if n in sys.argv else d


def main(src, out):
    chrome = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
    w, h, sc = int(arg("--width", 900)), int(arg("--height", 9000)), float(arg("--scale", 2))
    sel = arg("--select", ".card")
    t = open(src, encoding="utf-8").read()
    js = ("<script>window.addEventListener('load',()=>{const o=[];document.querySelectorAll(%s).forEach(c=>{const r=c.getBoundingClientRect();"
          "const rows=[...c.children].map(x=>{const q=x.getBoundingClientRect();return {text:x.textContent.trim().slice(0,40),box:[q.left,q.top+scrollY,q.width,q.height]}});"
          "o.push({key:c.dataset.k||c.textContent.trim().split('\\n')[0].slice(0,40),box:[r.left,r.top+scrollY,r.width,r.height],rows})});"
          "const p=document.createElement('pre');p.id='HCPOS';p.style.display='none';p.textContent=JSON.stringify(o);document.body.appendChild(p)});</script>") % json.dumps(sel)
    t = t.replace("</head>", arg("--css", "") + "</head>", 1).replace("</body>", js + "</body>", 1)
    tmp = os.path.splitext(out)[0] + "_capture.html"
    open(tmp, "w", encoding="utf-8").write(t)
    url = "file://" + os.path.abspath(tmp)
    base = [chrome, "--headless=new", "--disable-gpu", "--hide-scrollbars", f"--window-size={w},{h}", "--virtual-time-budget=3000"]
    subprocess.run(base + [f"--force-device-scale-factor={sc}", f"--screenshot={os.path.abspath(out)}", url], capture_output=True)
    dom = subprocess.run(base + ["--dump-dom", url], capture_output=True, text=True).stdout
    m = re.search(r'<pre id="HCPOS"[^>]*>(.*?)</pre>', dom, re.S)
    pos = json.loads(H.unescape(m.group(1))) if m else []
    for e in pos:
        e["box"] = [round(v * sc) for v in e["box"]]
        for r in e["rows"]:
            r["box"] = [round(v * sc) for v in r["box"]]
    json.dump(pos, open(os.path.splitext(out)[0] + ".json", "w"), ensure_ascii=False, indent=1)
    print(f"{out} · 요소 {len(pos)}개 → {os.path.splitext(out)[0]}.json")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
