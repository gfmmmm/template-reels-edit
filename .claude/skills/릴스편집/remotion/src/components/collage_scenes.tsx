// 콜라주 자료화면 장면 (한 편집 사례)
// 사용자: 기존 분석 화면을 그대로 쓰지 말고, 같은 내용을 콜라주로 새로 표현한다. 바탕은 흰 종이 질감.
// 원칙: 글자는 지어내지 않는다(대본·분석 결과 문구 그대로) / 화면 전체 1초 6장 스톱모션 / 인물 창(PersonPip)은 원래 속도·모습
// 화면 배치: 내용은 세로 150~1,040px(자막 1,120px 자리 비움), 인물 창은 1,400px 아래.
import React from "react";
import { AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { PersonPip } from "./scene";

const IMG = (n: string) => staticFile(`images/collage/${n}`);
const SANS = "'Apple SD Gothic Neo', Pretendard, sans-serif";
const INK = "#1B1B1B";
const RED = "#C8332B";
const GREEN = "#2E8B57";
const YEL = "rgba(244,199,15,0.85)";

const rand = (a: number, b: number) => {
  const s = Math.sin(a * 127.1 + b * 311.7) * 43758.5453;
  return s - Math.floor(s);
};

// ── 스톱모션 시계 ──
const Clock = React.createContext({ t: 0, step: 0, fps: 30, frame: 0 });
const useClock = () => React.useContext(Clock);

const Stage: React.FC<{ children: React.ReactNode; pip?: string; pipEnter?: boolean; stepFps?: number }> = ({ children, pip, pipEnter, stepFps = 6 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const hold = Math.max(1, Math.round(fps / stepFps));
  const qf = Math.floor(frame / hold) * hold;
  const step = Math.floor(frame / hold);
  const pe = pipEnter ? spring({ frame, fps, config: { damping: 22, stiffness: 300 } }) : 1;
  return (
    <Clock.Provider value={{ t: qf / fps, step, fps, frame: qf }}>
      <AbsoluteFill style={{ fontFamily: SANS, color: INK }}>
        <Img src={IMG("paper_white.png")} style={{ position: "absolute", inset: -8, width: 1096, height: 1936, objectFit: "cover",
          transform: `translate(${(rand(step, 9) - 0.5) * 2}px, ${(rand(9, step) - 0.5) * 2}px)` }} />
        {children}
        <svg width={1080} height={1920} style={{ position: "absolute", inset: 0, mixBlendMode: "multiply", opacity: 0.12, pointerEvents: "none" }}>
          <filter id={`g${step % 3}`}><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed={step % 3} /><feColorMatrix type="saturate" values="0" /></filter>
          <rect width="100%" height="100%" filter={`url(#g${step % 3})`} />
        </svg>
        {pip && <PersonPip pip={pip} enter={pe} />}
      </AbsoluteFill>
    </Clock.Provider>
  );
};

type Dir = "T" | "B" | "L" | "R" | "pop";
// 조각 하나: at에 dir 방향에서 들어와 (x,y)에 놓이고, out이 있으면 그때 outDir로 빠진다. x,y는 조각 가운데.
const Bit: React.FC<{
  x: number; y: number; w: number; h?: number; rot?: number; at: number; dir?: Dir; dur?: number;
  out?: number; outDir?: Dir; z?: number; shadow?: boolean; children?: React.ReactNode; src?: string; seed?: number;
}> = ({ x, y, w, h, rot = 0, at, dir = "T", dur = 0.45, out, outDir = "L", z = 1, shadow = true, children, src, seed = 0 }) => {
  const { t, step, fps } = useClock();
  if (t < at) return null;
  const k = spring({ frame: (t - at) * fps, fps, durationInFrames: Math.round(dur * fps), config: { damping: 11, stiffness: 150, mass: 0.7 } });
  const far: Record<string, [number, number]> = { T: [0, -1500], B: [0, 1500], L: [-1300, 0], R: [1300, 0], pop: [0, 0] };
  let dx = far[dir][0] * (1 - k), dy = far[dir][1] * (1 - k), sc = dir === "pop" ? k : 1, r = rot + (dir === "T" ? (1 - Math.min(k, 1)) * 9 : 0);
  if (out !== undefined && t >= out) {
    const o = interpolate(t, [out, out + 0.35], [0, 1], { extrapolateRight: "clamp" });
    if (o >= 1) return null;
    const f2 = far[outDir === "pop" ? "B" : outDir];
    dx += f2[0] * o; dy += f2[1] * o;
  }
  const settled = (t - at) > dur;
  const jx = (rand(step, seed + 1) - 0.5) * 3, jy = (rand(seed + 1, step) - 0.5) * 3, jr = settled ? (rand(step + 5, seed) - 0.5) * 0.7 : 0;
  return (
    <div style={{ position: "absolute", left: x - w / 2 + dx + jx, top: y + dy + jy, width: w, height: h, zIndex: z,
      transform: `translateY(-50%) rotate(${r + jr}deg) scale(${sc})`, filter: shadow ? "drop-shadow(3px 7px 6px rgba(40,30,20,0.32))" : undefined }}>
      {src ? <Img src={IMG(src)} style={{ width: "100%", height: h ? "100%" : undefined, display: "block" }} /> : children}
    </div>
  );
};

// 종이 쪽지(글자) — 가장자리를 살짝 비뚤게 오린 모양
const Note: React.FC<{ bg?: string; pad?: string; children: React.ReactNode; style?: React.CSSProperties }> = ({ bg = "#FBF8F1", pad = "18px 24px", children, style }) => (
  <div style={{ background: bg, padding: pad, clipPath: "polygon(0.6% 2%, 99% 0%, 100% 97%, 1.5% 100%)", lineHeight: 1.35, ...style }}>{children}</div>
);
// 마스킹 테이프 위 손글씨 같은 숫자·이름표
const TapeLabel: React.FC<{ children: React.ReactNode; size?: number; color?: string }> = ({ children, size = 30, color = INK }) => (
  <div style={{ position: "relative", padding: "6px 18px", display: "inline-block" }}>
    <Img src={IMG("tape1.png")} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", opacity: 0.92 }} />
    <span style={{ position: "relative", fontSize: size, fontWeight: 900, color }}>{children}</span>
  </div>
);
// 인화 사진(흰 테두리)
const Photo: React.FC<{ src: string; w: number; h: number; gray?: number; pad?: number; staticSrc?: boolean }> = ({ src, w, h, gray = 0, pad = 10 }) => (
  <div style={{ width: w, height: h, background: "#fff", padding: pad, boxSizing: "border-box" }}>
    <Img src={staticFile(src)} style={{ width: "100%", height: "100%", objectFit: "cover", filter: `grayscale(${gray}) contrast(1.05)` }} />
  </div>
);
// 형광펜: p(0~1)만큼 칠해짐
const Hl: React.FC<{ p: number; children: React.ReactNode; color?: string }> = ({ p, children, color = YEL }) => (
  <span style={{ backgroundImage: `linear-gradient(${color}, ${color})`, backgroundRepeat: "no-repeat", backgroundSize: `${p * 100}% 45%`, backgroundPosition: "0 88%" }}>{children}</span>
);
// 마커 동그라미·X (그려지듯)
const Marker: React.FC<{ kind: "circle" | "x" | "check" | "under"; x: number; y: number; w: number; h: number; at: number; color?: string; dur?: number; out?: number }> = ({ kind, x, y, w, h, at, color = RED, dur = 0.35, out }) => {
  const { t } = useClock();
  if (t < at || (out !== undefined && t >= out)) return null;
  const p = interpolate(t, [at, at + dur], [0, 1], { extrapolateRight: "clamp" });
  const L = 1000;
  const d = kind === "circle" ? `M ${w * 0.5} 4 C ${w * 1.02} 2, ${w} ${h}, ${w * 0.5} ${h - 3} C 0 ${h}, 0 4, ${w * 0.58} 10`
    : kind === "x" ? `M 8 8 L ${w - 8} ${h - 8} M ${w - 8} 8 L 8 ${h - 8}`
      : kind === "check" ? `M 6 ${h * 0.55} L ${w * 0.38} ${h - 6} L ${w - 6} 6` : `M 4 ${h / 2} C ${w * 0.3} ${h / 2 - 4}, ${w * 0.7} ${h / 2 + 4}, ${w - 4} ${h / 2 - 2}`;
  return (
    <svg width={w} height={h} style={{ position: "absolute", left: x, top: y, overflow: "visible", zIndex: 50 }}>
      <path d={d} fill="none" stroke={color} strokeWidth={kind === "under" ? 7 : 9} strokeLinecap="round" strokeLinejoin="round" pathLength={L} strokeDasharray={L} strokeDashoffset={L * (1 - p)} />
    </svg>
  );
};
// 빨간 고무도장
const Stamp: React.FC<{ children: React.ReactNode; size?: number; color?: string }> = ({ children, size = 44, color = RED }) => (
  <div style={{ border: `6px solid ${color}`, color, fontSize: size, fontWeight: 900, padding: "8px 20px", borderRadius: 10, letterSpacing: 1,
    background: "rgba(255,255,255,0.15)", opacity: 0.9, mixBlendMode: "multiply", textAlign: "center", lineHeight: 1.15, whiteSpace: "nowrap", display: "inline-block" }}>{children}</div>
);
// 오려 낸 잡지 글자 (글자마다 다른 종이 조각)
const Cutout: React.FC<{ text: string; size?: number }> = ({ text, size = 120 }) => {
  const { step } = useClock();
  const bgs = ["#1B1B1B", "#F4C70F", "#FBF8F1", "#C8332B", "#FBF8F1", "#1B1B1B"];
  return (
    <div style={{ display: "flex", gap: 6, alignItems: "center", justifyContent: "center" }}>
      {[...text].map((ch, i) => ch === " " ? <span key={i} style={{ width: size * 0.3 }} /> : (
        <span key={i} style={{ background: bgs[i % bgs.length], color: [0, 3].includes(i % bgs.length) ? "#fff" : INK, fontSize: size, fontWeight: 900,
          fontFamily: i % 2 ? "Georgia, serif" : SANS, padding: "2px 12px", lineHeight: 1.1, transform: `rotate(${(rand(i, 3) - 0.5) * 10 + (rand(step, i) - 0.5)}deg)`,
          boxShadow: "2px 5px 6px rgba(0,0,0,0.3)" }}>{ch}</span>
      ))}
    </div>
  );
};
// 손이 종이를 밀어 넣고 빠진다 (왼쪽에서)
const PushHand: React.FC<{ at: number; y: number; to: number }> = ({ at, y, to }) => {
  const { t, fps } = useClock();
  if (t < at) return null;
  const k = spring({ frame: (t - at) * fps, fps, durationInFrames: Math.round(0.45 * fps), config: { damping: 12, stiffness: 150 } });
  const o = interpolate(t, [at + 0.6, at + 1.0], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  if (o >= 1) return null;
  return <Img src={IMG("hand_push.png")} style={{ position: "absolute", width: 560, left: to - 560 + (1 - k) * -1300 - o * 800, top: y,
    filter: "drop-shadow(4px 8px 6px rgba(0,0,0,0.35))", zIndex: 60 }} />;
};

// ── 1. 프롬프트 ── 줄 노트에 프롬프트 전문이 적힌 채로 밀려 들어오고(타이핑 없음), 핵심 구절에 형광펜, "Aside" 도장.
// scanAt이 있으면(첫 프롬프트) 그때 노트가 빠지고 내 피드 사진이 쏟아지며 돋보기가 훑는다.
export const CPrompt: React.FC<{ prompt: string; tool: string; marks?: string[]; scanAt?: number; pip?: string; pipEnter?: boolean }> = ({ prompt, tool, marks = [], scanAt, pip, pipEnter }) => {
  const [first, ...rest] = prompt.split("\n");
  const body = rest.join("\n").trim();
  const long = prompt.length > 300;
  return (
    <Stage pip={pip} pipEnter={pipEnter}>
      <Clocked>{({ t }) => {
        const markP = (i: number) => interpolate(t, [0.55 + i * 0.25, 0.8 + i * 0.25], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
        const render = (txt: string) => {
 // 형광펜 구절을 찾아 칠한다 (문구는 그대로)
          let parts: (string | React.ReactElement)[] = [txt];
          marks.forEach((m, i) => {
            parts = parts.flatMap((p): (string | React.ReactElement)[] => typeof p !== "string" || !p.includes(m) ? [p] : p.split(m).flatMap((s, j, arr) => j < arr.length - 1 ? [s, <Hl key={`${i}-${j}`} p={markP(i)}>{m}</Hl>] : [s]));
          });
          return parts;
        };
        return (
          <>
            <Bit x={540} y={595} w={980} h={880} at={0} dir="L" dur={0.45} out={scanAt} outDir="L" seed={1}>
              <div style={{ position: "relative", width: 980, height: 880 }}>
                <Img src={IMG("lined.png")} style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }} />
                <div style={{ position: "absolute", left: 120, right: 50, top: 58 }}>
                  <div style={{ fontSize: long ? 36 : 40, fontWeight: 900, marginBottom: 14 }}>{render(first)}</div>
                  <div style={{ fontSize: long ? 25 : 29, fontWeight: 600, lineHeight: long ? 1.45 : 1.5, whiteSpace: "pre-wrap", color: "#2A2A2A" }}>{render(body)}</div>
                </div>
              </div>
            </Bit>
            <PushHand at={0} y={430} to={190} />
            <Bit x={830} y={985} w={400} at={0.5} dir="pop" dur={0.2} out={scanAt} outDir="L" seed={2} rot={-10} shadow={false} z={70}>
              <Stamp size={38}>{tool}에게 보냄</Stamp>
            </Bit>
            {scanAt !== undefined && <FeedScan at={scanAt} />}
          </>
        );
      }}</Clocked>
    </Stage>
  );
};
const Clocked: React.FC<{ children: (c: { t: number; step: number }) => React.ReactNode }> = ({ children }) => {
  const c = useClock();
  return <>{children(c)}</>;
};
// 내 피드 사진이 쏟아지고 돋보기가 훑는다 ("AI가 내 계정을 싹 분석해서")
const FeedScan: React.FC<{ at: number }> = ({ at }) => {
  const { t } = useClock();
  const cells = Array.from({ length: 12 }, (_, i) => i);
  const mx = interpolate(t, [at + 0.5, at + 1.6], [200, 860], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const my = 520 + Math.sin((t - at) * 6) * 150;
  return (
    <>
      <Bit x={540} y={215} w={560} at={at} dir="T" dur={0.35} seed={30} rot={-1.5} z={5}>
        <Note bg="#FBF8F1" pad="12px 22px" style={{ textAlign: "center" }}>
          <span style={{ fontSize: 34, fontWeight: 900 }}>@my_account</span><span style={{ fontSize: 26, fontWeight: 700, color: "#555" }}> 계정 분석 중</span>
        </Note>
      </Bit>
      {cells.map((i) => (
        <Bit key={i} x={210 + (i % 4) * 220} y={420 + Math.floor(i / 4) * 230} w={200} h={220} at={at + 0.05 + i * 0.04} dir="T" dur={0.3}
          rot={(rand(i, 7) - 0.5) * 10} seed={40 + i} z={6 + i}>
          <Photo src={`images/myfeed/${i + 1}.jpg`} w={200} h={220} />
        </Bit>
      ))}
      {t >= at + 0.45 && <Img src={IMG("magnifier.png")} style={{ position: "absolute", width: 300, left: mx - 110, top: my - 110, zIndex: 80,
        transform: "rotate(-20deg)", filter: "drop-shadow(6px 12px 8px rgba(0,0,0,0.35))" }} />}
    </>
  );
};

// ── 2. 계정 진단 보고서 ──
type ReportContent = {
  report: { eyebrow: string; title: string; problem: { label: string; text: string }; body: { t: string; b?: boolean }[]; fixTitle: string; fixes: [string, string][] };
  dashboard: { eyebrow: string; title: string; items: { img: string; views: string; tag: string; keep?: boolean; cut?: boolean }[];
    keep: { what: string; why: string }; cut: { what: string; why: string } };
};
export const CReport: React.FC<{ beats: Record<string, number>; content: ReportContent; pip?: string; pipEnter?: boolean }> = ({ beats: b, content: C, pip, pipEnter }) => {
  const R = C.report, D = C.dashboard;
  const out = b.recent; // 보고서 → 대시보드로 넘어가는 순간 앞 종이들은 왼쪽으로 쓸려 나간다
  const cell = (i: number) => ({ x: 195 + (i % 4) * 230, y: 430 + Math.floor(i / 4) * 255 });
  let ki = 0, ci = 0;
  return (
    <Stage pip={pip} pipEnter={pipEnter}>
 {/* 보고서 종이 */}
      <Bit x={540} y={290} w={930} at={0} dir="T" out={out} seed={1} rot={-1}>
        <Note pad="22px 34px">
          <div style={{ fontSize: 26, fontWeight: 800, color: "#777" }}>{R.eyebrow}</div>
          <div style={{ fontSize: 56, fontWeight: 900, marginTop: 6 }}>{R.title}</div>
        </Note>
      </Bit>
      <Bit x={540} y={450} w={900} at={b.problem} dir="L" dur={0.35} out={out} seed={2} rot={1.5} z={3}>
        <Note bg="#F6D5CF" pad="16px 28px"><span style={{ fontSize: 40, fontWeight: 900, color: RED }}>{R.problem.label}</span>
          <span style={{ fontSize: 40, fontWeight: 900 }}> {R.problem.text}</span></Note>
      </Bit>
      {R.body.map((l, i) => (
        <Bit key={i} x={540} y={565 + i * 66} w={880} at={b.blocker + i * 0.25} dir="R" dur={0.3} out={out} seed={3 + i} rot={(i - 1) * 0.8} z={2}>
          <Note pad="10px 24px"><span style={{ fontSize: 31, fontWeight: l.b ? 900 : 600 }}>{l.t}</span></Note>
        </Bit>
      ))}
      <Marker kind="under" x={120} y={705} w={520} h={24} at={b.blocker + 0.8} out={out} />
      <Bit x={250} y={900} w={330} at={b.fix} dir="pop" dur={0.25} out={out} seed={8} rot={-4} z={4} shadow={false}>
        <Note bg="transparent" pad="0"><span style={{ fontSize: 36, fontWeight: 900, color: RED, whiteSpace: "nowrap" }}>{R.fixTitle}</span></Note>
      </Bit>
      {R.fixes.map(([a, c], i) => (
        <Bit key={i} x={560 + i * 270} y={900} w={300} h={290} at={b.fix + 0.3 + i * 0.35} dir="pop" dur={0.25} out={out} seed={9 + i} rot={i ? 4 : -3} z={5 + i}>
          <div style={{ position: "relative", width: 300, height: 290 }}>
            <Img src={IMG("sticky.png")} style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }} />
            <div style={{ position: "absolute", inset: "34px 26px", fontSize: 31, fontWeight: 800, lineHeight: 1.3 }}><b style={{ fontWeight: 900 }}>{a}</b>{c}</div>
          </div>
        </Bit>
      ))}

 {/* TOP 8: 인화 사진이 하나씩 떨어진다 */}
      <Bit x={540} y={240} w={930} at={b.recent} dir="R" dur={0.35} seed={20} rot={1}>
        <div style={{ position: "relative" }}>
          <Img src={IMG("strip.png")} style={{ width: "100%", height: 150, display: "block" }} />
          <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", gap: 16 }}>
            <span style={{ fontSize: 30, fontWeight: 800, color: "#666" }}>{D.eyebrow}</span><span style={{ fontSize: 46, fontWeight: 900 }}>{D.title}</span>
          </div>
        </div>
      </Bit>
      {D.items.map((r, i) => {
        const c = cell(i);
        const kAt = r.keep ? b.keep + 0.1 + (ki++) * 0.12 : 0;
        const cAt = r.cut ? b.cut + 0.1 + (ci++) * 0.25 : 0;
        return (
          <React.Fragment key={i}>
            <Bit x={c.x} y={c.y} w={205} h={205} at={b.recent + 0.2 + i * 0.09} dir="T" dur={0.3} rot={(rand(i, 2) - 0.5) * 8} seed={30 + i} z={10 + i}>
              <Photo src={r.img} w={205} h={205} gray={r.cut ? interpolate(0, [0, 1], [0, 0]) : 0} />
            </Bit>
            <Bit x={c.x} y={c.y + 118} w={150} at={b.recent + 0.45 + i * 0.09} dir="pop" dur={0.2} seed={50 + i} rot={(rand(i, 5) - 0.5) * 6} z={30} shadow={false}>
              <div style={{ textAlign: "center" }}><TapeLabel size={27}>{r.views}</TapeLabel></div>
            </Bit>
            <Bit x={c.x} y={c.y - 92} w={190} at={b.contents + i * 0.06} dir="pop" dur={0.2} seed={60 + i} z={31} shadow={false}>
              <div style={{ textAlign: "center" }}><span style={{ fontSize: 22, fontWeight: 900, background: "#FBF8F1", padding: "3px 10px",
                color: r.keep ? GREEN : r.cut ? RED : INK, boxShadow: "1px 2px 3px rgba(0,0,0,0.2)" }}>{r.tag}</span></div>
            </Bit>
            {r.keep && <Marker kind="circle" x={c.x - 125} y={c.y - 125} w={250} h={250} at={kAt} color={GREEN} dur={0.3} />}
            {r.cut && <Marker kind="x" x={c.x - 100} y={c.y - 100} w={200} h={200} at={cAt} color={RED} dur={0.3} />}
          </React.Fragment>
        );
      })}
 {/* 근거 쪽지 */}
      <Bit x={540} y={995 - 105} w={960} at={b.keep} dir="L" dur={0.3} seed={70} rot={-1} z={40}>
        <Note bg="#E5F2E9" pad="12px 26px"><span style={{ fontSize: 33, fontWeight: 900, color: GREEN }}>✓ 유지할 것 </span><span style={{ fontSize: 33, fontWeight: 900 }}>{D.keep.what}</span>
          <div style={{ fontSize: 25, fontWeight: 700, color: "#3A3F47" }}>{D.keep.why}</div></Note>
      </Bit>
      <Bit x={540} y={995} w={960} at={b.cut} dir="R" dur={0.3} seed={71} rot={1} z={41}>
        <Note bg="#F8E1DE" pad="12px 26px"><span style={{ fontSize: 33, fontWeight: 900, color: RED }}>✕ 줄일 것 </span><span style={{ fontSize: 33, fontWeight: 900 }}>{D.cut.what}</span>
          <div style={{ fontSize: 25, fontWeight: 700, color: "#3A3F47" }}>{D.cut.why}</div></Note>
      </Bit>
    </Stage>
  );
};

// ── 3. 수익 구조 ── 폴라로이드 프로필 → 상품 티켓 3장 → 댓글·DM·전화·결제가 실로 이어짐 → 반응 8배
type RevenueContent = {
  profile: { img: string; handle: string; followers: string; role: string };
  offers: { pre: string; hl: string; items: [string, string, string][] };
  how: { line1: string; hl: string; flow: [string, string][]; bars: [string, number][]; big: string };
};
const OFFER_ICON = ["gradcap.png", "ticket.png", "robot.png"];
const FLOW_ICON = ["bubble.png", "envelope.png", "telephone.png", "card.png"];
export const CRevenue: React.FC<{ beats: Record<string, number>; content: RevenueContent; pip?: string; pipEnter?: boolean }> = ({ beats: b, content: C, pip, pipEnter }) => {
  return (
    <Stage pip={pip} pipEnter={pipEnter}>
      <Bit x={230} y={300} w={260} h={300} at={0} dir="T" dur={0.4} rot={-4} seed={1} out={b.how} outDir="L">
        <div style={{ background: "#fff", padding: "14px 14px 50px", width: 260, height: 300, boxSizing: "border-box" }}>
          <Img src={staticFile(C.profile.img)} style={{ width: "100%", height: "100%", objectFit: "cover", filter: "contrast(1.05)" }} />
        </div>
      </Bit>
      <Bit x={660} y={250} w={560} at={0.2} dir="R" dur={0.35} seed={2} rot={1.5} out={b.how} outDir="L">
        <Note pad="12px 24px"><div style={{ fontSize: 44, fontWeight: 900 }}>{C.profile.handle}</div>
          <div style={{ fontSize: 28, fontWeight: 800, color: "#555" }}>팔로워 {C.profile.followers} · {C.profile.role}</div></Note>
      </Bit>
      <Bit x={660} y={400} w={560} at={b.strategy} dir="pop" dur={0.2} seed={3} rot={-1} out={b.how} outDir="L" shadow={false}>
        <div style={{ fontSize: 38, fontWeight: 900 }}>{C.offers.pre} <Hl p={1}>{C.offers.hl}</Hl></div>
      </Bit>
      {C.offers.items.map(([, name, price], i) => (
        <Bit key={i} x={560} y={560 + i * 160} w={760} h={160} at={b.strategy + 0.15 + i * 0.2} dir="T" dur={0.3} rot={(i - 1) * 2} seed={10 + i} out={b.how} outDir="L" z={5 + i}>
          <div style={{ position: "relative", width: 760, height: 160 }}>
            <Img src={IMG("ticket.png")} style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }} />
            <Img src={IMG(OFFER_ICON[i])} style={{ position: "absolute", left: 36, top: 26, height: 108, maxWidth: 190, objectFit: "contain" }} />
            <div style={{ position: "absolute", left: 250, top: 40, fontSize: 36, fontWeight: 900 }}>{name}</div>
            <div style={{ position: "absolute", left: 250, top: 88, fontSize: 32, fontWeight: 900, color: RED }}>{price}</div>
          </div>
        </Bit>
      ))}
 {/* 어떻게: 댓글 한 단어 → 자동 DM → 상담 전화 → 결제 */}
      <Bit x={540} y={250} w={900} at={b.how} dir="R" dur={0.3} seed={20} rot={-1}>
        <div style={{ textAlign: "center", fontSize: 44, fontWeight: 900, lineHeight: 1.3 }}>{C.how.line1}<br /><Hl p={1}>{C.how.hl}</Hl></div>
      </Bit>
      {C.how.flow.map(([, label], i) => {
        const x = 165 + i * 250, y = 520 + (i % 2) * 40;
        return (
          <React.Fragment key={i}>
            <Bit x={x} y={y} w={200} at={b.how + 0.15 + i * 0.18} dir="pop" dur={0.22} seed={30 + i} rot={(rand(i, 4) - 0.5) * 10} z={10}
              src={i === 0 ? undefined : FLOW_ICON[i]}>
              {i === 0 && <div style={{ position: "relative", width: 200 }}><Img src={IMG("bubble.png")} style={{ width: 200, display: "block" }} />
                <div style={{ position: "absolute", left: 0, right: 0, top: 44, textAlign: "center", fontSize: 30, fontWeight: 900 }}>“정보”</div></div>}
            </Bit>
            <Bit x={x} y={y + 125} w={220} at={b.how + 0.25 + i * 0.18} dir="pop" dur={0.2} seed={40 + i} z={11} shadow={false}>
              <div style={{ textAlign: "center" }}><TapeLabel size={27}>{label}</TapeLabel></div>
            </Bit>
          </React.Fragment>
        );
      })}
      <RedString at={b.how + 0.3} pts={C.how.flow.map((_, i) => [165 + i * 250, 520 + (i % 2) * 40] as [number, number])} />
 {/* 반응 8배 */}
      {C.how.bars.map(([label, v], i) => (
        <Bit key={i} x={540} y={780 + i * 80} w={900} at={b.detail + i * 0.2} dir="L" dur={0.3} seed={60 + i} rot={0} z={20} shadow={false}>
          <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
            <span style={{ width: 300, fontSize: 28, fontWeight: 800, textAlign: "right" }}>{label}</span>
            <div style={{ height: 46, width: 30 + (v / 15.2) * 420, background: i ? RED : "#B9B2A6", clipPath: "polygon(0 6%, 100% 0, 98% 100%, 1% 94%)" }} />
            <span style={{ fontSize: 30, fontWeight: 900, color: i ? RED : "#666" }}>{v}%</span>
          </div>
        </Bit>
      ))}
      <Bit x={540} y={985} w={700} at={b.detail + 0.5} dir="pop" dur={0.22} seed={70} z={30} shadow={false}>
        <Cutout text={C.how.big} size={84} />
      </Bit>
    </Stage>
  );
};
const RedString: React.FC<{ at: number; pts: [number, number][] }> = ({ at, pts }) => {
  const { t } = useClock();
  if (t < at) return null;
  const p = interpolate(t, [at, at + 0.7], [0, 1], { extrapolateRight: "clamp" });
  const d = pts.map((q, i) => (i ? `Q ${(pts[i - 1][0] + q[0]) / 2} ${Math.max(pts[i - 1][1], q[1]) + 70} ${q[0]} ${q[1]}` : `M ${q[0]} ${q[1]}`)).join(" ");
  return <svg width={1080} height={1920} style={{ position: "absolute", inset: 0, zIndex: 9 }}>
    <path d={d} fill="none" stroke={RED} strokeWidth={5} pathLength={1000} strokeDasharray={1000} strokeDashoffset={1000 * (1 - p)} strokeLinecap="round" />
  </svg>;
};

// ── 4. 공구 계정 판매 흐름 ──
type FlowContent = { intro: { emoji: string; pre: string; hl: string; statLabel: string; stat: string; caption: string };
  title: string; steps: [string, string, string][]; keyIndex: number; result: { small: string; big: string } };
const STEP_ICON = ["clapper.png", "bell.png", "megaphone.png", "cart.png"];
export const CFlow: React.FC<{ beats: Record<string, number>; content: FlowContent; pip?: string; pipEnter?: boolean }> = ({ beats: b, content: C, pip, pipEnter }) => (
  <Stage pip={pip} pipEnter={pipEnter}>
    <Bit x={290} y={420} w={330} src="basket.png" at={0} dir="T" dur={0.4} seed={1} rot={-3} out={b.strategy} outDir="L" />
    <Bit x={700} y={300} w={560} at={0.15} dir="R" dur={0.35} seed={2} rot={1.5} out={b.strategy} outDir="L">
      <Note pad="12px 24px"><span style={{ fontSize: 40, fontWeight: 800 }}>{C.intro.pre} </span><span style={{ fontSize: 44, fontWeight: 900 }}><Hl p={1}>{C.intro.hl}</Hl></span></Note>
    </Bit>
    <Bit x={700} y={470} w={560} at={0.5} dir="pop" dur={0.25} seed={3} out={b.strategy} outDir="L" shadow={false}>
      <div style={{ textAlign: "center" }}><div style={{ fontSize: 28, fontWeight: 800, color: "#555", marginBottom: 8 }}>{C.intro.statLabel}</div><Cutout text={C.intro.stat} size={96} /></div>
    </Bit>
    <Bit x={540} y={760} w={900} at={0.9} dir="L" dur={0.3} seed={4} rot={-1} out={b.strategy} outDir="L">
      <Note pad="14px 26px" style={{ textAlign: "center" }}><span style={{ fontSize: 34, fontWeight: 900 }}>{C.intro.caption}</span></Note>
    </Bit>
    <Bit x={540} y={235} w={760} at={b.strategy} dir="R" dur={0.3} seed={10} rot={-1}>
      <div style={{ position: "relative" }}><Img src={IMG("strip.png")} style={{ width: "100%", height: 130, display: "block" }} />
        <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 48, fontWeight: 900 }}>{C.title}</div></div>
    </Bit>
    {C.steps.map(([, a, s], i) => (
      <Bit key={i} x={560} y={400 + i * 150} w={880} h={130} at={b.strategy + 0.2 + i * 0.22} dir={i % 2 ? "R" : "L"} dur={0.3} seed={20 + i} rot={(i % 2 ? 1 : -1) * 1.2} z={5 + i}>
        <Note bg={i === C.keyIndex ? "#FFF3B8" : "#FBF8F1"} pad="0" style={{ height: 130, display: "flex", alignItems: "center", gap: 24, paddingLeft: 26 }}>
          <span style={{ fontSize: 34, fontWeight: 900, color: RED, width: 30 }}>{i + 1}</span>
          <Img src={IMG(STEP_ICON[i])} style={{ height: 96 }} />
          <div><div style={{ fontSize: 36, fontWeight: 900 }}>{a}</div><div style={{ fontSize: 26, fontWeight: 700, color: "#555" }}>{s}</div></div>
        </Note>
      </Bit>
    ))}
    <Bit x={600} y={985} w={760} at={b.detail} dir="pop" dur={0.18} seed={40} rot={-6} z={30} shadow={false}>
      <Stamp size={44}>{C.result.small} {C.result.big}</Stamp>
    </Bit>
  </Stage>
);

// ── 5. 릴스 찾기 ── 휴대폰 안 사진이 한 칸씩 올라가며(사람처럼 스크롤) 찾은 개수가 늘고, 찾은 릴스 3편이 인화 사진으로 떨어진다
type HuntContent = { searching: string; count: number; unit: string; resultPre: string; resultPost: string; found: [string, string, string][] };
export const CReels: React.FC<{ beats: Record<string, number>; content: HuntContent; pip?: string; pipEnter?: boolean }> = ({ beats: b, content: C, pip, pipEnter }) => (
  <Stage pip={pip} pipEnter={pipEnter}>
    <Clocked>{({ t }) => {
      const PW = 560, PH = PW * 1088 / 803; // 휴대폰 조각 크기
      const sx = 0.075 * PW, sy = 0.093 * PH, sw = 0.577 * PW, sh = 0.82 * PH; // 화면 칸 (조각 이미지에서 잰 값)
      const idx = Math.floor(Math.max(0, t - 0.3) / 0.33); // 0.33초마다 한 칸
      const n = Math.min(C.count, Math.floor(Math.max(0, t - 0.3) / (b.found - 0.4) * C.count));
      return (
        <>
          <Bit x={460} y={720} w={PW} h={PH} at={0} dir="B" dur={0.4} seed={1} rot={-2} out={b.found} outDir="L">
            <div style={{ position: "relative", width: PW, height: PH }}>
              <Img src={IMG("phone.png")} style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }} />
              <div style={{ position: "absolute", left: sx, top: sy, width: sw, height: sh, overflow: "hidden" }}>
                <Img src={IMG(`scroll_${idx % 8}.jpg`)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
              </div>
            </div>
          </Bit>
          {t >= 0.5 && t < b.found && <Img src={IMG("hand_point.png")} style={{ position: "absolute", width: 380, left: 330, top: 760 + ((idx % 2) ? -60 : 0), zIndex: 40,
            filter: "drop-shadow(4px 8px 6px rgba(0,0,0,0.35))" }} />}
          <Bit x={830} y={300} w={360} at={0.3} dir="R" dur={0.3} seed={3} rot={4} out={b.found} outDir="R">
            <Note pad="14px 20px" style={{ textAlign: "center" }}><div style={{ fontSize: 26, fontWeight: 800, color: "#555" }}>{C.searching}</div>
              <div style={{ fontSize: 80, fontWeight: 900, color: RED, lineHeight: 1.05 }}>{n}<span style={{ fontSize: 40, color: INK }}>{C.unit}</span></div></Note>
          </Bit>
          <Bit x={540} y={230} w={900} at={b.found} dir="R" dur={0.3} seed={10} rot={-1}>
            <div style={{ textAlign: "center", fontSize: 50, fontWeight: 900 }}>{C.resultPre} <Hl p={1}>{C.count}{C.unit}</Hl> {C.resultPost}</div>
          </Bit>
          {C.found.map(([img, title, views], i) => (
            <Bit key={i} x={540} y={430 + i * 215} w={920} h={200} at={b.found + 0.15 + i * 0.22} dir="T" dur={0.3} seed={20 + i} rot={(i - 1) * 1.5} z={5 + i}>
              <Note pad="0" style={{ height: 200, display: "flex", alignItems: "center", gap: 22, paddingLeft: 14 }}>
                <Photo src={img} w={250} h={176} pad={8} />
                <div><div style={{ fontSize: 40, fontWeight: 900, color: RED }}>▶ {views}</div><div style={{ fontSize: 27, fontWeight: 800, lineHeight: 1.3, width: 600 }}>{title}</div></div>
              </Note>
            </Bit>
          ))}
        </>
      );
    }}</Clocked>
  </Stage>
);
