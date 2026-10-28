// 결과 보고서 장면: 실제 AI 결과 화면(화면 기록 9/17 12:32·12:48)을 HTML로 다시 그려
// ① 글자가 선명하고 크게 ② 사람이 쓰는 것처럼(커서 이동·클릭·형광펜·토글) ③ 카드가 겹치는 깊이감(기울이지는 않는다 — 사용자).
// 대사마다 화면을 바꾸면 너무 빨라 안 읽힌다(사용자) → 큰 덩어리 3장(문제·개선 / 데이터 / 유지·끊기)만 바꾸고, 그 안에서 움직임으로 짚는다.
// 글자는 화면 기록에 실제로 있는 문구만 옮긴다(지어내지 않는다). 인물 아래 창은 PersonPip.
// 일반화: 영상마다 바뀌는 글·데이터는 전부 props.content로 받는다(broll-plan.json에 적는다). 틀·움직임만 이 파일에.
import React from "react";
import { AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { PersonPip } from "./scene";

const BG = "#F3F4F6";
const INK = "#1A1A1A";
const SUB = "#6B7280";
const BLUE = "#2F55D4";
const GREEN = "#2E7D4F";
const RED = "#B3261E";
const SANS = "'Apple SD Gothic Neo', Pretendard, sans-serif";
const SERIF = "'AppleMyungjo', 'Nanum Myeongjo', serif";

const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

// 브라우저 창 틀(실제 화면 기록의 Arc 창 모양을 단순화)
const Window: React.FC<{ children: React.ReactNode; scroll?: number; height?: number; title: string; tool: string }> = ({ children, scroll = 0, height = 760, title, tool }) => (
  <div style={{ width: 900, height, background: "#fff", borderRadius: 28, overflow: "hidden",
    boxShadow: "0 30px 70px rgba(15,25,50,0.16), 0 4px 14px rgba(15,25,50,0.08)", fontFamily: SANS }}>
    <div style={{ height: 58, display: "flex", alignItems: "center", gap: 10, padding: "0 22px", borderBottom: "1px solid #EEF0F3", background: "#FAFAFB" }}>
      {["#FF5F57", "#FEBC2E", "#28C840"].map((c) => <div key={c} style={{ width: 16, height: 16, borderRadius: 8, background: c }} />)}
      <div style={{ marginLeft: 18, fontSize: 20, color: SUB, fontWeight: 600 }}>{title}</div>
      <div style={{ marginLeft: "auto", fontSize: 18, fontWeight: 700, color: INK, background: "#F1F2F4", padding: "6px 14px", borderRadius: 14 }}>Ask {tool}</div>
    </div>
 {/* 스크롤해도 글이 창 머리 위로 올라오지 않게 본문만 잘라 보인다 */}
    <div style={{ height: height - 58, overflow: "hidden" }}>
      <div style={{ padding: "34px 44px", transform: `translateY(${-scroll}px)` }}>{children}</div>
    </div>
  </div>
);

const Eyebrow: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{ fontSize: 20, letterSpacing: 4, color: BLUE, fontWeight: 800 }}>{children}</div>
);
const H1: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <div style={{ fontFamily: SERIF, fontSize: 58, fontWeight: 800, color: INK, margin: "12px 0 10px", letterSpacing: -1 }}>{children}</div>
);

// 형광펜: p(0~1)만큼 왼쪽부터 칠한다
const Mark: React.FC<{ p: number; color?: string; children: React.ReactNode }> = ({ p, color = "rgba(255,214,10,0.55)", children }) => (
  <span style={{ backgroundImage: `linear-gradient(${color},${color})`, backgroundRepeat: "no-repeat",
    backgroundSize: `${p * 100}% 42%`, backgroundPosition: "0 88%" }}>{children}</span>
);

// 마우스 커서 + 클릭 물결
const Cursor: React.FC<{ x: number; y: number; click: number }> = ({ x, y, click }) => (
  <div style={{ position: "absolute", left: x, top: y, pointerEvents: "none" }}>
    {click > 0 && click < 1 && (
      <div style={{ position: "absolute", left: -30 * click, top: -30 * click, width: 60 * click, height: 60 * click, borderRadius: "50%",
        border: `4px solid rgba(47,85,212,${1 - click})` }} />
    )}
    <svg width="46" height="46" viewBox="0 0 24 24" style={{ filter: "drop-shadow(0 3px 4px rgba(0,0,0,0.35))", transform: `scale(${1 - 0.12 * Math.sin(Math.PI * Math.min(1, click * 2))})` }}>
      <path d="M4 2 L4 19 L8.5 14.8 L11.6 21.5 L14.4 20.3 L11.3 13.7 L17.5 13.5 Z" fill="#111" stroke="#fff" strokeWidth="1.4" strokeLinejoin="round" />
    </svg>
  </div>
);

// 카드 쌓기: 오른쪽에서 들어오고, 다음 카드가 오면 뒤로 물러나 작아지고 흐려진다(기울기 없음)
const Stack: React.FC<{ enterAt: number; leaveAt: number; children: React.ReactNode; fps: number; f: number }> = ({ enterAt, leaveAt, children, fps, f }) => {
  const e = spring({ frame: f - enterAt * fps, fps, config: { damping: 17, stiffness: 140 } });
  const l = spring({ frame: f - leaveAt * fps, fps, config: { damping: 20, stiffness: 120 } });
  if (f < enterAt * fps) return null;
  if (l > 0.98) return null;
  const x = (1 - e) * 700 - l * 60;
  const y = -l * 70;
  const sc = 1 - 0.08 * l;
  return (
    <div style={{ position: "absolute", left: 90, top: 250, transform: `translate(${x}px, ${y}px) scale(${sc})`,
      opacity: Math.min(1, e * 1.5) * (1 - 0.55 * l), filter: `blur(${l * 2}px)`, transformOrigin: "50% 100%" }}>
      {children}
    </div>
  );
};

/** 장면 내용(영상마다 broll-plan.json props.content로)
 * report: 첫 장 — eyebrow, title(형광펜), problem{label, text}, body[{t, b?}](b=굵게), fixTitle, fixes[[굵게, 나머지]]
 * dashboard: 둘째 장 — eyebrow, title, items[{img(public 경로), views, tag, keep?, cut?}](4열), keep{what, why}, cut{what, why}
 * "유지" 대사에 keep 항목 초록 테두리·✓, "줄이기" 대사에 cut 항목 흑백, 근거 팝업이 한 줄씩 더해진다.
 */
type ReportContent = {
  windowTitle: string; tool: string;
  report: { eyebrow: string; title: string; problem: { label: string; text: string }; body: { t: string; b?: boolean }[]; fixTitle: string; fixes: [string, string][] };
  dashboard: { eyebrow: string; title: string; items: { img: string; views: string; tag: string; keep?: boolean; cut?: boolean }[];
    keep: { what: string; why: string }; cut: { what: string; why: string } };
};

export const ReportScene: React.FC<{ pip?: string; beats: Record<string, number>; content: ReportContent }> = ({ pip, beats: b, content: C }) => {
  const R = C.report, D = C.dashboard, items = D.items;
  const keepIdx = (i: number) => items.filter((r, k) => r.keep && k < i).length;
  const cutIdx = (i: number) => items.filter((r, k) => r.cut && k < i).length;
 // 격자 칸 위 커서 자리(화면 좌표, 첫 영상에서 맞춘 값): 4열 x 228·436·644·852, 행 y 510·690
  const cell = (i: number): [number, number] => [228 + (i % 4) * 208, 510 + Math.floor(i / 4) * 180];
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = f / fps;
  const ease = (a: number, d = 0.4) => interpolate(t, [a, a + d], [0, 1], clamp);

 // 커서 경로: (시각, x, y, 클릭) — 글자를 가리지 않게 오른쪽 여백 위주
  const keeps = items.map((r, i) => (r.keep ? i : -1)).filter((i) => i >= 0);
  const cuts = items.map((r, i) => (r.cut ? i : -1)).filter((i) => i >= 0);
  const path: [number, number, number, boolean][] = [
    [0, 980, 1000, false], [b.problem - 0.3, 900, 700, false], [b.problem, 880, 640, true],
    [b.fix + 0.4, 900, 860, false], [b.fix + 0.6, 900, 860, true],
    [b.recent + 0.6, 960, 1040, false],
    ...keeps.map((i, k) => [b.keep + 0.15 + k * 0.18, ...cell(i), true] as [number, number, number, boolean]),
    ...cuts.map((i, k) => [b.cut + 0.2 + k * 0.2, ...cell(i), true] as [number, number, number, boolean]),
    [Math.max(b.decide, b.cut + 0.3 + cuts.length * 0.2), 960, 1040, false], [99, 960, 1000, false],
  ];
  let cx = path[0][1], cy = path[0][2], click = 0;
  for (let i = 0; i < path.length - 1; i++) {
    const [ta, xa, ya] = path[i];
    const [tb, xb, yb, cb] = path[i + 1];
    if (t >= ta && t <= tb) {
      const p = interpolate(t, [ta, tb], [0, 1], { ...clamp, easing: (v) => 1 - Math.pow(1 - v, 3) });
      cx = xa + (xb - xa) * p; cy = ya + (yb - ya) * p;
    }
    if (cb && t >= tb && t < tb + 0.35) click = (t - tb) / 0.35;
  }
  if (t > path[path.length - 2][0]) { cx = path[path.length - 2][1]; cy = path[path.length - 2][2]; }

  const card = { f, fps };
  return (
    <AbsoluteFill style={{ background: BG, fontFamily: SANS }}>
 {/* 1. 성장을 막고 있는 5가지 / BLOCKER 01 → HOW TO FIX */}
      <Stack {...card} enterAt={0} leaveAt={b.recent}>
        <Window title={C.windowTitle} tool={C.tool} height={760} scroll={interpolate(t, [b.fix - 0.2, b.fix + 0.5], [0, 0], { ...clamp, easing: (v) => v * v * (3 - 2 * v) })}>
          <Eyebrow>{R.eyebrow}</Eyebrow>
          <H1><Mark p={ease(b.problem, 0.5)}>{R.title}</Mark></H1>
          <div style={{ height: 3, background: INK, margin: "24px 0" }} />
          <div style={{ fontSize: 42, fontWeight: 900, color: INK, margin: "6px 0 16px", lineHeight: 1.3 }}>
            <span style={{ color: RED }}>{R.problem.label}</span> <Mark p={ease(b.problem + 0.85, 0.5)} color="rgba(179,38,30,0.18)">{R.problem.text}</Mark>
          </div>
          <div style={{ fontSize: 30, color: "#333", lineHeight: 1.6 }}>
            {R.body.map((l, i) => <div key={i} style={{ fontWeight: l.b ? 800 : 400 }}>{l.t}</div>)}
          </div>
 {/* 이렇게 고쳐보세요: 앞으로 살짝 떠오르며 그림자가 짙어진다 */}
          <div style={{ marginTop: 30, background: "#EEF3FF", borderLeft: `6px solid ${BLUE}`, borderRadius: 14, padding: "26px 30px",
            transform: `translateY(${(1 - ease(b.fix, 0.35)) * 30}px) scale(${1 + 0.03 * ease(b.fix, 0.35)})`,
            boxShadow: `0 ${20 * ease(b.fix, 0.35)}px 40px rgba(47,85,212,${0.18 * ease(b.fix, 0.35)})` }}>
            <div style={{ fontSize: 26, fontWeight: 900, color: BLUE }}>{R.fixTitle}</div>
            {R.fixes.map(([a, c], i) => (
              <div key={i} style={{ fontSize: 31, color: "#222", marginTop: 16, lineHeight: 1.4, opacity: ease(b.fix + 0.35 + i * 0.35, 0.3),
                transform: `translateX(${(1 - ease(b.fix + 0.35 + i * 0.35, 0.3)) * 24}px)` }}>✓ <b>{a}</b>{c}</div>
            ))}
          </div>
        </Window>
      </Stack>

 {/* 2. 대시보드 한 장(사용자): 조회수 TOP 8 + 근거(좋아요율). "유지하고" → 초록 테두리·체크, "올리면 안 되는지" → 흑백 */}
      <Stack {...card} enterAt={b.recent} leaveAt={99}>
        <Window title={C.windowTitle} tool={C.tool} height={800}>
          <Eyebrow>{D.eyebrow}</Eyebrow>
          <div style={{ fontSize: 44, fontWeight: 900, color: INK, margin: "6px 0 22px" }}>{D.title}</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", columnGap: 20, rowGap: 16 }}>
            {items.map((r, i) => {
              const p = ease(b.recent + 0.25 + i * 0.07, 0.3);
              const sel = r.keep ? ease(b.keep + 0.15 + keepIdx(i) * 0.18, 0.3) : 0;
              const gray = r.cut ? ease(b.cut + 0.2 + cutIdx(i) * 0.2, 0.35) : 0;
              const rateShow = ease(b.recent + 0.6, 0.3);
              return (
                <div key={i} style={{ opacity: p, transform: `translateY(${(1 - p) * 20}px)` }}>
                  <div style={{ position: "relative", height: 112, borderRadius: 14, overflow: "hidden",
                    boxShadow: "0 6px 16px rgba(0,0,0,0.12)" }}>
                    <Img src={staticFile(r.img)} style={{ position: "absolute", width: "100%", height: "100%", objectFit: "cover",
                      filter: `grayscale(${gray}) brightness(${1 - 0.3 * gray})` }} />
                    <div style={{ position: "absolute", left: 8, top: 8, fontSize: 18, fontWeight: 900, color: "#fff", background: "rgba(0,0,0,0.55)", borderRadius: 8, padding: "2px 9px" }}>{i + 1}</div>
 {/* 선택 테두리: 썸네일 안쪽에 그려 잘리지 않게 */}
                    {sel > 0 && <div style={{ position: "absolute", inset: 0, borderRadius: 14, border: `${7 * sel}px solid ${GREEN}` }} />}
                    {sel > 0 && <div style={{ position: "absolute", right: 8, top: 8, width: 40, height: 40, borderRadius: 20, background: GREEN, color: "#fff", fontSize: 26, fontWeight: 900,
                      display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${sel})` }}>✓</div>}
                  </div>
                  <div style={{ fontSize: 25, fontWeight: 900, color: gray > 0.5 ? "#A0A6AE" : INK, marginTop: 6, textAlign: "center" }}>{r.views}</div>
                  <div style={{ fontSize: 21, fontWeight: 800, textAlign: "center", opacity: rateShow,
                    color: sel > 0.5 ? GREEN : gray > 0.5 ? "#8A9099" : SUB }}>{r.tag}</div>
                </div>
              );
            })}
          </div>
        </Window>
      </Stack>

 {/* 근거 팝업(사용자): 창 위에 떠오르는 카드. "유지하고"에 유지 줄, "올리면 안 되는지"에 줄일 줄이 더해지고 끝까지 남는다 */}
      {t >= b.keep && (() => {
        const o = spring({ frame: f - b.keep * fps, fps, config: { damping: 15, stiffness: 170 } });
        const rowsP = [
          { at: b.keep, color: GREEN, bg: "#EAF6EF", head: "✓ 유지할 것", what: D.keep.what, why: D.keep.why },
          { at: b.cut, color: RED, bg: "#FDEDEB", head: "✕ 줄일 것", what: D.cut.what, why: D.cut.why },
        ];
        return (
          <div style={{ position: "absolute", left: 70, right: 70, top: 838, background: "#fff", borderRadius: 28, padding: "14px 22px",
            boxShadow: "0 30px 80px rgba(15,25,50,0.28), 0 6px 18px rgba(15,25,50,0.12)", opacity: o, transform: `translateY(${(1 - o) * 40}px) scale(${0.94 + 0.06 * o})` }}>
                        {rowsP.map((x, k) => {
              const r = ease(x.at + 0.05, 0.3);
              return t >= x.at ? (
                <div key={k} style={{ background: x.bg, borderRadius: 16, padding: "10px 20px", marginTop: k ? 10 : 0, opacity: r, transform: `translateY(${(1 - r) * 16}px)` }}>
                  <div style={{ fontSize: 30, fontWeight: 900, color: x.color }}>{x.head} <span style={{ color: INK }}>{x.what}</span></div>
                  <div style={{ fontSize: 24, fontWeight: 700, color: "#3A3F47", marginTop: 4 }}>{x.why}</div>
                </div>
              ) : null;
            })}
          </div>
        );
      })()}

      <Cursor x={cx} y={cy} click={click} />
 {/* 앞 장면(프롬프트)과 같은 자리라 인물 창은 다시 들어오지 않고 그대로 이어진다 */}
      {pip && <PersonPip pip={pip} enter={1} />}
    </AbsoluteFill>
  );
};
