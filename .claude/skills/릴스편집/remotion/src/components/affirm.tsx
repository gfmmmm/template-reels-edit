// 음성 재생 장면 (한 편집 사례): AI로 만든 음성(자기암시문 등)을 "듣는" 자리.
// 흰 둥근 카드 안에 재생 버튼·소리 파형·진행 막대 + 지금 들리는 문장이 한 줄씩 크게 쌓인다(지난 줄은 작고 흐리게 위로).
// 문장은 실제 음성에서 받아쓴 것만 쓴다(지어내지 않는다). 아래 자막 자리(세로 1,050~1,200px)는 비우고 인물 창(PersonPip)을 둔다.
import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { PersonPip } from "./scene";

const BG = "#F3F4F6";
const BLUE = "#3B5BFD";
const INK = "#1F2329";
const SUB = "#9AA0A6";
const FONT = "'Apple SD Gothic Neo', Pretendard, sans-serif";
const card: React.CSSProperties = {
  background: "#fff", borderRadius: 36, boxShadow: "0 18px 50px rgba(20,30,60,0.10), 0 2px 8px rgba(20,30,60,0.06)",
};

export type AffirmContent = {
  title: string; // 카드 제목 (예: "나의 자기암시문")
  badge: string; // 오른쪽 위 작은 표시 (예: "AI 음성")
  lines: { t: number; text: string; hl?: boolean }[]; // t: 장면 시작 기준 초, hl: 결론 줄(형광펜)
};

export const AffirmScene: React.FC<{ playAt: number; pip?: string; content: AffirmContent }> = ({ playAt, pip, content: C }) => {
  const f = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const enter = spring({ frame: f, fps, config: { damping: 22, stiffness: 300 } });
  const playF = playAt * fps;
  const playing = f >= playF;
  const press = f >= playF - 3 && f < playF + 3 ? 0.85 : 1;
  const prog = interpolate(f, [playF, durationInFrames + fps * 4], [0.08, 0.42], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const shown = C.lines.filter((l) => f >= l.t * fps);
  const cur = shown.length - 1;
  const BARS = 34;

  return (
    <AbsoluteFill style={{ background: BG, fontFamily: FONT }}>
      <div style={{ position: "absolute", left: 70, right: 70, top: 250, height: 720, ...card, padding: "36px 40px", overflow: "hidden",
        transform: `translateY(${(1 - enter) * 60}px) scale(${0.96 + 0.04 * enter})`, opacity: enter }}>
 {/* 머리줄 */}
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{ fontSize: 44 }}>🎧</div>
          <div style={{ fontSize: 34, fontWeight: 900, color: INK }}>{C.title}</div>
          <div style={{ marginLeft: "auto", fontSize: 24, fontWeight: 800, color: BLUE, background: "#EEF1FF", padding: "8px 20px", borderRadius: 22 }}>{C.badge}</div>
        </div>

 {/* 문장들: 지금 줄은 크고 진하게, 지난 줄은 작고 흐리게 위로 밀려난다 */}
        <div style={{ position: "absolute", left: 40, right: 40, top: 100, height: 400, display: "flex", flexDirection: "column", justifyContent: "center", gap: 18 }}>
          {shown.map((l, i) => {
            const age = cur - i;
            const pop = spring({ frame: f - l.t * fps, fps, config: { damping: 18, stiffness: 200 } });
            const isCur = age === 0;
            const hlW = l.hl ? interpolate(f - l.t * fps, [4, 16], [0, 100], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }) : 0;
            return (
              <div key={i} style={{ fontSize: isCur ? (l.hl ? 80 : 70) : 36, whiteSpace: "pre-line", fontWeight: isCur ? 900 : 700, color: isCur ? INK : SUB, lineHeight: 1.25,
                opacity: Math.max(0, (isCur ? pop : 1) * (1 - Math.max(0, age - 2) * 0.5)),
                transform: isCur ? `translateY(${(1 - pop) * 30}px)` : undefined, wordBreak: "keep-all" }}>
                <span style={{ backgroundImage: `linear-gradient(transparent 58%, rgba(255,212,0,0.6) 58%)`, backgroundRepeat: "no-repeat",
                  backgroundSize: `${hlW}% 100%` }}>{l.text}</span>
              </div>
            );
          })}
        </div>

 {/* 소리 파형 */}
        <div style={{ position: "absolute", left: 40, right: 40, top: interpolate(f, [C.lines[0].t * fps - 6, C.lines[0].t * fps + 6], [150, 545], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }), height: interpolate(f, [C.lines[0].t * fps - 6, C.lines[0].t * fps + 6], [300, 70], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }), display: "flex", alignItems: "center", gap: 7 }}>
          {Array.from({ length: BARS }).map((_, i) => {
            const base = 0.25 + 0.2 * Math.abs(Math.sin(i * 1.7));
            const live = playing ? 0.35 + 0.65 * Math.abs(Math.sin(f * 0.35 + i * 0.9) * Math.cos(f * 0.13 + i * 0.4)) : base;
            const done = i / BARS < prog;
            return <div key={i} style={{ flex: 1, height: `${live * 100}%`, borderRadius: 6, background: done ? BLUE : "#D5DAE3" }} />;
          })}
        </div>

 {/* 진행 막대 + 재생 버튼 */}
        <div style={{ position: "absolute", left: 40, right: 40, bottom: 36, display: "flex", alignItems: "center", gap: 28 }}>
          <div style={{ width: 84, height: 84, borderRadius: 42, background: BLUE, color: "#fff", fontSize: 34, fontWeight: 900, flexShrink: 0,
            display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${press})`, boxShadow: "0 8px 20px rgba(59,91,253,0.35)" }}>
            {playing ? "❚❚" : "▶"}
          </div>
          <div style={{ flex: 1, height: 12, borderRadius: 6, background: "#E8EBF2", position: "relative" }}>
            <div style={{ width: `${prog * 100}%`, height: 12, borderRadius: 6, background: BLUE }} />
            <div style={{ position: "absolute", left: `calc(${prog * 100}% - 13px)`, top: -7, width: 26, height: 26, borderRadius: 13, background: "#fff", border: `4px solid ${BLUE}` }} />
          </div>
        </div>
      </div>
      {pip && <PersonPip pip={pip} enter={enter} top={1330} side={150} vidTop={-380} />}
    </AbsoluteFill>
  );
};
