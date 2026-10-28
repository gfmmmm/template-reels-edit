// AI 에이전트 시대 릴스 장면 6종 — scene.tsx와 같은 톤(연한 회색 바탕 + 흰 둥근 카드 + 파랑 포인트, 기울기 없음).
// 카드는 세로 250~1040px 안(자막 1,075~1,165px 자리 비움), 아래는 인물 창(PersonPip).
// 시각(beats)은 장면 시작부터의 초. 영상마다 바뀌는 글·숫자·그림 경로는 전부 props로 받는다.
import React from "react";
import { AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { PersonPip } from "./scene";

const BG = "#F3F4F6";
const BLUE = "#3B5BFD";
const INK = "#1F2329";
const SUB = "#8A9099";
const LINE = "#E6E8EC";
const GREEN = "#12B76A";
const RED = "#EC1D1D";
const FONT = "'Apple SD Gothic Neo', Pretendard, sans-serif";
const card: React.CSSProperties = {
  background: "#fff", borderRadius: 36, boxShadow: "0 18px 50px rgba(20,30,60,0.10), 0 2px 8px rgba(20,30,60,0.06)",
};

const useT = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = f / fps;
  const sp = (at: number, cfg = { damping: 20, stiffness: 170 }) => (t < at ? 0 : spring({ frame: f - at * fps, fps, config: cfg }));
  const lin = (a: number, b: number) => interpolate(t, [a, b], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return { f, fps, t, sp, lin };
};

const typed = (text: string, t: number, at: number, end: number) => {
  const n = Math.max(0, Math.min(text.length, Math.floor(((t - at) / Math.max(0.3, end - at)) * text.length)));
  return { shown: text.slice(0, n), typing: t >= at && n < text.length };
};
const Caret: React.FC<{ on: boolean }> = ({ on }) => {
  const { f } = useT();
  return on ? <span style={{ display: "inline-block", width: 4, height: "1em", background: BLUE, marginLeft: 4, verticalAlign: "-0.12em", opacity: Math.floor(f / 8) % 2 ? 0 : 1 }} /> : null;
};

// 뒤로 물러나며 작아지고 흐려지는 카드 (다음 카드가 오면)
const backStyle = (back: number): React.CSSProperties => ({
  transform: `translateY(${-back * 40}px) scale(${1 - 0.1 * back})`, opacity: 1 - 0.65 * back, filter: `blur(${back * 3}px)`,
});

// 내 AI 비서 머리표 (이름은 지어내지 않고 "내 AI 비서")
const AgentHead: React.FC<{ label?: string; sub?: string }> = ({ label = "내 AI 비서", sub }) => (
  <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
    <div style={{ width: 64, height: 64, borderRadius: 20, background: `linear-gradient(135deg,#7C9BFF,${BLUE})`, color: "#fff", fontSize: 36, display: "flex", alignItems: "center", justifyContent: "center" }}>✦</div>
    <div>
      <div style={{ fontSize: 34, fontWeight: 900, color: INK }}>{label}</div>
      {sub && <div style={{ fontSize: 28, fontWeight: 700, color: BLUE, marginTop: 2 }}>{sub}</div>}
    </div>
  </div>
);

const MyBubble: React.FC<{ text: string; at: number; end: number; size?: number }> = ({ text, at, end, size = 50 }) => {
  const { t, sp } = useT();
  const p = sp(at);
  const ty = typed(text, t, at + 0.1, end);
  return (
    <div style={{ alignSelf: "flex-end", maxWidth: 780, background: BLUE, color: "#fff", fontSize: size, fontWeight: 800, lineHeight: 1.35, padding: "20px 28px",
      borderRadius: 32, borderTopRightRadius: 8, opacity: p, transform: `translateY(${(1 - p) * 30}px)`, minHeight: size * 1.35 }}>
      {ty.shown}<Caret on={ty.typing} />
    </div>
  );
};

// ───────────────────────── ① 대신 전화하기
// 내 부탁(타이핑) → 전화 화면(파형 + 통화 글자) → 예약 완료 카드
export const CallScene: React.FC<{
  request: string; place: string; lines: { who: "ai" | "them"; text: string; at: number }[];
  beats: { call: number; done: number }; done: { title: string; when: string; name: string }; pip?: string; pipIn?: boolean;
}> = ({ request, place, lines, beats, done, pip, pipIn = true }) => {
  const { t, sp, lin } = useT();
  const enter = sp(0, { damping: 22, stiffness: 300 });
  const call = sp(beats.call);
  const fin = sp(beats.done, { damping: 14, stiffness: 160 });
  const secs = Math.max(0, Math.floor((t - beats.call) * 1 + 12));
  return (
    <AbsoluteFill style={{ background: BG, fontFamily: FONT }}>
 {/* 부탁 */}
      <div style={{ position: "absolute", left: 70, right: 70, top: 300, height: 400, ...card, padding: 40, display: "flex", flexDirection: "column", gap: 40,
        opacity: enter, transform: `translateY(${(1 - enter) * 60}px)`, ...(call > 0 ? backStyle(call * 0.6) : {}) }}>
        <AgentHead sub="채팅" />
        <MyBubble text={request} at={0.15} end={beats.call - 0.3} />
      </div>
 {/* 통화 화면 */}
      {t >= beats.call && (
        <div style={{ position: "absolute", left: 90, right: 90, top: 400, height: 640, borderRadius: 48, background: "linear-gradient(180deg,#1C2340,#0F1426)", padding: "36px 40px",
          boxShadow: "0 24px 60px rgba(10,20,50,0.35)", opacity: call, transform: `translateY(${(1 - call) * 120}px) scale(${0.94 + 0.06 * call})`, ...(fin > 0 ? backStyle(fin * 0.7) : {}) }}>
          <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
            <div style={{ width: 22, height: 22, borderRadius: 11, background: "#32D74B", boxShadow: "0 0 14px #32D74B", opacity: 0.6 + 0.4 * Math.abs(Math.sin(t * 4)) }} />
            <div style={{ fontSize: 30, fontWeight: 800, color: "#AEB6D6" }}>AI 비서가 대신 통화 중</div>
            <div style={{ marginLeft: "auto", fontSize: 30, fontWeight: 800, color: "#fff", fontVariantNumeric: "tabular-nums" }}>00:{String(secs).padStart(2, "0")}</div>
          </div>
          <div style={{ fontSize: 54, fontWeight: 900, color: "#fff", marginTop: 18 }}>📞 {place}</div>
 {/* 파형 */}
          <div style={{ display: "flex", alignItems: "center", gap: 8, height: 90, marginTop: 14 }}>
            {Array.from({ length: 34 }).map((_, i) => {
              const h = 14 + 60 * Math.abs(Math.sin(t * 9 + i * 0.7) * Math.sin(t * 3.3 + i * 0.31));
              return <div key={i} style={{ width: 12, height: h, borderRadius: 6, background: i % 2 ? "#5B7BFF" : "#8FA5FF" }} />;
            })}
          </div>
 {/* 통화 글자 */}
          <div style={{ display: "flex", flexDirection: "column", gap: 18, marginTop: 22 }}>
            {lines.map((l, i) => {
              const p = sp(l.at);
              if (p <= 0) return null;
              const ai = l.who === "ai";
              return (
                <div key={i} style={{ alignSelf: ai ? "flex-start" : "flex-end", maxWidth: 680, opacity: p, transform: `translateY(${(1 - p) * 24}px)` }}>
                  <div style={{ fontSize: 30, fontWeight: 800, color: ai ? "#8FA5FF" : "#9BE7B5", marginBottom: 6, textAlign: ai ? "left" : "right" }}>{ai ? "🤖 AI 비서" : "🏥 병원"}</div>
                  <div style={{ fontSize: 38, fontWeight: 800, color: "#fff", lineHeight: 1.35, wordBreak: "keep-all", background: ai ? "rgba(91,123,255,0.28)" : "rgba(50,215,75,0.22)", padding: "16px 24px", borderRadius: 26 }}>{l.text}</div>
                </div>
              );
            })}
          </div>
        </div>
      )}
 {/* 예약 완료 */}
      {t >= beats.done && (
        <div style={{ position: "absolute", left: 110, right: 110, top: 470, height: 470, ...card, padding: 44, textAlign: "center",
          opacity: fin, transform: `translateY(${(1 - fin) * 80}px) scale(${0.9 + 0.1 * fin})` }}>
          <div style={{ width: 130, height: 130, borderRadius: 65, background: GREEN, color: "#fff", fontSize: 84, fontWeight: 900, margin: "0 auto", display: "flex", alignItems: "center", justifyContent: "center",
            transform: `scale(${sp(beats.done + 0.15, { damping: 9, stiffness: 220 })})` }}>✓</div>
          <div style={{ fontSize: 64, fontWeight: 900, color: INK, marginTop: 28 }}>{done.title}</div>
          <div style={{ fontSize: 46, fontWeight: 800, color: BLUE, marginTop: 18 }}>{done.when}</div>
          <div style={{ fontSize: 32, fontWeight: 700, color: SUB, marginTop: 12, opacity: lin(beats.done + 0.3, beats.done + 0.6) }}>{done.name}</div>
        </div>
      )}
      {pip && <PersonPip pip={pip} enter={pipIn ? enter : 1} vidTop={-180} />}
    </AbsoluteFill>
  );
};

// ───────────────────────── ② 대신 장보기
// "햇반 떨어졌으니까 시켜줘" → 쿠팡 검색·최저가 비교 → 장바구니 담기 → 결제 승인 요청
export const ShopScene: React.FC<{
  request: string; product: string; productImg?: string; store: string;
  beats: { ask: number; search: number; cart: number; approve: number }; pip?: string; pipIn?: boolean; title?: string;
}> = ({ request, product, productImg, store, beats, pip, pipIn = true, title }) => {
  const { t, sp, lin } = useT();
  const enter = sp(0, { damping: 22, stiffness: 300 });
  const srch = sp(beats.search);
  const cart = sp(beats.cart, { damping: 12, stiffness: 200 });
  const appr = sp(beats.approve, { damping: 16, stiffness: 180 });
  const scan = lin(beats.search + 0.2, beats.cart - 0.15);
  const best = 2;
  return (
    <AbsoluteFill style={{ background: BG, fontFamily: FONT }}>
      <div style={{ position: "absolute", left: 70, right: 70, top: 300, ...card, padding: 34, overflow: "hidden", opacity: enter, transform: `translateY(${(1 - enter) * 60}px)` }}>
        <AgentHead sub="장보기" />
        {title && <div style={{ fontSize: 64, fontWeight: 900, color: INK, marginTop: 30, opacity: sp(0.15), transform: `translateY(${(1 - sp(0.15)) * 30}px)` }}>{title}</div>}
        <div style={{ display: "flex", flexDirection: "column", marginTop: 26 }}>
          {t >= beats.ask && <MyBubble text={request} at={beats.ask} end={beats.search - 0.2} />}
        </div>
 {/* 쿠팡 검색 결과 */}
        {t >= beats.search && (
          <div style={{ marginTop: 26, borderRadius: 28, border: `3px solid ${LINE}`, padding: "20px 22px", opacity: srch, transform: `translateY(${(1 - srch) * 40}px)` }}>
            <div style={{ display: "flex", alignItems: "center", gap: 14, fontSize: 38, fontWeight: 800, color: INK }}>
              <span style={{ fontSize: 36, fontWeight: 900, color: "#fff", background: "#E52528", padding: "6px 16px", borderRadius: 12 }}>{store}</span>
              <span>“{product}” 최저가 찾는 중</span>
              <span style={{ marginLeft: "auto", color: BLUE }}>{t < beats.cart ? "🔍" : "✓"}</span>
            </div>
            <div style={{ display: "flex", gap: 16, marginTop: 18 }}>
              {[0, 1, 2, 3].map((i) => {
                const seen = scan * 4 > i;
                const win = t >= beats.cart && i === best;
                return (
                  <div key={i} style={{ flex: 1, height: 200, borderRadius: 20, background: "#F6F7F9", position: "relative", overflow: "hidden",
                    border: win ? `5px solid ${BLUE}` : "5px solid transparent", opacity: t >= beats.cart && !win ? 0.35 : 1, transform: `scale(${win ? 1 + 0.06 * cart : 1})` }}>
                    {productImg ? <Img src={staticFile(productImg)} style={{ width: "100%", height: "100%", objectFit: "contain", padding: 10, boxSizing: "border-box" }} />
                      : <div style={{ textAlign: "center", paddingTop: 22 }}><div style={{ fontSize: 96 }}>🍚</div><div style={{ fontSize: 32, fontWeight: 900, color: INK, marginTop: 4 }}>{product}</div></div>}
                    {seen && !win && t < beats.cart && <div style={{ position: "absolute", inset: 0, background: "rgba(59,91,253,0.10)" }} />}
                    {win && <div style={{ position: "absolute", left: 0, right: 0, bottom: 0, background: BLUE, color: "#fff", fontSize: 26, fontWeight: 900, textAlign: "center", padding: "6px 0" }}>최저가</div>}
                  </div>
                );
              })}
            </div>
            {t >= beats.cart && (
              <div style={{ display: "flex", alignItems: "center", gap: 16, marginTop: 20, fontSize: 38, fontWeight: 900, color: INK, opacity: cart }}>
                <span style={{ fontSize: 46, transform: `scale(${cart})`, display: "inline-block" }}>🛒</span>
                장바구니에 담았어요
                <span style={{ marginLeft: "auto", width: 52, height: 52, borderRadius: 26, background: GREEN, color: "#fff", fontSize: 34, display: "flex", alignItems: "center", justifyContent: "center" }}>✓</span>
              </div>
            )}
          </div>
        )}
      </div>
 {/* 결제 승인 요청 팝업 */}
      {t >= beats.approve && (
        <div style={{ position: "absolute", left: 130, right: 130, top: 640, ...card, padding: "30px 36px", boxShadow: "0 30px 70px rgba(20,30,60,0.28)",
          opacity: appr, transform: `translateY(${(1 - appr) * 60}px) scale(${0.9 + 0.1 * appr})` }}>
          <div style={{ fontSize: 30, fontWeight: 800, color: SUB }}>🔔 내 AI 비서</div>
          <div style={{ fontSize: 44, fontWeight: 900, color: INK, marginTop: 10, lineHeight: 1.3 }}>결제해 드릴까요?</div>
          <div style={{ display: "flex", gap: 16, marginTop: 22 }}>
            <div style={{ flex: 1, height: 76, borderRadius: 38, background: "#EEF0F3", fontSize: 32, fontWeight: 800, color: SUB, display: "flex", alignItems: "center", justifyContent: "center" }}>나중에</div>
            <div style={{ flex: 1.4, height: 76, borderRadius: 38, background: BLUE, fontSize: 34, fontWeight: 900, color: "#fff", display: "flex", alignItems: "center", justifyContent: "center",
              transform: `scale(${1 + 0.04 * Math.sin(Math.max(0, t - beats.approve) * 6)})` }}>결제 승인</div>
          </div>
        </div>
      )}
      {pip && <PersonPip pip={pip} enter={pipIn ? enter : 1} vidTop={-180} />}
    </AbsoluteFill>
  );
};

// ───────────────────────── ③ 먼저 말 거는 AI
// 잠금화면 알림이 먼저 도착 → (어도비 해지 완료 메일) → AI가 메일함을 훑음 → 실제 메시지(사용자 캡처 문구) → 아낀 돈
export const ProactiveScene: React.FC<{
  time: string; date: string; notifTitle: string; notifBody: string;
  mails: { from: string; subject: string; hit?: boolean }[]; message: string[]; saved: number; savedLabel: string;
  beats: { notif: number; mail: number; scan: number; msg: number; saved: number }; pip?: string; pipIn?: boolean; checking?: string;
}> = ({ time, date, notifTitle, notifBody, mails, message, saved, savedLabel, beats, pip, pipIn = true, checking }) => {
  const { t, sp, lin } = useT();
  const enter = sp(0, { damping: 22, stiffness: 300 });
  const notif = sp(beats.notif, { damping: 14, stiffness: 200 });
  const mail = sp(beats.mail);
  const msg = sp(beats.msg);
  const sv = sp(beats.saved, { damping: 11, stiffness: 180 });
  const scan = lin(beats.scan, beats.msg - 0.1);
  const hitIdx = mails.findIndex((m) => m.hit);
  const num = saved * lin(beats.saved + 0.05, beats.saved + 0.5);
  return (
    <AbsoluteFill style={{ background: BG, fontFamily: FONT }}>
 {/* 잠금화면 + 알림 */}
      <div style={{ position: "absolute", left: 110, right: 110, top: 250, height: 790, borderRadius: 56, background: "linear-gradient(160deg,#2A3566,#151B33 60%,#0E1222)",
        boxShadow: "0 24px 60px rgba(10,20,50,0.35)", overflow: "hidden", opacity: enter, transform: `translateY(${(1 - enter) * 60}px)`, ...(mail > 0 ? backStyle(mail * 0.7) : {}) }}>
        <div style={{ textAlign: "center", color: "#fff", marginTop: 60 }}>
          <div style={{ fontSize: 32, fontWeight: 700, opacity: 0.8 }}>{date}</div>
          <div style={{ fontSize: 150, fontWeight: 800, letterSpacing: -4, lineHeight: 1.05 }}>{time}</div>
        </div>
        {checking && t < beats.notif && (
          <div style={{ position: "absolute", left: 0, right: 0, top: 420, textAlign: "center", opacity: sp(0.3) }}>
            <span style={{ fontSize: 38, fontWeight: 800, color: "#fff", background: "rgba(255,255,255,0.16)", padding: "16px 30px", borderRadius: 40 }}>
              ✦ {checking}{".".repeat(1 + (Math.floor(t * 3) % 3))}</span>
          </div>
        )}
        {t >= beats.notif && (
          <div style={{ position: "absolute", left: 30, right: 30, top: 330, borderRadius: 34, background: "rgba(255,255,255,0.92)", padding: "24px 28px",
            opacity: notif, transform: `translateY(${(1 - notif) * -120}px) scale(${0.92 + 0.08 * notif})` }}>
            <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
              <div style={{ width: 48, height: 48, borderRadius: 14, background: `linear-gradient(135deg,#7C9BFF,${BLUE})`, color: "#fff", fontSize: 26, display: "flex", alignItems: "center", justifyContent: "center" }}>✦</div>
              <div style={{ fontSize: 32, fontWeight: 900, color: INK }}>{notifTitle}</div>
              <div style={{ marginLeft: "auto", fontSize: 24, fontWeight: 700, color: SUB }}>지금</div>
            </div>
            <div style={{ fontSize: 42, fontWeight: 800, color: INK, marginTop: 12, lineHeight: 1.35, wordBreak: "keep-all" }}>{notifBody}</div>
          </div>
        )}
      </div>
 {/* 메일함을 훑는 AI */}
      {t >= beats.mail && (
        <div style={{ position: "absolute", left: 70, right: 70, top: 280, height: 740, ...card, padding: 34, overflow: "hidden",
          opacity: mail, transform: `translateY(${(1 - mail) * 80}px) scale(${1 + 0.04 * lin(beats.mail, beats.msg)})`, ...(msg > 0 ? backStyle(msg * 0.75) : {}) }}>
          <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
            <div style={{ fontSize: 44 }}>✉️</div>
            <div style={{ fontSize: 38, fontWeight: 900, color: INK }}>Gmail</div>
            {t >= beats.scan && <div style={{ marginLeft: "auto", fontSize: 28, fontWeight: 800, color: BLUE, background: "#EEF1FF", padding: "8px 18px", borderRadius: 20 }}>✦ AI가 혼자 확인 중</div>}
          </div>
          <div style={{ position: "relative", marginTop: 24 }}>
            {mails.map((m, i) => {
              const p = sp(beats.mail + 0.35 * i);
              const passed = scan * mails.length > i;
              const hit = m.hit && passed;
              return (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 18, height: 104, borderBottom: `2px solid ${LINE}`, padding: "0 14px", opacity: p,
                  background: hit ? "rgba(236,29,29,0.08)" : "transparent", borderRadius: hit ? 18 : 0, outline: hit ? `4px solid ${RED}` : "none" }}>
                  <div style={{ width: 60, height: 60, borderRadius: 30, background: m.from ? "#FA0F00" : "#D5D8DE", color: "#fff", fontSize: 26, fontWeight: 900, display: "flex", alignItems: "center", justifyContent: "center" }}>{m.from.slice(0, 1)}</div>
 {/* 다른 메일은 내용을 지어내지 않고 흐린 줄로 */}
                  {!m.from ? <div style={{ flex: 1 }}><div style={{ width: 220, height: 24, borderRadius: 12, background: "#C9CED6", filter: "blur(3px)" }} /><div style={{ width: 460, height: 24, borderRadius: 12, background: "#DDE0E5", filter: "blur(3px)", marginTop: 14 }} /></div> :
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontSize: 34, fontWeight: 800, color: INK }}>{m.from}</div>
                    <div style={{ fontSize: m.hit ? 44 : 38, fontWeight: m.hit ? 900 : 700, color: m.hit ? INK : SUB, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{m.subject}</div>
                  </div>}
                  {passed && <div style={{ fontSize: 36, fontWeight: 900, color: hit ? RED : GREEN }}>{hit ? "!" : "✓"}</div>}
                </div>
              );
            })}
            {t >= beats.scan && t < beats.msg && (
              <div style={{ position: "absolute", left: -34, right: -34, top: scan * mails.length * 124 - 4, height: 4, background: BLUE, boxShadow: `0 0 18px ${BLUE}` }} />
            )}
          </div>
          {hitIdx >= 0 && scan * mails.length > hitIdx && (
            <div style={{ marginTop: 22, fontSize: 46, fontWeight: 900, color: RED, opacity: lin(beats.scan + 0.2, beats.scan + 0.5) }}>⚠ Adobe Stock은 아직 해지 안 됨</div>
          )}
        </div>
      )}
 {/* 실제로 받은 메시지 (사용자 캡처 문구를 줄였다 — 숫자·상품명은 원문 그대로) */}
      {t >= beats.msg && (
        <div style={{ position: "absolute", left: 70, right: 70, top: 300, ...card, padding: "30px 34px", opacity: msg, transform: `translateY(${(1 - msg) * 70 - sv * 70}px) scale(${(0.94 + 0.06 * msg) * (1 - 0.06 * sv)})` }}>
          <AgentHead sub="먼저 보낸 메시지" />
          <div style={{ marginTop: 22, background: "#F2F3F5", borderRadius: 30, borderTopLeftRadius: 8, padding: "24px 28px", display: "flex", flexDirection: "column", gap: 14 }}>
            {message.map((m, i) => (
              <div key={i} style={{ fontSize: i === 0 ? 46 : 40, fontWeight: i === 0 ? 900 : 700, color: INK, lineHeight: 1.4, wordBreak: "keep-all", opacity: sp(beats.msg + 0.2 + i * 0.35) }}
                dangerouslySetInnerHTML={{ __html: m.replace(/\*\*(.+?)\*\*/g, `<b style="color:${RED}">$1</b>`) }} />
            ))}
          </div>
        </div>
      )}
 {/* 아낀 돈 */}
      {t >= beats.saved && (
        <div style={{ position: "absolute", left: 0, right: 0, top: 640, textAlign: "center", opacity: sv, transform: `scale(${0.6 + 0.4 * sv})` }}>
          <div style={{ display: "inline-block", width: 880, boxSizing: "border-box", ...card, borderRadius: 44, padding: "26px 40px", boxShadow: "0 24px 60px rgba(18,183,106,0.35)", border: `5px solid ${GREEN}` }}>
            <div style={{ fontSize: 40, fontWeight: 900, color: INK }}>{savedLabel}</div>
            <div style={{ fontSize: 170, fontWeight: 900, color: GREEN, lineHeight: 1.05, fontVariantNumeric: "tabular-nums" }}>+${num.toFixed(2)}</div>
          </div>
        </div>
      )}
      {pip && <PersonPip pip={pip} enter={pipIn ? enter : 1} vidTop={-180} />}
    </AbsoluteFill>
  );
};

// ───────────────────────── ④ 해외에서 쏟아지는 AI 비서 / ⑥ 한국에선 아직
// 로고 카드 3장이 차례로 톡톡. locked=true면 그 위에 "한국 ✕" 도장
export const AgentLogos: React.FC<{
  title: string; agents: { name: string; maker: string; img: string; at: number }[]; locked?: { at: number; text: string }; pip?: string; pipIn?: boolean;
}> = ({ title, agents, locked, pip, pipIn = true }) => {
  const { t, sp } = useT();
  const enter = sp(0, { damping: 22, stiffness: 300 });
  const lk = locked ? sp(locked.at, { damping: 10, stiffness: 220 }) : 0;
  return (
    <AbsoluteFill style={{ background: BG, fontFamily: FONT }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 290, textAlign: "center", fontSize: 62, fontWeight: 900, color: INK, opacity: pipIn ? enter : 1, transform: `translateY(${(1 - enter) * 30}px)` }}>{title}</div>
      <div style={{ position: "absolute", left: 50, right: 50, top: 430, display: "flex", gap: 26, justifyContent: "center" }}>
        {agents.map((a, i) => {
          const p = sp(a.at, { damping: 12, stiffness: 200 });
          const bob = Math.sin((t - a.at) * 2.4 + i) * 6;
          return (
            <div key={a.name} style={{ width: 300, height: 470, ...card, padding: "28px 20px", textAlign: "center", opacity: p,
              transform: `translateY(${(1 - p) * 120 + (p > 0.99 ? bob : 0)}px) scale(${0.7 + 0.3 * p})`, filter: lk > 0 ? `grayscale(${lk})` : undefined }}>
              <div style={{ width: 230, height: 230, borderRadius: 40, overflow: "hidden", margin: "0 auto", background: "#F6F7F9" }}>
                <Img src={staticFile(a.img)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
              </div>
              <div style={{ fontSize: 56, fontWeight: 900, color: INK, marginTop: 26 }}>{a.name}</div>
              <div style={{ fontSize: 30, fontWeight: 800, color: SUB, marginTop: 6 }}>{a.maker}</div>
            </div>
          );
        })}
      </div>
      {locked && t >= locked.at && (
        <div style={{ position: "absolute", left: 0, right: 0, top: 560, textAlign: "center", opacity: lk, transform: `scale(${2 - lk})` }}>
          <div style={{ display: "inline-block", fontSize: 76, fontWeight: 900, color: RED, border: `10px solid ${RED}`, borderRadius: 28, padding: "10px 40px", background: "rgba(255,255,255,0.9)" }}>{locked.text}</div>
        </div>
      )}
      {pip && <PersonPip pip={pip} enter={pipIn ? enter : 1} vidTop={-180} />}
    </AbsoluteFill>
  );
};

// ───────────────────────── ⑤ 비서 → 직원 (사원증이 뒤집히며 바뀐다)
export const EmployeeScene: React.FC<{ from: string; to: string; flipAt: number; sub: string; pip?: string; pipIn?: boolean }> = ({ from, to, flipAt, sub, pip, pipIn = true }) => {
  const { t, sp } = useT();
  const enter = sp(0, { damping: 18, stiffness: 220 });
  const flip = sp(flipAt, { damping: 16, stiffness: 140 });
  const angle = flip * 180;
  const face = angle < 90;
  return (
    <AbsoluteFill style={{ background: BG, fontFamily: FONT }}>
      <div style={{ position: "absolute", left: 0, right: 0, top: 260, display: "flex", justifyContent: "center", opacity: enter, transform: `translateY(${(1 - enter) * 80}px)` }}>
        <div style={{ width: 10, height: 120, background: "#9AA0A6", position: "absolute", top: 0 }} />
        <div style={{ marginTop: 100, width: 560, height: 680, ...card, borderRadius: 44, transformOrigin: "50% -100px", transform: `rotate(${Math.sin(t * 2.2) * 2.5}deg) perspective(1400px) rotateY(${face ? angle : angle - 180}deg)`, textAlign: "center", padding: 40, boxSizing: "border-box",
          border: `6px solid ${face ? LINE : BLUE}` }}>
          <div style={{ fontSize: 30, fontWeight: 800, color: face ? SUB : BLUE, letterSpacing: 4 }}>{face ? "ASSISTANT" : "EMPLOYEE"}</div>
          <div style={{ width: 230, height: 230, borderRadius: 115, margin: "30px auto", background: face ? "#EEF1FF" : BLUE, color: face ? BLUE : "#fff", fontSize: 130, display: "flex", alignItems: "center", justifyContent: "center" }}>🤖</div>
          <div style={{ fontSize: 96, fontWeight: 900, color: face ? INK : BLUE }}>AI {face ? from : to}</div>
          {!face && <div style={{ fontSize: 46, fontWeight: 900, color: INK, marginTop: 18, opacity: sp(flipAt + 0.35) }}>{sub}</div>}
        </div>
      </div>
      {pip && <PersonPip pip={pip} enter={pipIn ? enter : 1} vidTop={-180} />}
    </AbsoluteFill>
  );
};
