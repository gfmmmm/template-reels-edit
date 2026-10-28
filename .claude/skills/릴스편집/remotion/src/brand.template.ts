// 릴스편집 브랜드 값 — 자료화면 카드는 이 파일의 값만 쓴다.
// 이 파일을 `brand.ts`로 복사한 뒤, 1단계(편집메뉴얼)에서 레퍼런스·정답지로 잰 값으로 채운다. 근거는 편집메뉴얼 5·6·11번.
// 바꾸면 편집메뉴얼 14번 변경 이력에 적는다. 아래 값은 "채우기 전 기본값"이다 — 그대로 두면 흰 바탕·검정 글자·노랑 강조로 나온다.

export const colors = {
  white: "#FFFFFF",
  lime: "#90F820", /* 비교 이름표 색 — 레퍼런스에서 잰 값으로 */
  yellow: "#FFD400", /* 강조색 — 정답지 자막 강조색으로 */
  red: "#E53935", /* 경고·반전 — 정답지에서 잰 값으로 */
  sky: "#3A86FF", /* 아이콘 보조색 */
  dark: "#1E1E1E", /* 번호 장 카드 배경 */
  stroke: "#000000",
};

export const fonts = {
  /* 확인본 자막 글꼴 — CapCut 자막과 같은 글꼴 이름(편집메뉴얼 5번). 글꼴 파일(.ttf/.otf)을 public/fonts/ 에 넣고 파일 이름을 적는다 */
  caption: "(채울 것: 자막 글꼴 이름)",
  captionFile: "fonts/(채울 것: 글꼴 파일 이름).ttf",
  /* 카드 글자 — 자막과 비슷한 굵은 고딕. 레퍼런스 글꼴을 aside 로 찾아 적는다 */
  heading: "Pretendard, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif",
  weight: 800,
};

export const mood = "(채울 것: 편집메뉴얼 6번 — 예: 깔끔한 정보형, 흰 바탕 납작한 2D 아이콘, 굵은 고딕, 노랑 강조)";

export const broll = {
  perVideo: { min: 9, target: 11, max: 13 }, /* 자료화면 개수 — 편집메뉴얼 6·12번 */
  avgGapSec: 4.5,
  durSec: { min: 0.5, max: 2.0 },
  popInSec: 0.12, // 작게 → 크게 튀어나오기
  fadeOut: false, // 컷과 함께 사라짐
  anchor: { x: 540, y: 1300 }, // 자막 바로 아래 가슴 앞
  maxWidth: 650, // 여러 개 합친 폭
  iconWidth: { min: 240, max: 300 },
  yRange: { from: 1180, to: 1500 },
};

// 번호 장 카드 — 번호를 매기는 영상에서만 (편집메뉴얼 6번)
export const chapterCard = {
  overlay: "#1E1E1E",
  overlayOpacity: 0.85,
  textColor: "#FFD400", /* 강조색과 같게 */
  durSec: { min: 1.0, max: 1.7 },
};

// 아이콘은 Flaticon 납작한 2D 컬러 아이콘이 먼저, 없을 때만 아래 문구로 생성
export const aiImageStyle =
  "flat 2D vector icon illustration, clean thick outlines, simple shapes, white background, " +
  "main colors #FFD400 yellow and #3A86FF sky blue, no text"; /* 색은 위 colors 와 맞춘다 */

// 가리면 안 되는 영역 (1080×1920) — 인스타 화면 공통이라 그대로 둔다. rightButtons.width 180은 추정값.
export const safeZone = {
  top: 220,
  bottom: 420,
  side: 35,
  rightButtons: { fromY: 990, toY: 1500, width: 180 },
};

export const canvas = { width: 1080, height: 1920, fps: 30 };
