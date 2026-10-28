// 두려움 → 자기암시문 장면 (IMG_0518 "AI로 자신감 끌어올리는 법" 첫 사용)
// FearScene: GPT 창에 부탁(전체가 붙여 넣어진 상태) → 보냄 → "대화 분석 중" → 무의식 속 두려움 3줄 → 두려움마다 자기암시문으로 바뀜.
// AffirmListScene: 자기암시문 전체가 빠르게 올라가며 문장 수가 1→N으로 세어진다("이런 문장이 80개").
// 글은 전부 props(content). 문장은 사용자의 실제 자기암시문 원고에서만 가져온다(지어내지 않는다).
// 카드는 세로 260~1040px 안(자막 1,075~1,165px 자리를 비움), 아래는 인물 창(PersonPip).
import React from "react";
import { AbsoluteFill, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { PersonPip } from "./scene";

const BG = "#F3F4F6";
const BLUE = "#3B5BFD";
const INK = "#1F2329";
const SUB = "#9AA0A6";
const RED = "#E5484D";
const LINE = "#E6E8EC";
const FONT = "'Apple SD Gothic Neo', Pretendard, sans-serif";
const card: React.CSSProperties = {
  background: "#fff", borderRadius: 36, boxShadow: "0 18px 50px rgba(20,30,60,0.10), 0 2px 8px rgba(20,30,60,0.06)",
};

const useT = () => {
  const f = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const sp = (at: number, cfg = { damping: 20, stiffness: 170 }) => (f < at * fps ? 0 : spring({ frame: f - at * fps, fps, config: cfg }));
  const lin = (a: number, b: number) => interpolate(f / fps, [a, b], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return { f, fps, t: f / fps, sp, lin, dur: durationInFrames / fps };
};

const WindowHead: React.FC<{ title: string }> = ({ title }) => (
  <div style={{ height: 58, display: "flex", alignItems: "center", gap: 12, padding: "0 24px", background: "#F4F4F5", borderBottom: `1px solid ${LINE}` }}>
    {["#FF5F57", "#FEBC2E", "#28C840"].map((c) => <div key={c} style={{ width: 18, height: 18, borderRadius: 9, background: c }} />)}
    <div style={{ flex: 1, textAlign: "center", fontSize: 24, fontWeight: 800, color: "#6B7078", marginRight: 70 }}>{title}</div>
  </div>
);

export type FearContent = {
  windowTitle: string; // 예: "ChatGPT"
  prompt: string; // 부탁 전체(대사 속 명령)
  analyzing: string; // 예: "우리 대화 312개 분석 중…"
  fearTitle: string; // 예: "무의식 속 두려움"
  affirmTitle: string; // 예: "두려움을 깨는 자기암시문"
  pairs: { fear: string; affirm: string }[];
};

/**
 * beats(장면 시작부터 초): send(보냄) fears(두려움 첫 줄) flip(두려움 → 암시문 첫 줄) hl(결론 형광펜 "깨줄")
 */
export const FearScene: React.FC<{ beats: { send: number; fears: number; flip: number; hl: number }; content: FearContent; pip?: string }> = ({ beats: b, content: C, pip }) => {
  const { t, sp, lin, dur } = useT();
  const enter = sp(0);
  const drift = 1 + 0.04 * (t / dur); // 멈춰 보이지 않게 창이 천천히 다가온다(멈춤 검수)
  const sent = sp(b.send, { damping: 18, stiffness: 200 });
  const ana = t >= b.send + 0.2 && t < b.fears;
 // 보낸 뒤 부탁 말풍선은 위로 작아지며 물러난다
  const up = sp(b.fears - 0.2, { damping: 22, stiffness: 160 });
  const n = C.pairs.length;
  const fearGap = Math.min(0.3, (b.flip - b.fears) / n); // 셋을 빠르게 쌓아 창을 채운다(검수 3단계 1차)
  const flipGap = Math.max(0.6, (b.hl - b.flip) / n);
  return (
    <AbsoluteFill style={{ background: BG, fontFamily: FONT }}>
      <div style={{ position: "absolute", left: 50, right: 50, top: 250, height: 790, ...card, overflow: "hidden",
        transform: `translateY(${(1 - enter) * 60}px) scale(${(0.96 + 0.04 * enter) * drift})`, opacity: enter }}>
        <WindowHead title={C.windowTitle} />
        <div style={{ position: "absolute", top: 58, left: 0, right: 0, bottom: 0, padding: "26px 34px" }}>
 {/* 부탁: 입력창 안(보내기 전) → 오른쪽 말풍선(보낸 뒤) */}
          <div style={{
            position: "absolute", right: 34, left: interpolate(sent, [0, 1], [34, 150]), top: interpolate(sent, [0, 1], [440 - 70 * lin(0.2, b.send), 26]) - up * 26, // 보내기 전에도 입력창이 천천히 올라온다(멈춤 검수)
            background: sent > 0.5 ? "#EEF1FF" : "#fff", border: sent > 0.5 ? "none" : `2px solid ${LINE}`, borderRadius: 30, borderTopRightRadius: sent > 0.5 ? 8 : 30,
            padding: "20px 26px", fontSize: interpolate(up, [0, 1], [36, 26]), fontWeight: 800, color: INK, lineHeight: 1.4, wordBreak: "keep-all",
            opacity: 1 - up * 0.35, boxShadow: sent > 0.5 ? "none" : "0 6px 20px rgba(20,30,60,0.06)",
          }}>
            {C.prompt}
            {sent < 0.5 && (
              <div style={{ position: "absolute", right: 16, bottom: -76, width: 58, height: 58, borderRadius: 29, background: BLUE, color: "#fff", fontSize: 32, fontWeight: 900,
                display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${t > b.send - 0.15 ? 0.85 : 1 + 0.12 * Math.abs(Math.sin(t * 5))})`, boxShadow: `0 0 0 ${10 * Math.abs(Math.sin(t * 5))}px rgba(59,91,253,0.18)` }}>↑</div>
            )}
          </div>

 {/* 분석 중 */}
          {ana && (
            <div style={{ position: "absolute", left: 34, top: 330, display: "flex", alignItems: "center", gap: 16, fontSize: 32, fontWeight: 800, color: "#6B7078" }}>
              {[0, 1, 2].map((i) => (
                <div key={i} style={{ width: 16, height: 16, borderRadius: 8, background: BLUE, opacity: 0.3 + 0.7 * Math.abs(Math.sin(t * 6 - i * 0.8)) }} />
              ))}
              {C.analyzing}
            </div>
          )}
          {ana && (
            <div style={{ position: "absolute", left: 34, right: 34, top: 400, height: 300, overflow: "hidden" }}>
              {Array.from({ length: 12 }).map((_, i) => {
                const y = i * 58 - ((t - b.send) * 160) % 58;
                const w = [78, 52, 66, 40, 72, 58][i % 6];
                return <div key={i} style={{ position: "absolute", top: y, left: i % 2 ? "auto" : 0, right: i % 2 ? 0 : "auto", width: `${w}%`, height: 36, borderRadius: 18,
                  background: i % 2 ? "#EEF1FF" : "#F1F2F4" }} />;
              })}
              <div style={{ position: "absolute", left: 0, right: 0, top: ((t - b.send) * 260) % 300, height: 6, background: BLUE, opacity: 0.5, boxShadow: `0 0 18px ${BLUE}` }} />
            </div>
          )}

 {/* 답: 두려움 → 자기암시문 */}
          {t >= b.fears - 0.05 && (
            <div style={{ position: "absolute", left: 34, right: 34, top: 210 - up * 40, opacity: sp(b.fears - 0.05) }}>
              <div style={{ fontSize: 34, fontWeight: 900, color: t >= b.flip ? BLUE : RED, marginBottom: 22, display: "flex", alignItems: "center", gap: 12 }}>
                {t >= b.flip ? "✍️ " + C.affirmTitle : "🔍 " + C.fearTitle}
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 20 }}>
                {C.pairs.map((p, i) => {
                  const inn = sp(b.fears + i * fearGap);
                  const fl = sp(b.flip + i * flipGap, { damping: 16, stiffness: 180 });
                  const hlW = lin(b.hl + i * 0.12, b.hl + 0.35 + i * 0.12) * 100;
                  return (
                    <div key={i} style={{ position: "relative", minHeight: 128, borderRadius: 26, padding: "18px 26px",
                      background: fl > 0.5 ? "#F5F7FF" : "#FFF4F4", border: `3px solid ${fl > 0.5 ? "#D9E0FF" : "#FFD9DA"}`,
                      opacity: inn, transform: `translateX(${(1 - inn) * 30}px)` }}>
 {/* 두려움 줄: 뒤집히면 작게 줄 긋고 위로 */}
                      <div style={{ fontSize: interpolate(fl, [0, 1], [44, 26]), fontWeight: 800, color: fl > 0.5 ? SUB : RED,
                        textDecoration: fl > 0.5 ? "line-through" : "none", lineHeight: 1.3 }}>“{p.fear}”</div>
                      {fl > 0 && (
                        <div style={{ fontSize: 46, fontWeight: 900, color: INK, lineHeight: 1.3, marginTop: 6, opacity: fl, transform: `translateY(${(1 - fl) * 16}px)`, wordBreak: "keep-all" }}>
                          <span style={{ backgroundImage: "linear-gradient(transparent 58%, rgba(255,212,0,0.6) 58%)", backgroundRepeat: "no-repeat", backgroundSize: `${hlW}% 100%` }}>{p.affirm}</span>
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>
          )}
        </div>
      </div>
      {pip && <PersonPip pip={pip} enter={enter} top={1330} side={150} vidTop={-380} />}
    </AbsoluteFill>
  );
};

export type AffirmListContent = {
  title: string; // 예: "나의 자기암시문"
  badge: string; // 예: "13분 56초"
  unit: string; // 예: "문장"
  count: number; // 최종 숫자(예: 80)
  lines: string[]; // 실제 원고 문장들(빠르게 올라감)
};

/** beats: count(세기 시작) done(숫자가 다 차는 때) */
export const AffirmListScene: React.FC<{ beats: { count: number; done: number }; content: AffirmListContent; pip?: string }> = ({ beats: b, content: C, pip }) => {
  const { t, sp, lin } = useT();
  const enter = sp(0);
  const p = lin(b.count, b.done);
  const eased = 1 - Math.pow(1 - p, 2);
  const num = Math.round(eased * C.count);
  const ROW = 76;
  const scroll = eased * C.lines.length * ROW + t * 60; // 문장 번호는 쓰지 않는다(화면 문장 수와 말한 숫자가 어긋나 보임)
  const stamp = sp(b.done, { damping: 12, stiffness: 220 });
  return (
    <AbsoluteFill style={{ background: BG, fontFamily: FONT }}>
      <div style={{ position: "absolute", left: 70, right: 70, top: 250, height: 790, ...card, overflow: "hidden",
        transform: `translateY(${(1 - enter) * 60}px) scale(${0.96 + 0.04 * enter})`, opacity: enter }}>
        <div style={{ display: "flex", alignItems: "center", gap: 16, padding: "34px 40px 0" }}>
          <div style={{ fontSize: 44 }}>🎧</div>
          <div style={{ fontSize: 36, fontWeight: 900, color: INK }}>{C.title}</div>
          <div style={{ marginLeft: "auto", fontSize: 26, fontWeight: 800, color: BLUE, background: "#EEF1FF", padding: "8px 20px", borderRadius: 22 }}>{C.badge}</div>
        </div>
 {/* 문장 목록: 빠르게 위로 */}
        <div style={{ position: "absolute", left: 40, right: 40, top: 120, height: 380, overflow: "hidden",
          maskImage: "linear-gradient(transparent, #000 14%, #000 80%, transparent)", WebkitMaskImage: "linear-gradient(transparent, #000 14%, #000 80%, transparent)" }}>
          <div style={{ transform: `translateY(${-scroll}px)` }}>
            {[...C.lines, ...C.lines, ...C.lines].map((l, i) => (
              <div key={i} style={{ height: ROW, display: "flex", alignItems: "center", gap: 18, fontSize: 36, fontWeight: 800, color: "#3A3F47", whiteSpace: "nowrap" }}>
                <span style={{ width: 14, height: 14, borderRadius: 7, background: "#D5DAE3", flexShrink: 0 }} />{l}
              </div>
            ))}
          </div>
        </div>
 {/* 숫자 */}
        <div style={{ position: "absolute", left: 40, right: 40, bottom: 40, display: "flex", alignItems: "baseline", justifyContent: "center", gap: 10 }}>
          <div style={{ fontSize: 190, lineHeight: 1, fontWeight: 900, color: BLUE, transform: `scale(${1 + 0.12 * stamp * (1 - lin(b.done + 0.2, b.done + 0.5))})` }}>{num}</div>
          <div style={{ fontSize: 64, fontWeight: 900, color: INK }}>개 {C.unit}</div>
        </div>
      </div>
      {pip && <PersonPip pip={pip} enter={enter} top={1330} side={150} vidTop={-380} />}
    </AbsoluteFill>
  );
};
