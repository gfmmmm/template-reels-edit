// 공용 장면 부품 (IMG_0519에서 만들어 사용자 승인) — 틀은 코드, 글·숫자·아이콘은 전부 props(broll-plan.json).
// FilterHookScene: 훅 2분할 — "많은 것 → 안 맞는 건 ✕ → 맞는 것만 + 큰 숫자 + 돈 칩"(HookSplitScene 이름으로도 쓸 수 있음)
// ListCardScene: 번호 + 갈래 이름 + 항목 카드가 말에 맞춰 쌓임, 판 높이는 보이는 항목 수만큼(BenefitScene)
// IconPairPop: 인물 위 자막 아래 투명 배경, 아이콘 두 개가 말한 순서대로 뜸(HookPromptMini) — 화살표·노란 글자·흰 카드 없이
// 위치: 카드는 세로 250~1,040px, 아래는 인물 창(scene.tsx PersonPip 기본값). 글씨 최소: 이름 36·핵심 58~68·설명 32px.
import React from "react";
import { AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { PersonPip } from "./scene";


const BG = "#F3F4F6";
const BLUE = "#3B82F6";
const GREEN = "#16A34A";
const INK = "#1F2329";
const SUB = "#8E949C";
const LINE = "#E6E8EC";
const FONT = "'Apple SD Gothic Neo', Pretendard, sans-serif";
const card: React.CSSProperties = {
  background: "#fff", borderRadius: 36, boxShadow: "0 18px 50px rgba(20,30,60,0.10), 0 2px 8px rgba(20,30,60,0.06)",
};

const useAt = (sec: number, cfg = { damping: 18, stiffness: 190 }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const from = Math.round(sec * fps);
  return f < from ? 0 : spring({ frame: f - from, fps, config: cfg });
};

// 한 장 → 다음 장: 들어올 땐 아래에서 반듯하게, 다음 장이 오면 뒤로 물러나 작아지며 흐려진다
const Panel: React.FC<{ from: number; to?: number; top?: number; height?: number; side?: number; children: React.ReactNode }> = ({ from, to, top = 250, height = 790, side = 60, children }) => {
  const inn = useAt(from);
  const out = useAt(to ?? 1e6, { damping: 22, stiffness: 160 });
  const fr = useCurrentFrame();
  const { fps } = useVideoConfig();
  const drift = 1 + 0.012 * Math.max(0, fr / fps - from); // 멈춘 화면처럼 안 보이게 천천히 다가간다
  if (inn === 0) return null;
  if (out > 0.98) return null;
  return (
    <div style={{ position: "absolute", left: side, right: side, top, height, ...card, overflow: "hidden",
      opacity: inn * (1 - out), transform: `translateY(${(1 - inn) * 70 - out * 40}px) scale(${(0.96 + 0.04 * inn) * (1 - 0.08 * out) * drift})`,
      filter: out > 0 ? `blur(${out * 4}px)` : undefined }}>
      {children}
    </div>
  );
};

const Check: React.FC<{ p: number; color?: string; size?: number }> = ({ p, color = GREEN, size = 44 }) => (
  <div style={{ width: size, height: size, borderRadius: size / 2, background: color, color: "#fff", fontSize: size * 0.6, fontWeight: 900,
    display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${p})`, flexShrink: 0 }}>✓</div>
);

/**
 * 프롬프트 넣기 → AI가 질문 → 답하면 내 정보 저장 → 정부 사이트·구글·인스타·스레드 검색 → 리포트.
 * beats(장면 시작부터 초): send, ask, answer, learn, search, src[4], found, report, tiles, cut
 * prompt: 사용자가 실제로 넣은 프롬프트, questions: AI가 묻는 것(리포트 판정 기준에서), sources, report{title, stats, cut}
 */
export const PolicyIntroScene: React.FC<{
  beats: { send: number; ask: number; answer: number; learn: number; search: number; src: number[]; found: number; report: number; tiles: number; cut: number };
  tool: string; prompt: string; questions: string[]; sources: [string, string, string][];
  report: { title: string; sub: string; stats: [number, string][]; cut: [string, string][] };
  pip?: string; pipEnter?: boolean;
  reportShot?: { src: string; width: number; views: { at: number; x: number; y: number; w: number; drift?: number; box?: [number, number, number, number] }[] };
}> = ({ beats: b, tool, prompt, questions, sources, report, pip, pipEnter = true, reportShot }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = f / fps;
  const enter = useAt(0);
  const sent = useAt(b.send, { damping: 18, stiffness: 170 });
  const ask = useAt(b.ask);
  const learn = useAt(b.learn, { damping: 12, stiffness: 200 });
  const isSent = t >= b.send;
  const foundP = useAt(b.found);
  const cutP = useAt(b.cut);
  return (
    <AbsoluteFill style={{ background: BG, fontFamily: FONT }}>
 {/* 1장: 어사이드 채팅 — 프롬프트 붙여 넣기 → 전송 → AI 질문 → 답변 체크 → 내 정보 저장 */}
      <Panel from={0} to={b.search}>
        <div style={{ position: "absolute", left: 36, right: 36, top: 30, display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{ width: 44, height: 44, borderRadius: 12, background: INK, color: "#fff", fontSize: 26, fontWeight: 900, display: "flex", alignItems: "center", justifyContent: "center" }}>A</div>
          <div style={{ fontSize: 36, fontWeight: 900, color: INK }}>{tool}</div>
        </div>
 {/* 프롬프트: 처음엔 입력창에 통째로 붙여 넣은 상태, 보내면 위 말풍선으로 올라가 작아진다 */}
        <div style={{ position: "absolute", right: 36, left: isSent ? 150 : 36,
          top: isSent ? 108 : 120, height: isSent ? interpolate(sent, [0, 1], [560, 190]) : 560, overflow: "hidden",
          background: isSent ? "#E8F0FE" : "#F6F7F9", border: isSent ? "none" : `2px solid ${LINE}`, borderRadius: 28, borderTopRightRadius: isSent ? 8 : 28,
          padding: "22px 28px", fontSize: isSent ? 24 : 31, fontWeight: 600, lineHeight: 1.5, color: INK, whiteSpace: "pre-wrap" }}>
          {prompt}
          <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: 70, background: `linear-gradient(transparent, ${isSent ? "#E8F0FE" : "#F6F7F9"})` }} />
        </div>
        {!isSent && (
          <div style={{ position: "absolute", right: 56, top: 620, width: 72, height: 72, borderRadius: 36, background: BLUE, color: "#fff", fontSize: 38, fontWeight: 900,
            display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${t > b.send - 0.15 ? 0.85 : 1})` }}>↑</div>
        )}
 {/* AI 답: 질문 목록 */}
        {ask > 0 && (
          <div style={{ position: "absolute", left: 36, right: 90, top: 322, opacity: ask, transform: `translateY(${(1 - ask) * 40}px)` }}>
            <div style={{ fontSize: 34, fontWeight: 900, color: INK, marginBottom: 18 }}>먼저 몇 가지만 물어볼게요</div>
            {questions.map((q, i) => {
              const qi = Math.min(1, Math.max(0, (t - b.ask - 0.15 - i * 0.13) * 6));
              const ck = Math.min(1, Math.max(0, (t - b.answer - i * 0.22) * 6));
              return (
                <div key={q} style={{ display: "flex", alignItems: "center", gap: 18, height: 70, marginBottom: 10, padding: "0 24px", borderRadius: 20,
                  background: ck > 0 ? "#ECFDF3" : "#F6F7F9", opacity: qi, transform: `translateX(${(1 - qi) * -30}px)` }}>
                  <div style={{ fontSize: 30, fontWeight: 800, color: SUB, width: 34 }}>{i + 1}</div>
                  <div style={{ fontSize: 33, fontWeight: 800, color: INK, flex: 1 }}>{q}</div>
                  {ck > 0 && <Check p={ck} size={46} />}
                </div>
              );
            })}
          </div>
        )}
 {/* 내 정보 저장 */}
        {learn > 0 && (
          <div style={{ position: "absolute", left: "50%", top: 330, width: 640, marginLeft: -320, height: 330, ...card, background: "#fff",
            boxShadow: "0 24px 60px rgba(20,30,60,0.22)", transform: `scale(${0.7 + 0.3 * learn})`, opacity: learn,
            display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", gap: 14 }}>
            <div style={{ fontSize: 110 }}>📄</div>
            <div style={{ fontSize: 44, fontWeight: 900, color: INK }}>내 정보 저장 완료</div>
            <div style={{ fontSize: 28, fontWeight: 700, color: BLUE }}>이 정보로 정책을 고를게요</div>
          </div>
        )}
      </Panel>

 {/* 2장: 검색 — 출처가 말에 맞춰 하나씩 켜진다 */}
      <Panel from={b.search} to={b.report}>
        <div style={{ position: "absolute", left: 44, right: 44, top: 40, display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{ fontSize: 40, fontWeight: 900, color: INK }}>{t >= b.found ? "정책 찾기 완료" : "내 조건으로 정책 찾는 중…"}</div>
          {t >= b.found && <Check p={foundP} size={50} />}
        </div>
        {sources.map(([icon, name, sub], i) => {
          const on = t >= b.src[i];
          const p = Math.min(1, Math.max(0, (t - b.src[i]) * 5));
          const prog = interpolate(t, [b.src[i], b.found], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          return (
            <div key={name} style={{ position: "absolute", left: 44, right: 44, top: 140 + i * 156, height: 136, borderRadius: 28,
              background: on ? "#F0F6FF" : "#F6F7F9", border: `3px solid ${on ? BLUE : "transparent"}`, display: "flex", alignItems: "center", gap: 24, padding: "0 30px",
              opacity: 0.35 + 0.65 * (on ? 1 : 0), transform: `scale(${1 + 0.03 * (p < 1 ? p : 0)})` }}>
              <div style={{ fontSize: 66, width: 80, textAlign: "center" }}>{icon}</div>
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 40, fontWeight: 900, color: INK }}>{name}</div>
                <div style={{ fontSize: 32, fontWeight: 700, color: SUB, marginTop: 4 }}>{sub}</div>
                <div style={{ height: 10, borderRadius: 5, background: "#E3E8F0", marginTop: 10 }}>
                  <div style={{ width: `${prog * 100}%`, height: 10, borderRadius: 5, background: BLUE }} />
                </div>
              </div>
              {t >= b.found && <Check p={Math.min(1, (t - b.found) * 6)} size={48} color={BLUE} />}
            </div>
          );
        })}
      </Panel>

 {/* 3장(실제 보고서 캡처, "내 실제 보고서를 보여주자, 가독성 있게, 가릴 건 가리고"):
          화면 위쪽까지 넓게 쓰고, 처음엔 보고서 윗부분 전체 → 말에 맞춰 짚을 곳(views)으로 확대·이동 + 노란 테두리 */}
      {reportShot && t >= b.report && (() => {
        const W = 1080 - 2 * 30, H = 950;
        const vs = reportShot.views; // [{at, x, y, w, box?: [x,y,w,h]}] — 캡처 원본 픽셀 기준, w = 화면 폭에 들어갈 원본 폭
        let i = 0; while (i + 1 < vs.length && t >= b.report + vs[i + 1].at) i++;
        const cur = vs[i], prev = vs[Math.max(0, i - 1)];
        const k = i === 0 ? 1 : Math.min(1, spring({ frame: f - Math.round((b.report + cur.at) * fps), fps, config: { damping: 20, stiffness: 120 } }));
        const lerp = (a: number, c: number) => a + (c - a) * k;
        const drift = (t - b.report - cur.at) * (cur.drift ?? 0);
        const x = lerp(prev.x, cur.x), y = lerp(prev.y, cur.y) + drift, w = lerp(prev.w, cur.w);
        const sc = W / w;
        const inn = Math.min(1, (t - b.report) * 12);
        const bx = cur.box;
        return (
          <div style={{ position: "absolute", left: 30, right: 30, top: 95, height: H, ...card, overflow: "hidden", opacity: inn,
            transform: `translateY(${(1 - inn) * 50}px)` }}>
            <Img src={staticFile(reportShot.src)} style={{ position: "absolute", left: -x * sc, top: -y * sc, width: reportShot.width * sc }} />
            {bx && k > 0.6 && <div style={{ position: "absolute", left: (bx[0] - x) * sc - 8, top: (bx[1] - y) * sc - 8, width: bx[2] * sc + 16, height: bx[3] * sc + 16,
              border: "8px solid #F4C70F", borderRadius: 24, boxShadow: "0 0 0 4000px rgba(0,0,0,0.25)", opacity: (k - 0.6) / 0.4 }} />}
          </div>
        );
      })()}
 {/* 3장: 리포트 — 숫자 칸이 차오르고, 해당 안 되는 건 뺐다는 줄 (캡처가 없을 때) */}
      {!reportShot && <Panel from={b.report}>
        <div style={{ position: "absolute", left: 44, right: 44, top: 40 }}>
          <div style={{ fontSize: 26, fontWeight: 800, color: BLUE }}>📑 REPORT</div>
          <div style={{ fontSize: 46, fontWeight: 900, color: INK, marginTop: 6 }}>{report.title}</div>
          <div style={{ fontSize: 27, fontWeight: 700, color: SUB, marginTop: 6 }}>{report.sub}</div>
        </div>
        {(() => {
 // report.stats[0] = 주인공 숫자(가로 한 칸, 크게), 나머지는 아래 작게
          const [hero, ...rest] = report.stats;
          const hp = Math.min(1, Math.max(0, (t - b.tiles) * 2.5));
          return (
            <>
              <div style={{ position: "absolute", left: 44, right: 44, top: 220, height: 230, borderRadius: 30, background: "#EAF2FF", padding: "24px 34px",
                display: "flex", alignItems: "center", gap: 28, opacity: Math.min(1, hp * 2), transform: `scale(${0.9 + 0.1 * Math.min(1, hp * 2)})` }}>
                <div style={{ fontSize: 150, fontWeight: 900, color: BLUE, lineHeight: 1 }}>{Math.round(hero[0] * Math.min(1, hp * 3))}<span style={{ fontSize: 60 }}>건</span></div>
                <div style={{ fontSize: 40, fontWeight: 900, color: INK, lineHeight: 1.25, whiteSpace: "pre-line" }}>{hero[1]}</div>
              </div>
              <div style={{ position: "absolute", left: 44, right: 44, top: 470, display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: 14 }}>
                {rest.map(([n, label], i) => {
                  const p = Math.min(1, Math.max(0, (t - b.tiles - 0.3 - i * 0.15) * 3));
                  return (
                    <div key={label} style={{ height: 170, borderRadius: 24, background: "#F6F7F9", padding: "18px 20px", opacity: Math.min(1, p * 2) }}>
                      <div style={{ fontSize: 64, fontWeight: 900, color: INK, lineHeight: 1 }}>{n}<span style={{ fontSize: 30 }}>건</span></div>
                      <div style={{ fontSize: 30, fontWeight: 800, color: "#5B6270", marginTop: 12, lineHeight: 1.2 }}>{label}</div>
                    </div>
                  );
                })}
              </div>
            </>
          );
        })()}
        {t >= b.cut && (
          <div style={{ position: "absolute", left: 44, right: 44, top: 660, borderRadius: 22, background: "#FEF2F2", padding: "20px 28px", opacity: cutP }}>
            <div style={{ fontSize: 32, fontWeight: 900, color: "#B91C1C" }}>✕ 나한테 안 되는 건 뺐어요</div>
            <div style={{ fontSize: 32, fontWeight: 800, color: "#7F1D1D", marginTop: 8 }}>
              {report.cut.map(([n, why]) => <span key={n} style={{ marginRight: 22 }}><s>{n}</s> <span style={{ color: SUB }}>({why})</span></span>)}
            </div>
          </div>
        )}
      </Panel>}
      {pip && <PersonPip pip={pip} enter={pipEnter ? enter : 1} />}
    </AbsoluteFill>
  );
};

/**
 * 혜택 한 갈래(번호 + 이름) — 카드가 말에 맞춰 하나씩 쌓인다.
 * items: [{icon, name, big(가장 크게 보일 혜택), sub, at(장면 시작부터 초)}]
 */
export const BenefitScene: React.FC<{
  num: string; label: string; items: { icon: string; name: string; big: string; sub: string; at: number; money?: boolean }[]; pip?: string; pipEnter?: boolean;
}> = ({ num, label, items, pip, pipEnter = true }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = f / fps;
  const enter = useAt(0);
  const H = items.length >= 3 ? 200 : 270;
  const drift = 1 + 0.004 * t; // 멈춘 화면처럼 안 보이게 천천히 — 3항목일 때 자막을 덮지 않게 약하게
 // 판 높이는 지금 보이는 항목 수에 맞춰 늘어난다(첫 항목만 있을 때 아래가 빈 흰 판이 되지 않게)
  const grow = items.reduce((acc, it) => acc + (t < it.at ? 0 : spring({ frame: f - Math.round(it.at * fps), fps, config: { damping: 20, stiffness: 180 } })), 0);
  const panelH = 150 + Math.max(1, grow) * (H + 16) + 24;
  return (
    <AbsoluteFill style={{ background: BG, fontFamily: FONT }}>
      <div style={{ position: "absolute", left: 60, right: 60, top: 250, height: panelH, ...card, overflow: "hidden",
        opacity: enter, transform: `translateY(${(1 - enter) * 70}px) scale(${(0.96 + 0.04 * enter) * drift})` }}>
        <div style={{ position: "absolute", left: 40, top: 36, display: "flex", alignItems: "center", gap: 18 }}>
          <div style={{ width: 76, height: 76, borderRadius: 38, background: "#F4C70F", color: INK, fontSize: 46, fontWeight: 900, display: "flex", alignItems: "center", justifyContent: "center" }}>{num}</div>
          <div style={{ fontSize: 50, fontWeight: 900, color: INK }}>{label}</div>
        </div>
        {items.map((it, i) => {
          const p = t < it.at ? 0 : spring({ frame: f - Math.round(it.at * fps), fps, config: { damping: 16, stiffness: 190 } });
          const ck = Math.min(1, Math.max(0, (t - it.at - 0.25) * 5));
          return (
            <div key={it.name} style={{ position: "absolute", left: 40, right: 40, top: 150 + i * (H + 16), height: H, borderRadius: 30,
              background: "#F7F9FC", border: `2px solid ${LINE}`, display: "flex", alignItems: "center", gap: 26, padding: "0 30px",
              opacity: p, transform: `translateY(${(1 - p) * 50}px) scale(${0.94 + 0.06 * p})` }}>
              <div style={{ width: 130, height: 130, borderRadius: 32, background: "#fff", boxShadow: "0 6px 16px rgba(20,30,60,0.08)", fontSize: 72,
                display: "flex", alignItems: "center", justifyContent: "center", flexShrink: 0 }}>{it.icon}</div>
              <div style={{ flex: 1, minWidth: 0 }}>
                <div style={{ fontSize: 36, fontWeight: 800, color: SUB }}>{it.name}</div>
                <div style={{ fontSize: it.money ? 68 : 58, fontWeight: 900, color: it.money ? "#1D4ED8" : INK, marginTop: 2, lineHeight: 1.1 }}>
                  <span style={{ background: `linear-gradient(transparent 58%, rgba(244,199,15,${0.75 * ck}) 58%)` }}>{it.big}</span>
                </div>
                <div style={{ fontSize: 32, fontWeight: 700, color: "#5B6270", marginTop: 6 }}>{it.sub}</div>
              </div>
            </div>
          );
        })}
      </div>
      {pip && <PersonPip pip={pip} enter={pipEnter ? enter : 1} />}
    </AbsoluteFill>
  );
};

/**
 * 훅 증거 카드 ("결과를 먼저 보여주기"): 인물 위 자막 아래(세로 약 1,190~1,480px)에 흰 카드가 톡 튀어나와
 * 실제 리포트에서 나온 혜택이 0.45초씩 바뀌어 보이고, "싹 가져옵니다"에서 "내게 맞는 정책 11건"으로 마무리한다. 투명 배경.
 * chips: [[이모지, 이름, 혜택]], countAt: 11건으로 바뀌는 초, count/countLabel: 리포트 숫자
 */
export const HookProof: React.FC<{ chips: [string, string, string][]; chipFrom?: number; chipEvery?: number; countAt: number; count: number; countLabel: string }> = ({
  chips, chipFrom = 0.15, chipEvery = 0.45, countAt, count, countLabel,
}) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = f / fps;
  const enter = spring({ frame: f - Math.round(0.05 * fps), fps, config: { damping: 14, stiffness: 220 } });
  const showCount = t >= countAt;
  const idx = Math.min(chips.length - 1, Math.max(0, Math.floor((t - chipFrom) / chipEvery)));
  const local = showCount ? t - countAt : (t - chipFrom) - idx * chipEvery;
  const pop = Math.min(1, Math.max(0, local * 8));
  const [ic, name, val] = chips[idx];
  const n = Math.round(count * Math.min(1, (t - countAt) * 3));
  return (
    <AbsoluteFill style={{ fontFamily: FONT }}>
      <div style={{ position: "absolute", left: 110, width: 750, top: 1195, height: 270, ...card, borderRadius: 34,
        transform: `scale(${0.6 + 0.4 * enter})`, opacity: Math.min(1, enter * 1.5), display: "flex", alignItems: "center", gap: 28, padding: "0 36px" }}>
        {!showCount ? (
          <>
            <div style={{ width: 150, height: 150, borderRadius: 36, background: "#F3F6FB", fontSize: 92, display: "flex", alignItems: "center", justifyContent: "center",
              transform: `scale(${0.7 + 0.3 * pop})` }}>{ic}</div>
            <div style={{ opacity: pop, transform: `translateY(${(1 - pop) * 16}px)` }}>
              <div style={{ fontSize: 38, fontWeight: 800, color: SUB }}>{name}</div>
              <div style={{ fontSize: 66, fontWeight: 900, color: "#1D4ED8", lineHeight: 1.1, marginTop: 4 }}>{val}</div>
            </div>
            <div style={{ position: "absolute", right: 26, top: 22, fontSize: 26, fontWeight: 800, color: SUB }}>{idx + 1}/{chips.length}</div>
          </>
        ) : (
          <>
            <div style={{ fontSize: 140, fontWeight: 900, color: BLUE, lineHeight: 1, transform: `scale(${0.8 + 0.2 * pop})` }}>{n}<span style={{ fontSize: 60 }}>건</span></div>
            <div style={{ fontSize: 44, fontWeight: 900, color: INK, lineHeight: 1.25, whiteSpace: "pre-line" }}>{countLabel}</div>
          </>
        )}
      </div>
    </AbsoluteFill>
  );
};

/**
 * 훅 2분할: "AI한테 프롬프트 하나만 넣으면 / 나라에서 주는 혜택을 / 내게 맞는 걸로만 / 싹 가져옵니다"를
 * 위 카드 + 아래 인물 창으로. 프롬프트 한 장이 AI로 들어감 → 혜택 타일이 쏟아짐 → 안 맞는 건 흐려지고 맞는 건 ✓ →
 * 맞는 것만 모여 "11건" + 돈 칩 3개(와 포인트). 타일 이름·숫자는 리포트 원문에서만.
 * 상단 제목이 떠 있는 동안(titleEnd까지)은 카드를 제목 아래(세로 520px~)로 낮췄다가 제목이 사라지면 위로 넓힌다.
 * beats(장면 시작부터 초): prompt, one, drop, spill, filter, gather
 */
export const HookSplitScene: React.FC<{
  beats: { prompt: number; one: number; drop: number; spill: number; filter: number; gather: number };
  titleEnd: number; tool: string; tiles: [string, string, boolean, string?][]; total: number; count: number; countLabel: string; money: [string, string, string][];
  pip?: string;
}> = ({ beats: b, titleEnd, tool, tiles, total, count, countLabel, money, pip }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = f / fps;
  const enter = useAt(0);
  const growS = useAt(Math.max(0, titleEnd), { damping: 20, stiffness: 170 });
  const grow = titleEnd <= 0 ? 1 : growS; // 제목이 이미 사라진 뒤 시작하면 처음부터 넓게
  const top = 520 - 270 * grow;
  const height = 520 + 270 * grow;
  const drift = 1 + 0.01 * t;
  const pIn = useAt(b.prompt);
  const drop = useAt(b.drop, { damping: 16, stiffness: 150 });
  const spill = t >= b.spill;
  const filt = Math.min(1, Math.max(0, (t - b.filter) * 3));
  const gather = useAt(b.gather, { damping: 18, stiffness: 160 });
  const n = Math.round(count * Math.min(1, Math.max(0, (t - b.gather - 0.1) * 2.5)));
  const aiGlow = t >= b.drop ? 0.5 + 0.5 * Math.sin((t - b.drop) * 12) : 0;
  return (
    <AbsoluteFill style={{ background: BG, fontFamily: FONT }}>
      <div style={{ position: "absolute", left: 60, right: 60, top, height, ...card, overflow: "hidden",
        opacity: enter, transform: `translateY(${(1 - enter) * 60}px) scale(${(0.96 + 0.04 * enter) * drift})` }}>
 {/* 1) 프롬프트 한 장 → AI */}
        {!spill && (
          <>
            <div style={{ position: "absolute", left: "50%", top: 70, marginLeft: 120, width: 240, height: 240, borderRadius: 60, background: INK,
              color: "#fff", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
              boxShadow: `0 0 ${30 + 50 * aiGlow}px rgba(59,130,246,${0.25 + 0.5 * aiGlow})` }}>
              <div style={{ fontSize: 110, fontWeight: 900, lineHeight: 1 }}>A</div>
              <div style={{ fontSize: 34, fontWeight: 800, marginTop: 8 }}>{tool}</div>
            </div>
            <div style={{ position: "absolute", left: 120 + drop * 330, top: 80 + drop * 40, width: 250, height: 300, borderRadius: 26, background: "#fff",
              border: `4px solid ${BLUE}`, boxShadow: "0 12px 30px rgba(20,30,60,0.15)", opacity: pIn * (1 - drop * 0.9),
              transform: `scale(${(0.6 + 0.4 * pIn) * (1 - 0.5 * drop)})`, padding: 22 }}>
              <div style={{ fontSize: 34, fontWeight: 900, color: BLUE }}>📄 프롬프트</div>
              {[0, 1, 2, 3, 4].map((i) => <div key={i} style={{ height: 14, borderRadius: 7, background: "#E3E8F0", marginTop: 18, width: `${90 - i * 9}%` }} />)}
            </div>
            {t >= b.one && t < b.drop + 0.3 && (
              <div style={{ position: "absolute", left: 90, top: 375, fontSize: 52, fontWeight: 900, color: INK,
                transform: `scale(${Math.min(1, (t - b.one) * 6)})` }}>딱 <span style={{ color: BLUE }}>1개</span>만</div>
            )}
          </>
        )}
 {/* 2) 큰 숫자 + 글자 없는 아이콘 벽 → 안 맞는 건 꺼짐 → "걸로만"에서 안 맞는 건 빠지고 맞는 것만 세로로 모여
            줄마다 혜택 세부 내용이 붙는 보고서가 된다 (사용자 2026-10-24: 각각에 대해 세로로 나열된 보고서가 자연스러운 흐름) */}
        {spill && (() => {
          const COLS = 6, CW = (1080 - 120 - 72 - 5 * 14) / COLS, CH = 110;
          const wall = Array.from({ length: 24 }, (_, i) => {
            const tl = tiles[i % tiles.length];
            return { ic: tl[0], name: tl[1], ok: i < tiles.length && tl[2], detail: (tl as any)[3] as string | undefined };
          });
          const okList = wall.filter((w) => w.ok);
          const counted = Math.round(total * Math.min(1, (t - b.spill) / Math.max(0.3, b.filter - b.spill - 0.1)));
          const RH = 92; // 보고서 한 줄 높이 — 6줄만 또렷하게, 7줄째부터는 아래 그러데이션에 묻혀 '더 있다'는 느낌만(사용자 2026-10-24)
          return (
            <>
              <div style={{ position: "absolute", left: 0, right: 0, top: 36, textAlign: "center", opacity: Math.max(0, 1 - gather * 3) }}>
                <div style={{ fontSize: 40, fontWeight: 900, color: SUB }}>{t >= b.filter ? "나한테 맞는 것만" : "나라에서 주는 혜택"}</div>
                <div style={{ fontSize: 130, fontWeight: 900, color: t >= b.filter ? GREEN : BLUE, lineHeight: 1.05 }}>
                  {t >= b.filter ? <>✓ 고르는 중</> : <>{counted.toLocaleString()}<span style={{ fontSize: 64 }}>건</span></>}
                </div>
              </div>
              {gather > 0 && (
                <div style={{ position: "absolute", left: 40, right: 40, top: 34, display: "flex", alignItems: "baseline", gap: 16, opacity: Math.max(0, gather * 2 - 0.6) }}>
                  <div style={{ fontSize: 44, fontWeight: 900, color: INK }}>📑 내 맞춤 혜택 리포트</div>
                </div>
              )}
              {wall.map((w, i) => {
                const p = Math.min(1, Math.max(0, (t - b.spill - i * 0.025) * 7));
                const gx = 36 + (i % COLS) * (CW + 14), gy = 250 + Math.floor(i / COLS) * (CH + 14);
                if (!w.ok) {
                  return (
                    <div key={i} style={{ position: "absolute", left: gx, top: gy, width: CW, height: CH, borderRadius: 22, background: "#F3F4F6",
                      display: "flex", alignItems: "center", justifyContent: "center", fontSize: 64, filter: filt > 0 ? `grayscale(${filt})` : undefined,
                      opacity: p * (1 - 0.8 * filt) * (1 - gather), transform: `translateY(${(1 - p) * -50 + gather * 60}px) scale(${(0.7 + 0.3 * p) * (1 - 0.1 * filt) * (1 - 0.4 * gather)})` }}>{w.ic}</div>
                  );
                }
                const k = okList.indexOf(w);
                const m = Math.min(1, Math.max(0, gather * 1.15 - k * 0.012));
                const tx = 40, ty = 125 + k * RH, size = RH - 16;
                const x = gx + (tx - gx) * m, y = gy + (ty - gy) * m, wdt = CW + (size - CW) * m, hgt = CH + (size - CH) * m;
                const d = k > 6 ? 0 : Math.min(1, Math.max(0, (t - b.gather - 0.3 - k * 0.07) * 6)); // 8줄째부터는 글 없이 아이콘만 그러데이션 아래로
                return (
                  <React.Fragment key={i}>
                    <div style={{ position: "absolute", left: x, top: y, width: wdt, height: hgt, borderRadius: 22 - 8 * m,
                      background: filt > 0 ? "#ECFDF3" : "#F3F4F6", border: `${4 - 2 * m}px solid ${filt > 0 ? GREEN : "transparent"}`,
                      display: "flex", alignItems: "center", justifyContent: "center", fontSize: 64 - 18 * m, opacity: p,
                      transform: `translateY(${(1 - p) * -50}px) scale(${(0.7 + 0.3 * p) * (1 + 0.08 * filt * (1 - m))})` }}>{w.ic}</div>
                    {d > 0 && (
                      <div style={{ position: "absolute", left: tx + size + 18, right: 40, top: ty, height: size, display: "flex", alignItems: "center",
                        justifyContent: "space-between", borderBottom: `2px solid ${LINE}`, opacity: d, transform: `translateX(${(1 - d) * 30}px)` }}>
                        <div style={{ fontSize: 40, fontWeight: 800, color: INK }}>{w.name}</div>
                        <div style={{ fontSize: 42, fontWeight: 900, color: "#1D4ED8" }}>{w.detail}</div>
                      </div>
                    )}
                  </React.Fragment>
                );
              })}
              {gather > 0 && <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: 170, opacity: gather,
                background: "linear-gradient(rgba(255,255,255,0), #fff 85%)" }} />}
            </>
          );
        })()}
      </div>
      {pip && <PersonPip pip={pip} enter={enter} />}
    </AbsoluteFill>
  );
};

/**
 * 훅 앞부분 "AI한테 프롬프트 하나만 넣으면" — 인물 위, 자막 바로 아래(세로 약 1,190~1,470px) 투명 배경 작은 그래픽.
 * 프롬프트 문서 한 장이 AI 칩으로 쏙 들어가고 "딱 1개" 표시. beats(장면 시작부터 초): prompt, one, drop
 */
export const HookPromptMini: React.FC<{ beats: { prompt: number }; tool?: string; icons?: [string, string] }> = ({ beats: b, icons = ["🤖", "doc"] }) => {
 // 투명 바탕, "AI한테"에 로봇 → "프롬프트"에 문서가 옆에 나타나는 정도로만. 화살표·노란 표시·들어가는 움직임 없음
 // 번지는 그림자는 CapCut에서 덩어리가 되므로(IMG_0517) 또렷한 흰 테두리(스티커)로 — 확대도 그대로 걸 수 있다
  const robot = useAt(0.03, { damping: 12, stiffness: 220 });
  const doc = useAt(b.prompt, { damping: 12, stiffness: 220 });
  const shadow = "drop-shadow(5px 0 0 #fff) drop-shadow(-5px 0 0 #fff) drop-shadow(0 5px 0 #fff) drop-shadow(0 -5px 0 #fff)";
  return (
    <AbsoluteFill style={{ fontFamily: FONT }}>
      <div style={{ position: "absolute", left: 200, width: 600, top: 1200, height: 260 }}>
        <div style={{ position: "absolute", left: 0, top: 0, width: 250, height: 250, display: "flex", alignItems: "center", justifyContent: "center",
          fontSize: 200, lineHeight: 1, filter: shadow, opacity: Math.min(1, robot * 1.5), transform: `scale(${0.5 + 0.5 * robot})` }}>{icons[0]}</div>
        {icons[1] !== "doc" ? (
          <div style={{ position: "absolute", right: 0, top: 0, width: 250, height: 250, display: "flex", alignItems: "center", justifyContent: "center",
            fontSize: 200, lineHeight: 1, filter: shadow, opacity: Math.min(1, doc * 1.5), transform: `scale(${0.5 + 0.5 * doc})` }}>{icons[1]}</div>
        ) : <div style={{ position: "absolute", right: 30, top: 20, width: 175, height: 220, borderRadius: 22, background: "#fff", border: `5px solid ${BLUE}`,
          padding: 18, filter: shadow, opacity: Math.min(1, doc * 1.5), transform: `scale(${0.5 + 0.5 * doc})` }}>
          <div style={{ fontSize: 34 }}>📄</div>
          {[0, 1, 2, 3].map((i) => <div key={i} style={{ height: 13, borderRadius: 7, background: "#D5DCE8", marginTop: 16, width: `${90 - i * 12}%` }} />)}
        </div>}
      </div>
    </AbsoluteFill>
  );
};

export const FilterHookScene = HookSplitScene;
export const ListCardScene = BenefitScene;
export const IconPairPop = HookPromptMini;

/**
 * 숫자 팝 (공용): 인물 위 자막 아래(세로 약 1,190~1,450px) 투명 배경 — 영상에서 가장 센 숫자를 크게.
 * big: 큰 숫자 글(파랑 110px), small: 위 작은 설명(흰 글씨 40px), 둘 다 그림자. 흰 카드 없음.
 */
export const NumberPop: React.FC<{ big: string; small?: string }> = ({ big, small }) => {
  const p = useAt(0.02, { damping: 11, stiffness: 230 });
  const sh = "none"; // 번지는 그림자 없이 또렷한 테두리만(CapCut 반투명 덩어리 방지)
  return (
    <AbsoluteFill style={{ fontFamily: FONT }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 1200, textAlign: "center", opacity: Math.min(1, p * 1.5), transform: `scale(${0.5 + 0.5 * p})` }}>
        {small && <div style={{ fontSize: 44, fontWeight: 900, color: "#fff", WebkitTextStroke: "8px #111", paintOrder: "stroke fill", textShadow: sh }}>{small}</div>}
        <div style={{ fontSize: 120, fontWeight: 900, color: "#3B7BFF", lineHeight: 1.1, WebkitTextStroke: "14px #fff", paintOrder: "stroke fill", textShadow: sh }}>{big}</div>
      </div>
    </AbsoluteFill>
  );
};

/**
 * 댓글 한 줄 (공용): 마무리 "댓글에 ○○ 남기면" — 자막 아래 인스타 댓글처럼 프로필 동그라미 + 키워드(노랑 칠, 64px).
 */
export const CommentPop: React.FC<{ word: string; label?: string }> = ({ word, label = "댓글" }) => {
  const p = useAt(0.02, { damping: 12, stiffness: 220 });
  return (
    <AbsoluteFill style={{ fontFamily: FONT }}>
      <div style={{ position: "absolute", left: 170, width: 640, top: 1210, height: 170, borderRadius: 85, background: "#fff", border: "4px solid #E6E8EC", display: "flex", alignItems: "center", gap: 26, padding: "0 36px",
        opacity: Math.min(1, p * 1.5), transform: `translateY(${(1 - p) * 30}px) scale(${0.7 + 0.3 * p})` }}>
        <div style={{ width: 96, height: 96, borderRadius: 48, background: "linear-gradient(45deg,#FEDA75,#FA7E1E,#D62976,#962FBF)", fontSize: 50,
          display: "flex", alignItems: "center", justifyContent: "center" }}>💬</div>
        <div>
          <div style={{ fontSize: 30, fontWeight: 800, color: SUB }}>{label}</div>
          <div style={{ fontSize: 64, fontWeight: 900, color: INK, lineHeight: 1.1 }}><span style={{ background: "linear-gradient(transparent 55%, #F4C70F 55%)" }}>{word}</span></div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

/**
 * 실제 문서 짚기 (공용"그 뒤 항목들도 실제 보고서를 토대로"): 실제 캡처(가릴 것 가린 것) 위를
 * 항목마다 그 카드로 확대 이동하고, 핵심 줄에 노란 형광펜 + 아래에 큰 숫자 스티커. 화면 위쪽까지 넓게(세로 95~1045px).
 * src/width: public 안 캡처와 원본 폭(px), items: [{at, view:{x,y,w}, mark:[x,y,w,h], big, small?}] — 좌표는 캡처 원본 픽셀
 */
export const ReportFocusScene: React.FC<{
  src: string; width: number; num?: string; label?: string;
  items: { at: number; view: { x: number; y: number; w: number }; mark?: [number, number, number, number]; big: string; small?: string }[];
  pip?: string; pipEnter?: boolean;
}> = ({ src, width, num, label, items, pip, pipEnter = true }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = f / fps;
  const enter = useAt(0);
  const W = 1080 - 60, H = 950;
  let i = 0; while (i + 1 < items.length && t >= items[i + 1].at) i++;
  const cur = items[i], prev = items[Math.max(0, i - 1)];
  const k = i === 0 ? 1 : Math.min(1, spring({ frame: f - Math.round(cur.at * fps), fps, config: { damping: 20, stiffness: 120 } }));
  const L = (a: number, c: number) => a + (c - a) * k;
  const vx = L(prev.view.x, cur.view.x), vy = L(prev.view.y, cur.view.y) + (t - cur.at) * 25, vw = L(prev.view.w, cur.view.w);
  const sc = W / vw;
  const mk = cur.mark;
  const mp = Math.min(1, Math.max(0, (t - cur.at - (i === 0 ? 0.15 : 0.45)) * 4));
  const st = Math.min(1, Math.max(0, (t - cur.at - (i === 0 ? 0.25 : 0.55)) * 5));
  return (
    <AbsoluteFill style={{ background: BG, fontFamily: FONT }}>
      <div style={{ position: "absolute", left: 30, right: 30, top: 95, height: H, ...card, overflow: "hidden", opacity: enter,
        transform: `translateY(${(1 - enter) * 60}px) scale(${0.96 + 0.04 * enter})` }}>
        <Img src={staticFile(src)} style={{ position: "absolute", left: -vx * sc, top: -vy * sc, width: width * sc }} />
        {mk && mp > 0 && <div style={{ position: "absolute", left: (mk[0] - vx) * sc - 6, top: (mk[1] - vy) * sc - 4, width: (mk[2] * sc + 12) * mp, height: mk[3] * sc + 8,
          background: "rgba(244,199,15,0.38)", borderRadius: 10, mixBlendMode: "multiply" }} />}
        {num && <div style={{ position: "absolute", left: 22, top: 22, display: "flex", alignItems: "center", gap: 12, background: "#fff", borderRadius: 40,
          padding: "8px 22px 8px 10px", boxShadow: "0 4px 14px rgba(20,30,60,0.15)" }}>
          <div style={{ width: 56, height: 56, borderRadius: 28, background: "#F4C70F", fontSize: 34, fontWeight: 900, color: INK, display: "flex", alignItems: "center", justifyContent: "center" }}>{num}</div>
          <div style={{ fontSize: 38, fontWeight: 900, color: INK }}>{label}</div>
        </div>}
        {cur.big && <div style={{ position: "absolute", left: 0, right: 0, bottom: 34, display: "flex", justifyContent: "center", opacity: st, transform: `translateY(${(1 - st) * 30}px) scale(${0.85 + 0.15 * st})` }}>
          <div style={{ background: "#1F2329", color: "#fff", borderRadius: 30, padding: "18px 40px", textAlign: "center", boxShadow: "0 10px 24px rgba(0,0,0,0.25)" }}>
            {cur.small && <div style={{ fontSize: 34, fontWeight: 800, color: "#F4C70F" }}>{cur.small}</div>}
            <div style={{ fontSize: 70, fontWeight: 900, lineHeight: 1.1 }}>{cur.big}</div>
          </div>
        </div>}
      </div>
      {pip && <PersonPip pip={pip} enter={pipEnter ? enter : 1} />}
    </AbsoluteFill>
  );
};
