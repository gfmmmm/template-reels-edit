#!/usr/bin/env bash
# 도구 자동 설치 — doctor.sh 가 도구 ❌를 보면 먼저 이걸 돌린다. 없는 것만 설치하고, 사람 손이 필요한 것만 "→ 사용자:" 줄로 낸다.
# 사용: bash scripts/setup.sh
# 마지막 줄: "✅ 도구 준비 완료" 또는 "❌ 사용자 할 일 N개" (그 위에 "→ 사용자: …" 줄). 설치한 것은 "설치함: …" 한 줄.
# 맥(애플 칩): brew(ffmpeg·node), uv(yt-dlp·mlx-whisper), npm(capcut-cli)
# 맥(인텔)·윈도우: 받아쓰기는 whisper-ctranslate2. 윈도우는 winget(파이썬·ffmpeg·node·uv·git)
# 윈도우 분기는 실제 윈도우에서 아직 시험하지 않았다.
D="$(cd "$(dirname "$0")" && pwd)"
source "$D/env.sh"
installed=(); todo=()
has() { command -v "$1" >/dev/null 2>&1; }
ask() { todo+=("→ 사용자: $1"); }
wg() { winget install -e --id "$1" --silent --accept-source-agreements --accept-package-agreements >/dev/null 2>&1; }
refresh_path() { # 방금 깐 것이 잡히게
  if [ "$OS" = win ]; then for d in "$LAD/Microsoft/WinGet/Links" "$LAD"/Programs/Python/Python3*/ "$LAD"/Programs/Python/Python3*/Scripts "$HOME/AppData/Roaming/npm" "$HOME/.local/bin"; do [ -d "$d" ] && PATH="$d:$PATH"; done; export PATH; fi
}

[ "$OS" = other ] && { echo "→ 사용자: 맥이나 윈도우에서만 자동 설치가 돼요 (지금 컴퓨터: $(uname -s))"; echo "❌ 사용자 할 일 1개"; exit 1; }

# ── 1) 기본 도구 ──
if [ "$OS" = mac ]; then
  if ! xcode-select -p >/dev/null 2>&1; then
    xcode-select --install >/dev/null 2>&1
    ask "맥 기본 개발 도구가 없어요. 방금 뜬 설치 창에서 '설치'를 누르고, 끝나면 다시 불러 주세요."
  fi
  if ! has brew; then
    ask "Homebrew가 없어요. 터미널 앱에 아래 한 줄을 붙여 넣고 비밀번호를 넣은 뒤, 끝나면 다시 불러 주세요.
/bin/bash -c \"\$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\""
  fi
else
  has winget || ask "윈도우 설치 도구(winget)가 없어요. 마이크로소프트 스토어에서 '앱 설치 관리자(App Installer)'를 설치하고 다시 불러 주세요."
  if has winget; then
    has git || { wg Git.Git && installed+=("git"); }
    if [ -z "$PY" ]; then wg Python.Python.3.12 && installed+=("파이썬"); refresh_path; for c in python3 python "py -3"; do $c -c "import sys" >/dev/null 2>&1 && { PY="$c"; break; }; done; fi
    [ -n "$PY" ] || ask "파이썬을 설치했는데 아직 안 잡혀요. 클로드 코드를 완전히 껐다 켠 뒤 다시 불러 주세요."
  fi
fi

# ── 2) ffmpeg · node · uv ──
if [ "$OS" = mac ] && has brew; then
  for p in ffmpeg node uv; do has "$p" || { brew install "$p" >/dev/null 2>&1 && installed+=("$p") || ask "$p 설치가 안 됐어요 — 터미널에서 brew install $p 를 돌려 주세요"; }; done
elif [ "$OS" = win ] && has winget; then
  has ffmpeg || { wg Gyan.FFmpeg; refresh_path; has ffmpeg && installed+=("ffmpeg") || ask "ffmpeg 설치가 안 잡혀요. 클로드 코드를 껐다 켠 뒤 다시 불러 주세요."; }
  has node || { wg OpenJS.NodeJS.LTS; refresh_path; has node && installed+=("node") || ask "node 설치가 안 잡혀요. 클로드 코드를 껐다 켠 뒤 다시 불러 주세요."; }
  has uv || { wg astral-sh.uv; refresh_path; has uv && installed+=("uv") || ask "uv 설치가 안 잡혀요. 클로드 코드를 껐다 켠 뒤 다시 불러 주세요."; }
fi

# ── 3) uv 로 까는 것: yt-dlp · 받아쓰기 ──
if has uv; then
  has yt-dlp || { uv tool install yt-dlp >/dev/null 2>&1 && installed+=("yt-dlp") || ask "yt-dlp 설치 실패 — 인터넷 연결을 확인해 주세요"; }
  if [ "$OS" = mac ] && [ "$ARCH" = arm64 ]; then
    has mlx_whisper || { uv tool install mlx-whisper >/dev/null 2>&1 && installed+=("mlx_whisper") || ask "받아쓰기 도구(mlx-whisper) 설치 실패 — 인터넷 연결을 확인해 주세요"; }
  else
    has whisper-ctranslate2 || { uv tool install whisper-ctranslate2 >/dev/null 2>&1 && installed+=("whisper-ctranslate2") || ask "받아쓰기 도구(whisper-ctranslate2) 설치 실패 — 인터넷 연결을 확인해 주세요"; }
  fi
fi

# ── 4) capcut-cli ──
if has npm; then
  if ! has capcut || ! capcut describe --command compile 2>/dev/null | grep -q -- '--into'; then
    npm i -g capcut-cli@latest >/dev/null 2>&1 && installed+=("capcut-cli") || ask "capcut-cli 설치 실패 — 터미널에서 npm i -g capcut-cli@latest 를 돌려 주세요"
    refresh_path
  fi
fi

# ── 5) 파이썬 꾸러미: numpy(전부), opencv·rembg(윈도우) ──
if [ -n "$PY" ]; then
  $PY -c "import numpy" >/dev/null 2>&1 || { $PY -m pip install -q numpy >/dev/null 2>&1 && installed+=("numpy"); }
  if [ "$OS" = win ]; then
    $PY -c "import cv2" >/dev/null 2>&1 || { $PY -m pip install -q opencv-python >/dev/null 2>&1 && installed+=("opencv"); }
  fi
fi

# ── 6) CapCut 앱 ──
if [ "$OS" = mac ]; then [ -d /Applications/CapCut.app ] || ask "CapCut 앱이 없어요. capcut.com 에서 맥용 CapCut(9.x)을 설치해 주세요."
else [ -d "$LAD/CapCut" ] || [ -d "$HOME/AppData/Local/CapCut" ] || ask "CapCut 앱이 없어요. capcut.com 에서 윈도우용 CapCut(9.x)을 설치해 주세요."; fi

# ── 7) Remotion — 꾸러미(스킬 안 remotion/)가 있으면 [Remotion폴더]로 복사하고 npm install ──
REM="$($PY - "$SKILL_DIR" <<'PYEOF' 2>/dev/null
import re, sys, os
v = ""
for l in open(os.path.join(sys.argv[1], "환경.md"), encoding="utf-8"):
    m = re.match(r"\|\s*\[Remotion폴더\]\s*\|\s*(.*?)\s*\|", l)
    if m: v = re.split(r"\s+\(", m.group(1))[0].strip("\x60 ")  # 값 뒤 설명 괄호·코드 표시는 뗀다(platform_util.env_value 와 같게 — 안 떼면 괄호째 이름의 폴더에 깔린다)
print(os.path.expanduser(v or "~/Projects/reels-edit-remotion"))
PYEOF
)"
REM="${REM:-$HOME/Projects/reels-edit-remotion}"
if has npm; then
  if [ ! -f "$REM/package.json" ] && [ -f "$SKILL_DIR/remotion/package.json" ]; then
    mkdir -p "$(dirname "$REM")" && cp -R "$SKILL_DIR/remotion" "$REM" && installed+=("Remotion 소스 → $REM")
    [ -f "$REM/src/brand.ts" ] || { [ -f "$REM/src/brand.template.ts" ] && cp "$REM/src/brand.template.ts" "$REM/src/brand.ts"; }
  fi
  if [ -f "$REM/package.json" ] && [ ! -d "$REM/node_modules" ]; then
    (cd "$REM" && npm install >/dev/null 2>&1) && installed+=("Remotion 패키지(npm install)") || ask "Remotion 패키지 설치가 안 됐어요 — $REM 에서 npm install 을 돌려 주세요"
  fi
fi

chmod +x "$D"/*.sh 2>/dev/null
[ ${#installed[@]} -gt 0 ] && echo "설치함: $(IFS='·'; echo "${installed[*]}")"
if [ ${#todo[@]} -eq 0 ]; then echo "✅ 도구 준비 완료"; exit 0; fi
for t in "${todo[@]}"; do echo "$t"; done
echo "❌ 사용자 할 일 ${#todo[@]}개"; exit 1
