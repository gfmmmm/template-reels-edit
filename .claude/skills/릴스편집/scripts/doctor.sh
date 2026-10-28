#!/usr/bin/env bash
# 상태 진단 — 스킬이 불리면 맨 먼저 돌린다. 이 컴퓨터에 도구가 다 있는지, 학습(편집메뉴얼·프리셋·효과음·brand.ts)이 됐는지 보고
# 마지막 줄에 "다음 할 일: 설치 | 학습 | 편집 가능" 하나를 찍는다.
# 먼저 setup.sh 로 없는 도구를 그 자리에서 설치하고(자가 수리), 드라이브 파일이 실제로 읽히는지 본 뒤, 남은 일을 "→ AI:" / "→ 사용자:" 줄로 낸다.
# "→ AI:" 로 시작하면 이 스킬을 돌리는 AI가 사용자에게 묻지 않고 바로 한다
# "→ 사용자:" 로 시작하면 사용자에게 그 한 가지만 부탁한다(설치 창·비밀번호·키·앱 설치)
# 사용: bash scripts/doctor.sh [--json <경로>] [--write-env] [--no-install] [--force] [--reset]
# (기본) 이 컴퓨터에서 한 번 "편집 가능"을 통과했으면(통과표시 파일이 있으면) 진단을 건너뛰고 바로 "다음 할 일: 편집 가능"만 찍는다
# --force 통과표시가 있어도 전체 진단을 다시 돈다(세팅 요청·편집메뉴얼 다시·도중에 도구가 안 될 때)
# --reset 통과표시를 지운다(다음 호출은 전체 진단)
# --json <경로> 같은 내용을 JSON 파일로도 쓴다
# --write-env 환경.md 의 [운영체제]·[받아쓰기 엔진] 행 값을 이 컴퓨터 것으로 채운다(행이 없으면 "## 경로" 표 끝에 추가)
# --no-install setup.sh(자동 설치)를 건너뛰고 보기만 한다
# 윈도우 분기는 실제 윈도우에서 아직 시험하지 않았다.
D="$(cd "$(dirname "$0")" && pwd)"
source "$D/env.sh"
JSON=""; WRITE_ENV=0; NO_INSTALL=0; FORCE=0
# 통과표시: 컴퓨터마다 하나(스킬 폴더는 드라이브로 여러 컴퓨터가 같이 쓰므로 여기 두지 않는다)
OK_MARK="${HOME}/.cache/릴스편집/doctor_ok"
while [ $# -gt 0 ]; do
  case "$1" in --json) JSON="$2"; shift 2 ;; --write-env) WRITE_ENV=1; shift ;; --no-install) NO_INSTALL=1; shift ;; --force) FORCE=1; shift ;; --reset) rm -f "$OK_MARK"; echo "통과표시를 지웠어요. 다음엔 전체 진단을 돌아요."; exit 0 ;; *) shift ;; esac
done
# ── 최초 1회만: 이 컴퓨터에서 이미 "편집 가능"을 통과했으면 건너뛴다 ──
if [ "$FORCE" = 0 ] && [ "$WRITE_ENV" = 0 ] && [ -z "$JSON" ] && [ -f "$OK_MARK" ]; then
  echo "릴스편집 상태 진단 — $(head -1 "$OK_MARK") 에 이 컴퓨터에서 통과했어요. 건너뜁니다 (다시 보려면 --force)."
  echo "다음 할 일: 편집 가능"
  exit 0
fi
TODO=(); FIXED=""
# ── 자가 수리: 없는 도구는 setup.sh 가 그 자리에서 설치한다 ──
if [ "$NO_INSTALL" = 0 ]; then
  SETUP_OUT="$(bash "$D/setup.sh" 2>&1)"
  FIXED="$(printf '%s\n' "$SETUP_OUT" | grep '^설치함: ' | sed 's/^설치함: //')"
  while IFS= read -r l; do case "$l" in "→ 사용자:"*) TODO+=("$l");; esac; done <<<"$SETUP_OUT"
  source "$D/env.sh"   # 방금 깐 도구가 잡히게 다시 읽는다
fi
# ── 드라이브 파일이 실제로 읽히나 — 구글 드라이브 앱은 "오프라인 사용"이 꺼져 있으면 파일이 이름만 있고 내용이 안 내려와 읽기가 멈춘다 ──
SLOW=""
for f in "$SKILL_DIR/SKILL.md" "$D/cutplan.py" "$SKILL_DIR"/sfx/files/01.*; do
  [ -e "$f" ] || continue
  ( head -c 64 "$f" >/dev/null 2>&1 ) & pid=$!; n=0
  while kill -0 $pid 2>/dev/null && [ $n -lt 20 ]; do sleep 0.5; n=$((n+1)); done
  kill -0 $pid 2>/dev/null && { kill $pid 2>/dev/null; SLOW="$SLOW $(basename "$f")"; }
done
[ -n "$SLOW" ] && TODO+=("→ 사용자: 스킬 파일($SLOW)이 안 내려와요 — 구글 드라이브 앱에서 이 폴더를 오른쪽 클릭 → '오프라인 사용 가능'을 켜고 잠시 뒤 다시 해 주세요")

has() { command -v "$1" >/dev/null 2>&1; }
TOOL_BAD=0
TOOLS=()   # "이름|상태|설명"  상태: ok / bad / opt(선택이라 없어도 됨) / info
add() { TOOLS+=("$1|$2|$3"); [ "$2" = bad ] && TOOL_BAD=1; return 0; }

# ── 컴퓨터 ──
case "$OS" in mac) OSNAME="맥";; win) OSNAME="윈도우";; *) OSNAME="$(uname -s)";; esac
if [ "$OS" = mac ] && [ "$ARCH" = arm64 ]; then CHIP="애플 칩"; elif [ "$OS" = mac ]; then CHIP="인텔 칩"; else CHIP="$ARCH"; fi
[ "$OS" = other ] && add "운영체제" bad "$OSNAME 은 지원하지 않아요 (맥·윈도우만)"

# ── 도구 ──
if has capcut && capcut describe --command compile 2>/dev/null | grep -q -- '--into'; then add "capcut-cli" ok "$(capcut -v 2>/dev/null | head -1)"
elif has capcut; then add "capcut-cli" bad "너무 옛 판이에요 (compile --into 없음) → npm i -g capcut-cli@latest"
else add "capcut-cli" bad "없음 → npm i -g capcut-cli@latest"; fi

if [ "$OS" = mac ]; then
  CV="$(defaults read /Applications/CapCut.app/Contents/Info.plist CFBundleShortVersionString 2>/dev/null)"
  if [ -z "$CV" ]; then add "CapCut 앱" bad "없음 → capcut.com 에서 설치"
  elif [ "${CV%%.*}" -ge 10 ] 2>/dev/null; then add "CapCut 앱" bad "$CV — 10 이상은 프로젝트 쓰기가 막혀요"
  else add "CapCut 앱" ok "$CV"; fi
elif [ "$OS" = win ]; then
  if [ -d "${LAD:-$HOME/AppData/Local}/CapCut" ] || [ -d "$CAPCUT_DRAFTS" ]; then add "CapCut 앱" ok "설치 폴더 있음"
  else add "CapCut 앱" bad "없음 → capcut.com 에서 설치"; fi
fi

if has ffmpeg && has ffprobe; then
  if ffmpeg -hide_banner -filters 2>/dev/null | grep -q " zscale "; then ZS="zscale 있음"; else ZS="zscale 없음"; fi
  if [ "$OS" = mac ] || [ "$ZS" = "zscale 있음" ]; then add "ffmpeg" ok "$ZS$( [ "$OS" = mac ] && echo ' (맥은 HDR 변환에 avconvert 사용)')"
  else add "ffmpeg" bad "$ZS — HDR 변환이 안 돼요 → winget install Gyan.FFmpeg (full 판)"; fi
else add "ffmpeg" bad "없음 → 맥 brew install ffmpeg / 윈도우 winget install Gyan.FFmpeg"; fi

case "$WHISPER_ENGINE" in
  mlx) add "받아쓰기" ok "mlx_whisper (애플 칩)";;
  faster) add "받아쓰기" ok "faster_whisper / whisper-ctranslate2";;
  *) if [ "$OS" = mac ] && [ "$ARCH" = arm64 ]; then add "받아쓰기" bad "없음 → uv tool install mlx-whisper"
     else add "받아쓰기" bad "없음 → uv tool install whisper-ctranslate2"; fi;;
esac
[ "$OS" = mac ] && { has avconvert && add "avconvert(HDR 변환)" ok "있음" || add "avconvert(HDR 변환)" bad "맥 기본 도구가 안 보여요"; }
has yt-dlp && add "yt-dlp" ok "있음" || add "yt-dlp" bad "없음 → uv tool install yt-dlp"
has node && has npm && add "node/npm" ok "$(node -v 2>/dev/null)" || add "node/npm" bad "없음 → 맥 brew install node / 윈도우 winget install OpenJS.NodeJS.LTS"
[ -n "$PY" ] && add "파이썬" ok "$($PY -c 'import sys;print(sys.version.split()[0])' 2>/dev/null)" || add "파이썬" bad "없음 → 맥 xcode-select --install / 윈도우 winget install Python.Python.3.12"
if [ "$OS" = mac ]; then has swiftc && add "swiftc(얼굴·인물 인식)" ok "있음" || add "swiftc(얼굴·인물 인식)" bad "없음 → xcode-select --install"; fi
if [ -n "$PY" ] && $PY -c "import numpy" >/dev/null 2>&1; then add "numpy" ok "있음"
elif [ -n "$WHISPER_PY" ] && "$WHISPER_PY" -c "import numpy" >/dev/null 2>&1; then add "numpy" ok "받아쓰기 파이썬에 있음 (export_compare 는 그 파이썬으로)"
else add "numpy" bad "없음 → $PY -m pip install numpy"; fi
if [ -n "$PY" ] && $PY -c "import cv2" >/dev/null 2>&1; then add "opencv(cv2)" ok "있음"
elif [ "$OS" = mac ]; then add "opencv(cv2)" opt "없음 — 맥은 CapCut 화면 자동 검수에만 필요 (pip install opencv-python)"
else add "opencv(cv2)" bad "없음 — 윈도우는 얼굴 기준 확대에 필요 → $PY -m pip install opencv-python"; fi
if [ "$OS" != mac ]; then
  if [ -n "$PY" ] && $PY -c "import rembg" >/dev/null 2>&1; then add "rembg(인물 오려내기)" ok "있음"
  else add "rembg(인물 오려내기)" opt "없음 — 인물 창을 오려내지 않고 넣어요 (pip install rembg pillow)"; fi
fi
if ls -d "$HOME"/.claude/plugins/cache/claude-video/watch/*/skills/watch >/dev/null 2>&1; then add "/watch 플러그인(영상 장면·설명)" ok "있음"
else add "/watch 플러그인(영상 장면·설명)" bad "없음 → claude plugin marketplace add bradautomates/claude-video 뒤 claude plugin install watch@claude-video (1단계 레퍼런스 분석에 필요)"; fi
if command -v aside >/dev/null 2>&1; then add "aside(웹 캡처·출처 찾기)" ok "있음"; else add "aside(웹 캡처·출처 찾기)" opt "없음 — 웹 화면 캡처·출처 찾기를 쓸 때만 (0단계 (1) 11번)"; fi
if grep -q "^GEMINI_API_KEY=." "$HOME/.config/watch/.env" 2>/dev/null; then add "Gemini 키" ok "~/.config/watch/.env"; else add "Gemini 키" opt "없음 — 레퍼런스 분석(1단계)에 필요. 0단계 (3)에서 받는다"; fi
if [ -n "${OPENAI_API_KEY:-}" ] || grep -q "OPENAI_API_KEY=." "$HOME/.zshrc" "$HOME/.bashrc" "$HOME/.bash_profile" 2>/dev/null; then add "OpenAI 키(GPT Image)" ok "있음"; else add "OpenAI 키(GPT Image)" opt "없음 — AI 그림이 필요한 장면에만"; fi
NARR_ENV="$HOME/.config/reels-edit/.env"
if grep -q "^FISH_API_KEY=." "$NARR_ENV" 2>/dev/null; then
  if grep -qE '^\| \[나레이션 목소리\] \| *[^ (|]' "$SKILL_DIR/환경.md" 2>/dev/null || grep -q "^FISH_VOICE_ID=." "$NARR_ENV"; then add "나레이션(Fish Audio) 키·목소리" ok "있음"
  else add "나레이션(Fish Audio) 키·목소리" opt "키는 있는데 목소리 id 가 없음 — fish.audio 본인 목소리 모델 id 를 환경.md [나레이션 목소리]에"; fi
else add "나레이션(Fish Audio) 키·목소리" opt "없음 — 나레이션을 쓸 때만. ~/.config/reels-edit/.env 에 FISH_API_KEY=, 환경.md 에 [나레이션 목소리]"; fi
if [ "$OS" = win ]; then add "자동 내보내기·화면 검수" info "윈도우: 내보내기·화면 검수는 사용자가 직접"; fi

# ── 상태(학습) — 환경.md·편집메뉴얼·프리셋·효과음·Remotion ──
STATE_JSON="$($PY - "$SKILL_DIR" "$OS" "$WHISPER_ENGINE" "$WRITE_ENV" <<'PYEOF'
import json, os, re, sys, glob
skill, osk, eng, write_env = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] == "1"
rows, bad = [], False
def add(name, ok, note):
    global bad
    rows.append({"name": name, "ok": ok, "note": note})
    if not ok: bad = True
envp = os.path.join(skill, "환경.md")
vals, lines = {}, []
if os.path.exists(envp):
    lines = open(envp, encoding="utf-8").read().split("\n")
    for l in lines:
        m = re.match(r"\|\s*(\[[^\]]+\])\s*\|\s*(.*?)\s*\|\s*$", l)
        if m: vals[m.group(1)] = m.group(2)
def resolve(v):
    for k, x in vals.items():
        if k in v: v = v.replace(k, x)
    return os.path.expanduser(v)
EMPTY = ("", "(채울 것)", "미정", "없음")
for k in ("[결과루트]", "[Remotion폴더]", "[효과음팔레트]", "[정답지]", "[레퍼런스]"):
    v = vals.get(k)
    if v is None or v.strip() in EMPTY: add(f"환경.md {k}", False, "비어 있음 → 0단계 끝 질문으로 채운다")
    else: add(f"환경.md {k}", True, v[:60])
# 편집메뉴얼
mp = os.path.join(skill, "편집메뉴얼.md")
if not os.path.exists(mp): add("편집메뉴얼.md", False, "없음 → 1단계(레퍼런스 분석)")
else:
    t = open(mp, encoding="utf-8").read()
    heads = re.split(r"^## (\d+)\.", t, flags=re.M)
    n = (len(heads) - 1) // 2
    empty = [heads[i] for i in range(1, len(heads), 2) if len(re.sub(r"\s", "", heads[i + 1])) < 20]
    if "(채울 것)" in t or n < 14 or empty: add("편집메뉴얼.md", False, f"항목 {n}/14, 빈 항목 {empty or '없음'}, '(채울 것)' {'있음' if '(채울 것)' in t else '없음'} → 1단계")
    else: add("편집메뉴얼.md", True, "14개 항목 채워짐")
pr = glob.glob(os.path.join(skill, "presets", "*.json"))
add("자막 프리셋(presets/)", bool(pr), f"{len(pr)}개" if pr else "없음 → 1단계(정답지에서 떠낸다)")
tp = glob.glob(os.path.join(skill, "sfx", "templates", "*.json"))
if not tp: add("효과음 템플릿(sfx/templates/)", False, "없음 → 0단계 (2) 효과음 팔레트")
else:
    missing = 0
    for f in tp:
        try: j = json.load(open(f, encoding="utf-8"))
        except Exception: missing += 1; continue
        m = j.get("material") or {}
        p = (m.get("data") or {}).get("path") if isinstance(m.get("data"), dict) else m.get("path")
        p = p or ""
        if not p or not os.path.exists(p): missing += 1
    if missing: add("효과음 템플릿(sfx/templates/)", False, f"{len(tp)}개 중 {missing}개가 이 컴퓨터에 없는 소리 파일을 가리켜요 → scripts/sfx_register.py")
    else: add("효과음 템플릿(sfx/templates/)", True, f"{len(tp)}개, 소리 파일 모두 있음")
rem = resolve(re.split(r"\s+\(", vals.get("[Remotion폴더]", "~/Projects/reels-edit-remotion"))[0].strip("\x60 "))  # 설명 괄호·코드 표시는 뗀다(setup.sh·platform_util 와 같게)
add("Remotion node_modules", os.path.isdir(os.path.join(rem, "node_modules")), rem if os.path.isdir(os.path.join(rem, "node_modules")) else f"{rem} 에 설치 안 됨 → 그 폴더에서 npm install")
add("brand.ts", os.path.exists(os.path.join(rem, "src", "brand.ts")), "있음" if os.path.exists(os.path.join(rem, "src", "brand.ts")) else "없음 → 1단계 끝(brand.ts)")
# --write-env
if write_env and os.path.exists(envp):
    osname = {"mac": "맥", "win": "윈도우"}.get(osk, osk)
    engname = {"mlx": "mlx_whisper(애플 칩)", "faster": "faster_whisper / whisper-ctranslate2"}.get(eng, "없음")
    want = {"[운영체제]": osname, "[받아쓰기 엔진]": engname}
    out, in_path, inserted = [], False, set()
    for i, l in enumerate(lines):
        m = re.match(r"\|\s*(\[[^\]]+\])\s*\|", l)
        if m and m.group(1) in want:
            out.append(f"| {m.group(1)} | {want[m.group(1)]} |"); inserted.add(m.group(1)); continue
        if l.startswith("## 경로"): in_path = True
        elif l.startswith("## ") and in_path:
 # 경로 표 끝: 표 뒤 빈 줄 앞에 넣는다
            while out and out[-1].strip() == "": out.pop()
            for k, v in want.items():
                if k not in inserted: out.append(f"| {k} | {v} |"); inserted.add(k)
            out.append(""); in_path = False
        out.append(l)
    for k, v in want.items():
        if k not in inserted: out.append(f"| {k} | {v} |")
    open(envp, "w", encoding="utf-8").write("\n".join(out))
print(json.dumps({"rows": rows, "bad": bad}, ensure_ascii=False))
PYEOF
)"
STATE_BAD="$(printf '%s' "$STATE_JSON" | $PY -c 'import json,sys;print(1 if json.load(sys.stdin)["bad"] else 0)')"

# ── 출력 ──
echo "릴스편집 상태 진단"
echo "컴퓨터: $OSNAME ($CHIP) · 파이썬: ${PY:-없음} · 받아쓰기: $WHISPER_ENGINE"
echo "CapCut 프로젝트 폴더: $CAPCUT_DRAFTS"
echo
echo "[도구]"
for t in "${TOOLS[@]}"; do
  IFS='|' read -r n s d <<<"$t"
  case "$s" in ok) m="✅";; bad) m="❌";; opt) m="⚪";; *) m="ℹ️";; esac
  echo "  $m $n — $d"
done
echo
echo "[학습 상태]"
printf '%s' "$STATE_JSON" | $PY -c '
import json,sys
for r in json.load(sys.stdin)["rows"]:
    mark = "✅" if r["ok"] else "❌"
    print("  " + mark + " " + r["name"] + " — " + r["note"])'
echo
if [ "$TOOL_BAD" = 1 ]; then NEXT="설치"; elif [ "$STATE_BAD" = 1 ]; then NEXT="학습"; else NEXT="편집 가능"; fi
# ── 남은 일: 도구 ❌는 설치 안내, 학습 ❌는 단계 안내 — AI 가 그대로 따라 한다 ──
if [ "$TOOL_BAD" = 1 ]; then
  for t in "${TOOLS[@]}"; do IFS='|' read -r n s d <<<"$t"; [ "$s" = bad ] && TODO+=("→ AI: $n — $d (0_설치.md (1)번 표대로 설치하고 doctor 를 다시 돌린다)"); done
elif [ "$STATE_BAD" = 1 ]; then
  while IFS= read -r l; do [ -n "$l" ] && TODO+=("$l"); done <<<"$(printf '%s' "$STATE_JSON" | $PY -c '
import json,sys
for r in json.load(sys.stdin)["rows"]:
    if not r["ok"]:
        n = r["note"]
        step = "1_편집메뉴얼만들기.md" if "1단계" in n else ("0_설치.md" if "0단계" in n else "")
        print("→ AI: " + r["name"] + " — " + n + ((" → " + step) if step else ""))')"
fi
[ -n "$FIXED" ] && echo "고침(자동 설치): $FIXED"
if [ ${#TODO[@]} -gt 0 ]; then echo "[남은 일 ${#TODO[@]}개]"; for t in "${TODO[@]}"; do echo "  $t"; done; echo; fi
[ -n "$SLOW" ] && NEXT="설치"
[ "$WRITE_ENV" = 1 ] && echo "환경.md 의 [운영체제]·[받아쓰기 엔진] 을 채웠어요."
if [ -n "$JSON" ]; then
  TOOLS_STR="$(printf '%s\n' "${TOOLS[@]}")"
  TOOLS_STR="$TOOLS_STR" STATE_JSON="$STATE_JSON" NEXT="$NEXT" OSNAME="$OSNAME" CHIP="$CHIP" $PY - "$JSON" <<'PYEOF'
import json, os, sys
tools = []
for l in os.environ["TOOLS_STR"].split("\n"):
    if not l.strip(): continue
    n, s, d = l.split("|", 2)
    tools.append({"name": n, "status": s, "note": d})
st = json.loads(os.environ["STATE_JSON"])
json.dump({"os": os.environ["OSNAME"], "chip": os.environ["CHIP"], "python": os.environ.get("PY"), "whisper": os.environ.get("WHISPER_ENGINE"),
           "capcut_drafts": os.environ.get("CAPCUT_DRAFTS"), "tools": tools, "state": st["rows"], "next": os.environ["NEXT"]},
          open(sys.argv[1], "w", encoding="utf-8"), ensure_ascii=False, indent=1)
PYEOF
fi
if [ "$NEXT" = "편집 가능" ]; then
  mkdir -p "$(dirname "$OK_MARK")" && { date '+%Y-%m-%d %H:%M'; echo "$(hostname) · $OSNAME · $CHIP"; } > "$OK_MARK"
else
  rm -f "$OK_MARK"
fi
echo "다음 할 일: $NEXT"
