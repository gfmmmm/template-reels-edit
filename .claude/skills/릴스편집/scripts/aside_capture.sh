#!/usr/bin/env bash
# 자료화면 캡처 — aside 브라우저(사용자 로그인 브라우저)로 웹페이지를 열어 화면을 찍고 세로 자료화면용 PNG로 맞춘다.
# 사용: bash scripts/aside_capture.sh <주소> <출력.png> [--selector "CSS"] [--scroll 픽셀] [--wait 밀리초] [--full]
# --selector 그 요소만 찍는다(기사 본문, 표, 그래프 하나 등). 못 찾으면 화면 전체로 찍고 알린다
# --scroll 찍기 전에 아래로 내린다
# --full 페이지 전체 길이로 찍는다(스크롤 캡처)
# 결과: <출력.png>(원본 그대로) + <출력>_세로.png(1080 폭에 맞춘 흰 바탕 카드, 세로 1920 안) — 3단계 ③-A "실제 화면 캡처"에 쓴다.
# 주의: aside 는 사용자 로그인 상태로 연다. 개인 정보가 보이는 화면(메일·결제·DM)은 사용자가 시킨 때만 찍고, 찍은 뒤 가릴 곳을 확인한다.
D="$(cd "$(dirname "$0")" && pwd)"; source "$D/env.sh"
URL="$1"; OUT="$2"; shift 2 || { echo "사용: aside_capture.sh <주소> <출력.png> [옵션]"; exit 1; }
SEL=""; SCROLL=0; WAIT=1500; FULL=false
while [ $# -gt 0 ]; do case "$1" in --selector) SEL="$2"; shift 2;; --scroll) SCROLL="$2"; shift 2;; --wait) WAIT="$2"; shift 2;; --full) FULL=true; shift;; *) shift;; esac; done
command -v aside >/dev/null 2>&1 || { echo "❌ aside 가 없어요 — 0단계 (1) 11번(aside 설치·로그인)을 먼저 해 주세요"; exit 1; }
mkdir -p "$(dirname "$OUT")"
JS_URL="$($PY -c 'import json,sys;print(json.dumps(sys.argv[1]))' "$URL")"
JS_SEL="$($PY -c 'import json,sys;print(json.dumps(sys.argv[1]))' "$SEL")"
LOG="$(aside repl "const cU=$JS_URL, cS=$JS_SEL; const cT = await openTab(cU); await sleep($WAIT); if ($SCROLL>0) { await cT.evaluate(y => window.scrollBy(0, y), $SCROLL); await sleep(600); }
let cNote = 'page', cBox = '';
if (cS) { const r = await cT.evaluate(q => { const el = document.querySelector(q); if (!el) return null; el.scrollIntoView({ block: 'center' }); const b = el.getBoundingClientRect(); return [b.left, b.top, b.width, b.height, window.devicePixelRatio || 1]; }, cS);
  if (r && r[2] > 0 && r[3] > 0) { await sleep(400); const r2 = await cT.evaluate(q => { const b = document.querySelector(q).getBoundingClientRect(); return [b.left, b.top, b.width, b.height, window.devicePixelRatio || 1]; }, cS); cBox = r2.map(v => Math.round(v * 1000) / 1000).join(','); cNote = 'selector'; } else cNote = 'selector-miss'; }
const cB = await cT.screenshot({ fullPage: cBox ? false : $FULL });
await fs.mkdir('./artifacts', { recursive: true }); await fs.writeFile('./artifacts/capture.png', cB);
console.log('CAPDIR=' + pwd); console.log('CAPNOTE=' + cNote); console.log('CAPBOX=' + cBox); await closeTab(cT);" 2>&1)"
DIR="$(printf '%s\n' "$LOG" | sed -n 's/^CAPDIR=//p' | tail -1)"; NOTE="$(printf '%s\n' "$LOG" | sed -n 's/^CAPNOTE=//p' | tail -1)"
[ -n "$DIR" ] && [ -f "$DIR/artifacts/capture.png" ] || { echo "❌ 캡처 실패"; printf '%s\n' "$LOG" | tail -3; exit 1; }
BOX="$(printf '%s\n' "$LOG" | sed -n 's/^CAPBOX=//p' | tail -1)"
if [ -n "$BOX" ]; then
 # 요소 위치(CSS 픽셀) × 화면 배율 = 캡처 그림 픽셀. 위아래 여백 12px 붙여 잘라 낸다
  CROP="$($PY -c 'import sys;x,y,w,h,r=map(float,sys.argv[1].split(","));p=12;print("%d:%d:%d:%d"%((w+2*p)*r,(h+2*p)*r,max(0,(x-p)*r),max(0,(y-p)*r)))' "$BOX")"
  ffmpeg -v error -y -i "$DIR/artifacts/capture.png" -vf "crop=$CROP" -frames:v 1 "$OUT"
else cp "$DIR/artifacts/capture.png" "$OUT"; fi
[ "$NOTE" = selector-miss ] && echo "⚠️ 요소($SEL)를 못 찾아 화면 전체를 찍었어요"
# 세로 자료화면 카드: 흰 바탕 1080×1920, 가로 1010px(좌우 35px 여백)에 맞추고 세로는 220~1500px 안에 들어가게 줄인다
BASE="${OUT%.*}"
ffmpeg -v error -y -i "$OUT" -vf "scale='min(1010,iw)':'min(1280,ih*min(1010,iw)/iw)':force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:220+(1280-ih)/2:white" -frames:v 1 "${BASE}_세로.png"
echo "캡처: $OUT ($(ffprobe -v error -show_entries stream=width,height -of csv=p=0 "$OUT")) · 세로 카드: ${BASE}_세로.png · 출처: $URL"
