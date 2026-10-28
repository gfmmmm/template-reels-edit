// 종이 콜라주 스톱모션 자료화면 (스타일1 레퍼런스)
// 기존 카드(cards.tsx)와 별개. 오려 낸 종이 조각(투명 PNG)이 하나씩 들어와 완성 그림이 된다.
// 레퍼런스 실측: 화면이 1초에 5~6번만 바뀐다(나머지는 같은 장면 반복) → stepFps 6.
import React from "react";
import { AbsoluteFill, Audio, Freeze, Img, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { PersonPip, PromptScene } from "./scene";
import { ReportScene } from "./report";
import { FlowScene, ReelsHuntScene, RevenueScene } from "./scene2";

export type Enter = "drop" | "slideL" | "slideR" | "slideT" | "slideB" | "pop";

export type Piece = {
  src: string; // public/ 기준 경로
  x: number; y: number; w: number; // 패널 안 중심 좌표·폭(px)
  rot?: number; // 놓인 뒤 기울기(도). 콜라주 맛은 ±3도 안
  at: number; // 등장 시작(초)
  enter: Enter;
  dur?: number; // 들어오는 데 걸리는 시간(초), 기본 0.6
  z?: number;
 // 손이 밀어 넣기: 손 조각이 같은 방향에서 같이 들어왔다가 놓은 뒤 빠진다
  hand?: { src: string; w: number; dx: number; dy: number; rot?: number }; // dx,dy = 조각 중심 기준 손 위치
};

export type Line = { at: number; dur?: number; from: [number, number]; to: [number, number]; color?: string; width?: number };

type Props = {
  bg: string; // 크라프트지 배경 이미지
  panel?: { x: number; y: number; w: number; h: number; radius?: number }; // 1080×1920 화면 안 패널
  pieces: Piece[];
  lines?: Line[];
  stepFps?: number; // 스톱모션 장수(초당)
  jitter?: number; // 장면마다 흔들림(px)
  sfx?: { src: string; volume?: number }; // 조각이 놓일 때 "탁"
  board?: string; // 패널 밖 바탕색(없으면 투명 → CapCut에서 인물 위에 얹기)
};

// 같은 장·같은 조각이면 늘 같은 값이 나오는 난수 (렌더할 때마다 결과가 같아야 한다)
const rand = (a: number, b: number) => {
  const s = Math.sin(a * 127.1 + b * 311.7) * 43758.5453;
  return s - Math.floor(s);
};

export const PaperCollage: React.FC<Props> = ({
  bg, panel = { x: 40, y: 440, w: 1000, h: 640, radius: 22 }, pieces, lines = [], stepFps = 6, jitter = 1.5, sfx, board,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const hold = Math.max(1, Math.round(fps / stepFps));
  const f = Math.floor(frame / hold) * hold; // 스톱모션: hold 프레임마다 한 번만 바뀜
  const step = Math.floor(frame / hold);
  const t = f / fps;

  const pose = (p: Piece, i: number) => {
    const dur = p.dur ?? 0.6;
    const local = (t - p.at) * fps;
    if (local < 0) return null;
    const k = spring({ frame: local, fps, durationInFrames: Math.round(dur * fps), config: { damping: 11, stiffness: 140, mass: 0.7 } });
    const far = { L: [-panel.w * 0.8, 0], R: [panel.w * 0.8, 0], T: [0, -panel.h * 1.1], B: [0, panel.h * 1.1] };
    let dx = 0, dy = 0, sc = 1, rot = p.rot ?? 0;
    if (p.enter === "pop") sc = k;
    else {
      const key = p.enter === "drop" ? "T" : (p.enter.slice(-1) as "L" | "R" | "T" | "B");
      dx = far[key][0] * (1 - k); dy = far[key][1] * (1 - k);
      if (p.enter === "drop") rot += (1 - Math.min(k, 1)) * 8; // 떨어지며 살짝 돌다가 놓임
    }
 // 놓인 뒤에도 장마다 미세하게 떨림 (손으로 찍은 느낌)
    const settled = local > dur * fps;
    const jx = (rand(step, i) - 0.5) * 2 * jitter, jy = (rand(i, step) - 0.5) * 2 * jitter;
    const jr = settled ? (rand(step + 7, i) - 0.5) * 0.6 : 0;
    return { dx: dx + jx, dy: dy + jy, sc, rot: rot + jr, k, local, dur };
  };

  return (
    <AbsoluteFill style={{ background: board ?? "transparent" }}>
      <div style={{ position: "absolute", left: panel.x, top: panel.y, width: panel.w, height: panel.h, borderRadius: panel.radius ?? 22,
        overflow: "hidden", boxShadow: "0 10px 30px rgba(0,0,0,0.35)" }}>
        <Img src={staticFile(bg)} style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover",
          transform: `translate(${(rand(step, 99) - 0.5) * jitter}px, ${(rand(99, step) - 0.5) * jitter}px) scale(1.01)` }} />
 {/* 줄·선: 그려지듯 늘어남 */}
        <svg width={panel.w} height={panel.h} style={{ position: "absolute", inset: 0 }}>
          {lines.map((l, i) => {
            const p = interpolate(t, [l.at, l.at + (l.dur ?? 0.5)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
            if (p <= 0) return null;
            return <line key={i} x1={l.from[0]} y1={l.from[1]} x2={l.from[0] + (l.to[0] - l.from[0]) * p} y2={l.from[1] + (l.to[1] - l.from[1]) * p}
              stroke={l.color ?? "#C0392B"} strokeWidth={l.width ?? 5} strokeLinecap="round" />;
          })}
        </svg>
        {pieces.map((p, i) => ({ p, i })).sort((a, b) => (a.p.z ?? a.i) - (b.p.z ?? b.i)).map(({ p, i }) => {
          const s = pose(p, i);
          if (!s) return null;
          const shadow = "drop-shadow(3px 5px 4px rgba(0,0,0,0.35))";
 // 손: 조각과 같이 들어왔다가 놓인 뒤 0.3초 머물고 왔던 쪽으로 빠진다
          let hand = null;
          if (p.hand) {
            const out = interpolate(s.local, [s.dur * fps + 0.3 * fps, s.dur * fps + 0.8 * fps], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
            const dir = p.enter === "slideL" ? [-1, 0] : p.enter === "slideR" ? [1, 0] : p.enter === "slideB" ? [0, 1] : [0, -1];
            const hx = p.x + p.hand.dx + s.dx + dir[0] * out * panel.w * 0.7;
            const hy = p.y + p.hand.dy + s.dy + dir[1] * out * panel.h * 0.9;
            hand = <Img src={staticFile(p.hand.src)} style={{ position: "absolute", width: p.hand.w, left: hx - p.hand.w / 2, top: hy - p.hand.w / 2,
              transform: `rotate(${p.hand.rot ?? 0}deg)`, filter: shadow, zIndex: 100 + i }} />;
          }
          return (
            <React.Fragment key={i}>
              <Img src={staticFile(p.src)} style={{ position: "absolute", width: p.w, left: p.x - p.w / 2 + s.dx, top: p.y - p.w / 2 + s.dy,
                transform: `rotate(${s.rot}deg) scale(${s.sc})`, filter: shadow, zIndex: p.z ?? i }} />
              {hand}
            </React.Fragment>
          );
        })}
 {/* 종이 결: 장마다 바뀌는 잔 얼룩 (필름 끓는 느낌) */}
        <svg width={panel.w} height={panel.h} style={{ position: "absolute", inset: 0, mixBlendMode: "multiply", opacity: 0.18, pointerEvents: "none" }}>
          <filter id={`grain${step % 3}`}><feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves="2" seed={step % 3} /><feColorMatrix type="saturate" values="0" /></filter>
          <rect width="100%" height="100%" filter={`url(#grain${step % 3})`} />
        </svg>
      </div>
 {/* 조각이 놓이는 순간 "탁" — 들어오는 시간 끝에 맞춘다 */}
      {sfx && pieces.map((p, i) => (
        <Sequence key={`s${i}`} from={Math.round((p.at + (p.dur ?? 0.6) * 0.55) * fps)} durationInFrames={Math.round(0.6 * fps)}>
          <Audio src={staticFile(sfx.src)} volume={sfx.volume ?? 0.6} />
        </Sequence>
      ))}
    </AbsoluteFill>
  );
};

// ───────────────────────────────────────────────────────────────
// 화면 장면을 콜라주 위에 (한 편집 사례)
// 사용자: 분석 화면·녹화 시연은 그 화면 자체를 최대한 살린다 / 인물 창은 지금 모습 그대로.
// → 기존 장면(PromptScene·ReportScene…)을 고치지 않고 감싼다: 연회색 바탕을 걷어 내 크라프트지를 깔고,
// 화면은 1초 6장 스톱모션 + 종이 그림자 + 모서리 테이프, 인물 창(PersonPip)만 원래 속도로 바깥에 그린다.

const SCREENS: Record<string, React.FC<any>> = { PromptScene, ReportScene, RevenueScene, FlowScene, ReelsHuntScene };
const KRAFT = "images/collage/kraft_9x16.png";

const Grain: React.FC<{ step: number; opacity?: number }> = ({ step, opacity = 0.16 }) => (
  <svg width={1080} height={1920} style={{ position: "absolute", inset: 0, mixBlendMode: "multiply", opacity, pointerEvents: "none" }}>
    <filter id={`g${step % 3}`}><feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed={step % 3} /><feColorMatrix type="saturate" values="0" /></filter>
    <rect width="100%" height="100%" filter={`url(#g${step % 3})`} />
  </svg>
);

export const CollageScreen: React.FC<{
  component: string; props: Record<string, any>;
  pip?: string; pipEnter?: boolean; // 인물 창 (앞 장면에서 이어지면 pipEnter false)
  push?: boolean; // 첫 등장 때 손이 화면 종이를 밀어 넣는다
  tapes?: { x: number; y: number; rot: number; w?: number; src?: string }[];
  stepFps?: number;
  stepScreen?: boolean; // 화면 안 움직임까지 스톱모션으로 (기본 끔 — 화면이 바뀌는 중간에 멈추면 두 화면이 겹쳐 지저분하다)
}> = ({ component, props, pip, pipEnter = false, push = false, tapes = [], stepFps = 6, stepScreen = false }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const hold = Math.max(1, Math.round(fps / stepFps));
  const qf = Math.floor(frame / hold) * hold;
  const step = Math.floor(frame / hold);
  const Comp = SCREENS[component];
  const jx = (rand(step, 1) - 0.5) * 3, jy = (rand(1, step) - 0.5) * 3;
 // 손이 밀어 넣기: 0~0.5초 들어오고, 0.7~1.1초 손만 빠진다
  const k = push ? spring({ frame: qf, fps, durationInFrames: Math.round(0.5 * fps), config: { damping: 13, stiffness: 150 } }) : 1;
  const sx = (1 - k) * -1150;
  const handOut = interpolate(qf / fps, [0.7, 1.1], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const pe = pipEnter ? spring({ frame, fps, config: { damping: 22, stiffness: 300 } }) : 1;
  return (
    <AbsoluteFill>
      <style>{`.cs-root > div { background: transparent !important; }`}</style>
      <Img src={staticFile(KRAFT)} style={{ position: "absolute", inset: -8, width: 1096, height: 1936, objectFit: "cover",
        transform: `translate(${(rand(step, 9) - 0.5) * 2}px, ${(rand(9, step) - 0.5) * 2}px)` }} />
      <div className="cs-root" style={{ position: "absolute", inset: 0, transform: `translate(${sx + jx}px, ${jy}px)`,
        filter: "drop-shadow(4px 9px 7px rgba(40,25,10,0.38)) sepia(0.06)" }}>
        {stepScreen ? <Freeze frame={qf}><Comp {...props} pip={undefined} /></Freeze> : <Comp {...props} pip={undefined} />}
      </div>
      {tapes.map((tp, i) => (
        <Img key={i} src={staticFile(tp.src ?? (i % 2 ? "images/collage/tape2.png" : "images/collage/tape1.png"))}
          style={{ position: "absolute", width: tp.w ?? 210, left: tp.x - (tp.w ?? 210) / 2 + sx + jx, top: tp.y - 30 + jy, opacity: 0.88,
            transform: `rotate(${tp.rot + (rand(step, i + 3) - 0.5) * 0.8}deg)` }} />
      ))}
      {push && handOut < 1 && (
        <Img src={staticFile("images/collage/hand_push.png")} style={{ position: "absolute", width: 620, left: -560 + sx - handOut * 700, top: 640,
          filter: "drop-shadow(4px 8px 6px rgba(0,0,0,0.35))" }} />
      )}
      <Grain step={step} />
      {pip && <PersonPip pip={pip} enter={pe} />}
    </AbsoluteFill>
  );
};

// 번호 장 카드 콜라주판: 오려 낸 큰 숫자가 떨어지고, 제목이 적힌 찢긴 노트 종이띠가 오른쪽에서 밀려 들어온다
export const CollageChapter: React.FC<{ num: number; title: string; stepFps?: number; bg?: string }> = ({ num, title, stepFps = 6, bg = KRAFT }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const hold = Math.max(1, Math.round(fps / stepFps));
  const qf = Math.floor(frame / hold) * hold;
  const step = Math.floor(frame / hold);
  const drop = spring({ frame: qf, fps, durationInFrames: Math.round(0.45 * fps), config: { damping: 10, stiffness: 150, mass: 0.7 } });
  const slide = spring({ frame: qf - Math.round(0.3 * fps), fps, durationInFrames: Math.round(0.45 * fps), config: { damping: 13, stiffness: 150 } });
  const j = (a: number) => (rand(step, a) - 0.5) * 3;
  return (
    <AbsoluteFill>
      <Img src={staticFile(bg)} style={{ position: "absolute", inset: -8, width: 1096, height: 1936, objectFit: "cover" }} />
 {/* 숫자: 흰 종이에 오려 낸 잡지 글자 */}
      <div style={{ position: "absolute", left: 540 - 170 + j(1), top: 520 - (1 - drop) * 900 + j(2), width: 340, height: 400,
        transform: `rotate(${-5 + (1 - drop) * 10}deg)`, background: bg === KRAFT ? "#F4EFE4" : "#1B1B1B", clipPath: "polygon(2% 4%, 97% 0%, 100% 95%, 4% 100%)",
        filter: "drop-shadow(5px 9px 7px rgba(0,0,0,0.4))", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <span style={{ fontFamily: "Georgia, 'Times New Roman', serif", fontWeight: 900, fontSize: 330, color: bg === KRAFT ? "#1B1B1B" : "#F4EFE4", lineHeight: 1 }}>{num}</span>
      </div>
 {/* 제목 종이띠 */}
      {qf >= Math.round(0.3 * fps) && (
        <div style={{ position: "absolute", left: 60 + (1 - slide) * 1100 + j(3), top: 960 + j(4), width: 960, height: 230, transform: "rotate(2deg)",
          filter: "drop-shadow(4px 8px 6px rgba(0,0,0,0.35))" }}>
          <Img src={staticFile("images/collage/strip.png")} style={{ position: "absolute", width: "100%", height: "100%" }} />
          <div style={{ position: "absolute", inset: 0, display: "flex", alignItems: "center", justifyContent: "center",
            fontFamily: "'Apple SD Gothic Neo', Pretendard, sans-serif", fontWeight: 900, fontSize: 70, color: "#1B1B1B" }}>
            <span style={{ background: "linear-gradient(transparent 55%, rgba(244,199,15,0.85) 55%)", padding: "0 10px" }}>{title}</span>
          </div>
        </div>
      )}
      <Grain step={step} />
    </AbsoluteFill>
  );
};
