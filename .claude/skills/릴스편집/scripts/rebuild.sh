#!/usr/bin/env bash
# 컷(cutplan·edge_snap·gap_trim)을 다시 짠 뒤 3단계 효과·카드·자막·확인본까지 정해진 순서로 다시 만든다.
# (한 생활용품 계정 개선 루프: 컷을 고칠 때마다 효과 옮기기 → 끝맺음 → J컷 → 시연 시점 → 장면 쪼개기 → 카드 → 자막 → 효과음 →
# 조립 설계 → 확인본을 손으로 하나씩 돌리다 효과음이 0.9초 어긋나고 카드 길이가 0.014초 넘쳐 CapCut 조립이 멈췄다)
# 사용법: rebuild.sh <결과폴더> [--old-timemap 옛_timemap.json] [--max-chars 10] [--scale 0.5] [계정이 켠 기능들]
# 계정이 켠 기능(편집메뉴얼 0번 "켜는 공용 기능" 줄에 적힌 것만 넘긴다 — 충돌 점검: 튜토리얼형 계정과 부딪힌다):
# --caption-place 자막 높이 장면별(공용 66) · --rhythm 2.0 장면 리듬 상한(58) · --jcut J컷(60) · --snap 시연 시점(61, 시연 카드만) · --snap-all(61, 모션그래픽 카드도)
# 직접 찍은 시연 장면(screen_clip 카드) 계정용이다. 모션그래픽·화면 기록(Remotion) 카드는 이 스크립트가 다시 렌더하지 않는다 —
# 끝에 다시 렌더할 카드 목록을 알려 주면 3_효과 ③-A 7 렌더·pip_prepare 를 따로 한다.
# --old-timemap 컷을 고치기 전 timemap 사본 — 주면 remap.py 로 효과 시간을 먼저 옮긴다
# --max-chars 자막 글자 상한(계정 메뉴얼 5번, 기본 10)
# --scale 확인본 크기(0.5 검수용, 1 승인용 최종본_고화질)
# cutplan 은 계정마다 옵션이 달라 이 스크립트가 돌리지 않는다. 이 스크립트가 멈추면(끝맺음이 짧다 등) 안내대로 고치고 다시 돌린다.
set -euo pipefail
R="$(cd "$1" && pwd)"; shift
OLD=""; MAXC=10; CPLACE=0; RHY=0; SCALE=0.5; JCUT=0; SNAP=0
while [ $# -gt 0 ]; do case "$1" in
  --old-timemap) OLD="$2"; shift 2 ;; --max-chars) MAXC="$2"; shift 2 ;; --caption-place) CPLACE=1; shift ;;
  --rhythm) RHY="$2"; shift 2 ;; --scale) SCALE="$2"; shift 2 ;; --jcut) JCUT=1; shift ;; --snap) SNAP=1; shift ;; --snap-all) SNAP=2; shift ;; *) shift ;; esac; done
D="$(cd "$(dirname "$0")" && pwd)"; source "$D/env.sh"
cd "$R"
TALK=$($PY -c "import json,os;p=json.load(open('spec.json'))['tracks'][0]['items'][0]['path'];print(p if os.path.isabs(p) else os.path.abspath(p))")
step(){ echo "── $1"; }

step "말끝·첫소리 점검"; $PY "$D/edge_check.py" . "$TALK" | tail -6 || true   # 잘림 의심이 있으면 edge_check --fix → cutplan → rebuild 다시(공용 76)
[ -n "$OLD" ] && { step "효과 시간 옮기기"; $PY "$D/remap.py" . "$OLD" | tail -1 | cut -c1-120; }
if grep -qE '"role": "(react|end|result)"' overlays.json broll-plan.json 2>/dev/null; then
  step "끝맺음"; $PY "$D/ending.py" . || { echo "끝맺음이 짧다 — 위 안내대로 edge_fix 를 고치고 cutplan → rebuild.sh 다시"; exit 2; }
fi
step "컷 미리보기·얼굴";   $PY "$D/render_cut.py" . "$TALK" >/dev/null; $PY "$D/face_anchor.py" . | tail -1
[ "$JCUT" = 1 ] && { step "J컷"; $PY "$D/jcut.py" . | tail -1; }
[ "$SNAP" != 0 ] && { step "시연 시점"; $PY "$D/broll_snap.py" . $([ "$SNAP" = 2 ] && echo --all) | tail -1; }
[ -f broll-plan.json ] && { step "대사 맞춤(모션그래픽)"; $PY "$D/cue_sync.py" . | head -8 || true; }
if [ "$RHY" != "0" ]; then step "장면 쪼개기"; $PY "$D/shot_rhythm.py" . --max "$RHY" --fix | tail -1; fi
if [ -f screens.json ]; then
step "카드"
$PY - <<'P'
import json
S=json.load(open("screens.json")); L=S if isinstance(S,list) else S["screens"]
B={c["id"]:c for c in json.load(open("broll-plan.json"))["cards"]}
for s in L:
    if s["id"] in B: s["end"]=round(round((B[s["id"]]["end"]-B[s["id"]]["start"])*30)/30,4)
json.dump(S,open("screens.json","w"),ensure_ascii=False,indent=1)
P
$PY "$D/screen_clip.py" . >/dev/null
fi
step "자막"; $PY "$D/captions.py" . --max-chars "$MAXC" | tail -1
[ "$CPLACE" = 1 ] && $PY "$D/caption_place.py" . | tail -1
[ -f sfx_후보.json ] && { step "효과음"; $PY "$D/sfx_plan.py" . sfx_후보.json | grep -v "^$" | head -2; }
step "조립 설계"; $PY "$D/build_spec.py" . zoom.json | tail -1
step "확인본"
mkdir -p preview
$PY - <<'P'
import json,os
p=json.load(open("preview/overlay_props.json")) if os.path.exists("preview/overlay_props.json") else {"title":"","titleDur":0,"titleFirstWhite":False}
t=json.load(open("timemap.json")); p["duration"]=round(t[-1]["start"]+t[-1]["duration"],3)
p["captions"]=json.load(open("captions.json")); p["overlays"]=json.load(open("overlays.json")) if os.path.exists("overlays.json") else []
if os.path.exists("title_dur.txt"): p["titleDur"]=float(open("title_dur.txt").read())  # remap 이 옮긴 상단 제목 길이
json.dump(p,open("preview/overlay_props.json","w"),ensure_ascii=False)
P
REM=$($PY -c "import sys;sys.path.insert(0,'$D');import platform_util as pu;print(pu.remotion_dir())")
(cd "$REM" && npx remotion render src/index.ts overlay-any "$R/preview/자막레이어.mov" --props="$R/preview/overlay_props.json" \
  --codec=prores --prores-profile=4444 --pixel-format=yuva444p10le --image-format=png --log=error)
$PY "$D/render_check.py" . preview/자막레이어.mov --scale "$SCALE" | tail -1
step "장면 점검"; $PY "$D/scene_check.py" . | tail -4 || true   # 끼인 장면·첫 화면 잘린 얼굴(공용 72)
[ "$RHY" != "0" ] && $PY "$D/shot_rhythm.py" . --max "$RHY" | head -1
$PY - <<'P'
import json
cards=json.load(open("broll-plan.json"))["cards"]
rem=[c["id"] for c in cards if c.get("component") not in ("Screen",)]
if rem: print("⚠ 모션그래픽·화면 기록 카드는 다시 렌더하지 않았다(장면 안 시간은 remap 이 옮김) — 3_효과 ③-A 7 렌더·pip_prepare:", ", ".join(rem))
P
echo "끝 — CapCut 조립은 3_효과 ③-D(capcut_fill → capcut_finish → preview_match)"
