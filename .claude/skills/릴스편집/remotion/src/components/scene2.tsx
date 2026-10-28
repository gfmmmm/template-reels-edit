// 결과 화면 모션그래픽 2 (기울기 없음, 덩어리 1~2장, 사람 말 문구, 실제 데이터, 근거가 보이게, "우와" 포인트를 크게).
// 글은 화면 기록(9/17 14:08 danmartell 분석, 14:13·15:10 공구 퍼널 스크린샷, 15:32 벤치마킹 릴스 결과)의 실제 내용을 쉬운 말로 옮긴 것.
import React from "react";
import { AbsoluteFill, Img, OffthreadVideo, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { PersonPip } from "./scene";

const BG = "#F3F4F6";
const INK = "#16181D";
const SUB = "#6B7280";
const BLUE = "#2F55D4";
const GREEN = "#1F8A4C";
const SANS = "'Apple SD Gothic Neo', Pretendard, sans-serif";
const EMOJI = "'Apple Color Emoji'";
const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };
const card: React.CSSProperties = { background: "#fff", borderRadius: 30, boxShadow: "0 30px 70px rgba(15,25,50,0.14), 0 4px 14px rgba(15,25,50,0.07)" };

const useT = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = f / fps;
  const ease = (a: number, d = 0.3) => { const v = interpolate(t, [a, a + d], [0, 1], clamp); return v * v * (3 - 2 * v); };
  const sp = (a: number) => (t < a ? 0 : spring({ frame: f - a * fps, fps, config: { damping: 16, stiffness: 160 } }));
  return { f, fps, t, ease, sp };
};

// 한 장 → 다음 장: 앞 장은 위로 물러나 흐려지고 다음 장이 아래에서 올라온다(기울기 없음)
const Page: React.FC<{ t: number; from: number; to: number; children: React.ReactNode }> = ({ t, from, to, children }) => {
  if (t < from - 0.01 || t > to + 0.3) return null;
  const i = interpolate(t, [from, from + 0.25], [0, 1], clamp);
  const o = interpolate(t, [to, to + 0.25], [0, 1], clamp);
  return <div style={{ position: "absolute", inset: 0, opacity: i * (1 - o), transform: `translateY(${(1 - i) * 50 - o * 50}px) scale(${1 - 0.04 * o})`, filter: `blur(${o * 4}px)` }}>{children}</div>;
};

const Big: React.FC<{ children: React.ReactNode; size?: number; color?: string }> = ({ children, size = 64, color = INK }) => (
  <div style={{ fontSize: size, fontWeight: 900, color, letterSpacing: -1.5, lineHeight: 1.2 }}>{children}</div>
);
const Hl: React.FC<{ p: number; children: React.ReactNode; c?: string }> = ({ p, children, c = "rgba(255,212,0,0.6)" }) => (
  <span style={{ backgroundImage: `linear-gradient(${c},${c})`, backgroundRepeat: "no-repeat", backgroundSize: `${p * 100}% 40%`, backgroundPosition: "0 92%" }}>{children}</span>
);

/**
 * 다른 계정이 돈 버는 구조 — 우와 포인트: "팔로워 307만인데 링크 하나 없이, 댓글 한 단어로 수백만 원 결제까지".
 * 1장(전략): 프로필 + 큰 가격 카드 3장 / 2장(어떻게): 댓글→DM→전화→결제 흐름 + 댓글 반응 8배 근거
 */
type RevenueContent = {
  profile: { img: string; handle: string; followers: string; role: string };
  offers: { pre: string; hl: string; items: [string, string, string][] };          // [이모지, 상품, 값]
  how: { line1: string; hl: string; flow: [string, string][];                      // [이모지, 단계] 마지막 단계가 초록
         bars: [string, number][]; big: string };                                   // [이름, 값(%)] 둘째 막대가 강조, big = 가장 큰 결론
};
export const RevenueScene: React.FC<{ beats: Record<string, number>; pip?: string; content: RevenueContent }> = ({ beats: b, pip, content: C }) => {
  const { t, ease, sp } = useT();
  const inn = sp(0);
  const prices = C.offers.items;
  const flow = C.how.flow;
  return (
    <AbsoluteFill style={{ background: BG, fontFamily: SANS }}>
      <div style={{ position: "absolute", left: 50, right: 50, top: 225, height: 840, ...card, overflow: "hidden", opacity: inn, transform: `translateY(${(1 - inn) * 60}px)` }}>
 {/* 머리: 프로필 (두 장 모두 고정) */}
        <div style={{ display: "flex", alignItems: "center", gap: 22, padding: "30px 44px 0" }}>
          <div style={{ width: 112, height: 112, borderRadius: 56, padding: 4, background: "linear-gradient(45deg,#FEDA75,#FA7E1E,#D62976,#962FBF)" }}>
            <Img src={staticFile(C.profile.img)} style={{ width: 104, height: 104, borderRadius: 52, objectFit: "cover", border: "3px solid #fff" }} />
          </div>
          <div>
            <div style={{ fontSize: 40, fontWeight: 900, color: INK }}>{C.profile.handle}</div>
            <div style={{ fontSize: 28, fontWeight: 800, color: SUB, marginTop: 4 }}>팔로워 <b style={{ color: INK }}>{C.profile.followers}</b> · {C.profile.role}</div>
          </div>
        </div>
        <div style={{ position: "relative", height: 700 }}>
          <Page t={t} from={0} to={b.how}>
            <div style={{ padding: "26px 44px" }}>
              <Big size={58}>{C.offers.pre} <Hl p={ease(b.strategy, 0.45)}>{C.offers.hl}</Hl></Big>
              <div style={{ display: "flex", flexDirection: "column", gap: 20, marginTop: 30 }}>
                {prices.map(([e, a, c], i) => {
                  const r = sp(0.25 + i * 0.15);
                  return (
                    <div key={a} style={{ display: "flex", alignItems: "center", gap: 22, background: "#F6F8FC", borderRadius: 26, padding: "34px 30px",
                      opacity: Math.min(1, r * 1.4), transform: `translateY(${(1 - r) * 30}px)` }}>
                      <div style={{ fontFamily: EMOJI, fontSize: 60 }}>{e}</div>
                      <div style={{ flex: 1, fontSize: 36, fontWeight: 800, color: INK }}>{a}</div>
                      <div style={{ fontSize: 56, fontWeight: 900, color: BLUE }}>{c}</div>
                    </div>
                  );
                })}
              </div>
            </div>
          </Page>
          <Page t={t} from={b.how} to={99}>
            <div style={{ padding: "26px 44px" }}>
              <Big size={56}>{C.how.line1}<br /><Hl p={ease(b.how + 0.25, 0.45)}>{C.how.hl}</Hl></Big>
 {/* 흐름: 큰 아이콘 4개가 차례로 이어진다 */}
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginTop: 34 }}>
                {flow.map(([e, x], i) => {
                  const r = sp(b.how + 0.1 + i * 0.12);
                  const last = i === flow.length - 1;
                  return (
                    <React.Fragment key={x}>
                      {i > 0 && <div style={{ flex: 1, height: 5, margin: "0 6px 46px", background: `linear-gradient(90deg, ${BLUE} ${r * 100}%, #DDE2EA ${r * 100}%)`, borderRadius: 3 }} />}
                      <div style={{ textAlign: "center", opacity: Math.min(1, r * 1.4), transform: `scale(${0.7 + 0.3 * r})` }}>
                        <div style={{ width: 132, height: 132, borderRadius: 66, background: last ? "#E7F5EC" : "#EEF3FF", display: "flex", alignItems: "center", justifyContent: "center",
                          fontFamily: EMOJI, fontSize: 64, boxShadow: last ? `0 0 0 5px ${GREEN}` : "none" }}>{e}</div>
                        <div style={{ fontSize: 28, fontWeight: 900, color: last ? GREEN : INK, marginTop: 12, whiteSpace: "nowrap" }}>{x}</div>
                      </div>
                    </React.Fragment>
                  );
                })}
              </div>
 {/* 근거: 실제 숫자 — 틀은 처음부터, 막대는 "돈 벌고" 뒤에 차오르고 "반응 8배"를 가장 크게 */}
              <div style={{ marginTop: 36, background: "#F6F8FC", borderRadius: 24, padding: "22px 30px" }}>
                {C.how.bars.map(([l, v], i) => { const c = i === C.how.bars.length - 1 ? BLUE : "#B5BAC2"; const mx = Math.max(...C.how.bars.map((x) => x[1]));
                  const p = ease(b.how + 0.7 + i * 0.25, 0.4);
                  return (
                    <div key={l as string} style={{ display: "flex", alignItems: "center", gap: 16, marginTop: i ? 14 : 0 }}>
                      <div style={{ width: 270, fontSize: 28, fontWeight: 800, color: INK }}>{l}</div>
                      <div style={{ flex: 1, height: 36, background: "#E8EBF2", borderRadius: 18 }}>
                        <div style={{ width: `${((v as number) / mx) * 100 * p}%`, minWidth: 36 * p, height: 36, background: c as string, borderRadius: 18 }} />
                      </div>
                      <div style={{ width: 120, fontSize: 36, fontWeight: 900, color: c as string, textAlign: "right" }}>{((v as number) * p).toFixed(1)}%</div>
                    </div>
                  );
                })}
                <div style={{ textAlign: "center", fontSize: 96, fontWeight: 900, color: BLUE, marginTop: 10, letterSpacing: -2,
                  opacity: ease(b.how + 1.15, 0.2), transform: `scale(${0.7 + 0.3 * sp(b.how + 1.15)})` }}>{C.how.big}</div>
              </div>
            </div>
          </Page>
        </div>
      </div>
      {pip && <PersonPip pip={pip} enter={1} />}
    </AbsoluteFill>
  );
};

/**
 * 공구 계정 판매 전략 — 우와 포인트: "휴지통 하나로 3차 공구까지 완판". 실제 스크린샷 내용.
 * 1장(특히 공구 계정을 넣으면): 살림 꿀팁 공구 계정 + 릴스 조회수 / 2장(판매 전략): 큰 흐름 + 진짜 자산 + 결과
 */
type FlowContent = {
  intro: { emoji: string; pre: string; hl: string; statLabel: string; stat: string; caption: string };
  title: string; steps: [string, string, string][]; keyIndex: number;   // steps: [이모지, 단계, 작은 설명], keyIndex 단계를 파랑으로 강조
  result: { small: string; big: string };
};
export const FlowScene: React.FC<{ beats: Record<string, number>; pip?: string; content: FlowContent }> = ({ beats: b, pip, content: C }) => {
  const { t, ease, sp } = useT();
  const inn = sp(0);
  const steps = C.steps;
  return (
    <AbsoluteFill style={{ background: BG, fontFamily: SANS }}>
      <div style={{ position: "absolute", left: 50, right: 50, top: 225, height: 840, ...card, overflow: "hidden", opacity: inn, transform: `translateY(${(1 - inn) * 60}px)` }}>
        <Page t={t} from={0} to={b.strategy}>
          <div style={{ height: "100%", padding: "50px 50px", boxSizing: "border-box", display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", textAlign: "center" }}>
            <div style={{ fontFamily: EMOJI, fontSize: 210, lineHeight: 1, transform: `scale(${0.8 + 0.2 * sp(0.1)})` }}>{C.intro.emoji}</div>
            <Big size={76}>{C.intro.pre} <Hl p={ease(0.3, 0.4)}>{C.intro.hl}</Hl></Big>
            <div style={{ marginTop: 34, background: "#F6F8FC", borderRadius: 26, padding: "24px 40px", opacity: ease(0.5, 0.3) }}>
              <div style={{ fontSize: 30, fontWeight: 800, color: SUB }}>{C.intro.statLabel}</div>
              <div style={{ fontSize: 100, fontWeight: 900, color: BLUE, letterSpacing: -2, lineHeight: 1.1 }}>{C.intro.stat}</div>
            </div>
            <div style={{ fontSize: 36, fontWeight: 800, color: INK, marginTop: 30 }}>{C.intro.caption}</div>
          </div>
        </Page>
        <Page t={t} from={b.strategy} to={99}>
          <div style={{ padding: "34px 44px" }}>
            <Big size={54}>{C.title}</Big>
            <div style={{ marginTop: 18, display: "flex", flexDirection: "column", gap: 0 }}>
              {steps.map(([e, a, c], i) => {
                const r = sp(b.strategy + 0.1 + i * 0.18);
                const key = i === C.keyIndex;
                return (
                  <React.Fragment key={a}>
                    {i > 0 && <div style={{ marginLeft: 52, height: 22, width: 5, background: r > 0.1 ? BLUE : "#DDE2EA", borderRadius: 3 }} />}
                    <div style={{ display: "flex", alignItems: "center", gap: 22, background: key ? BLUE : "#F6F8FC", borderRadius: 22, padding: "18px 26px",
                      opacity: Math.min(1, r * 1.4), transform: `translateX(${(1 - r) * 40}px)`, boxShadow: key ? "0 12px 30px rgba(47,85,212,0.3)" : "none" }}>
                      <div style={{ fontFamily: EMOJI, fontSize: 52 }}>{e}</div>
                      <div style={{ flex: 1 }}>
                        <div style={{ fontSize: 36, fontWeight: 900, color: key ? "#fff" : INK }}>{a}</div>
                        <div style={{ fontSize: 26, fontWeight: 800, color: key ? "#DCE5FF" : BLUE, marginTop: 2 }}>{c}</div>
                      </div>
                    </div>
                  </React.Fragment>
                );
              })}
            </div>
 {/* 결과: 우와 포인트 — 가장 크게, 일찍 */}
            <div style={{ marginTop: 22, background: "#E7F5EC", borderRadius: 24, padding: "18px 26px", textAlign: "center",
              opacity: ease(b.strategy + 0.9, 0.25), transform: `scale(${0.8 + 0.2 * sp(b.strategy + 0.9)})` }}>
              <div style={{ fontSize: 34, fontWeight: 800, color: GREEN }}>{C.result.small}</div>
              <div style={{ fontSize: 70, fontWeight: 900, color: INK, letterSpacing: -2, lineHeight: 1.15 }}>{C.result.big}</div>
            </div>
          </div>
        </Page>
      </div>
      {pip && <PersonPip pip={pip} enter={1} />}
    </AbsoluteFill>
  );
};

/** 릴스 탭을 스크롤하며 터진 릴스를 찾는다 → 찾은 결과. 인물 창 없음(노트북 보며 읽는 테이크) → 화면을 넓게 쓴다 */
type HuntContent = { searching: string; count: number; unit: string; resultPre: string; resultPost: string;
  found: [string, string, string][] };   // [썸네일 경로, 제목, 조회수]
export const ReelsHuntScene: React.FC<{ beats: Record<string, number>; pip?: string; video: string; content: HuntContent }> = ({ beats: b, video, content: C }) => {
  const { t, sp } = useT();
  const inn = sp(0);
  const res = t < b.found ? 0 : spring({ frame: (t - b.found) * 30, fps: 30, config: { damping: 20, stiffness: 260 } });
  const n = Math.round(interpolate(t, [0.3, b.found], [0, C.count], clamp));
  const found = C.found;
  return (
    <AbsoluteFill style={{ background: BG, fontFamily: SANS }}>
 {/* 1. 큰 휴대폰: 실제 릴스 탭 스크롤 기록 + 찾은 개수 */}
      {t < b.found + 0.4 && (
        <div style={{ position: "absolute", left: 0, right: 0, top: 230, display: "flex", justifyContent: "center", opacity: inn * (1 - res), transform: `translateY(${(1 - inn) * 60}px) scale(${1 - 0.06 * res})` }}>
          <div style={{ position: "relative" }}>
            <div style={{ width: 690, height: 1260, borderRadius: 76, background: "#111", padding: 14, boxShadow: "0 30px 70px rgba(15,25,50,0.25)" }}>
              <div style={{ width: "100%", height: "100%", borderRadius: 60, overflow: "hidden", position: "relative" }}>
                <OffthreadVideo src={staticFile(video)} muted style={{ position: "absolute", width: "100%", top: -30 }} />
              </div>
            </div>
            <div style={{ position: "absolute", left: -150, top: 60, ...card, borderRadius: 30, padding: "24px 34px", textAlign: "center" }}>
              <div style={{ fontSize: 28, fontWeight: 800, color: SUB }}>🔍 {C.searching}</div>
              <div style={{ fontSize: 110, fontWeight: 900, color: BLUE, lineHeight: 1.05, letterSpacing: -2 }}>{n}<span style={{ fontSize: 52, color: INK }}>{C.unit}</span></div>
            </div>
          </div>
        </div>
      )}
 {/* 2. 찾은 결과: 자막·오른쪽 버튼 자리 위(y 1050)에서 끝나게 */}
      {t >= b.found && (
        <div style={{ position: "absolute", left: 40, right: 40, top: 230, height: 820, ...card, opacity: res, transform: `translateY(${(1 - res) * 60}px)` }}>
          <div style={{ padding: "34px 40px" }}>
            <Big size={60}>{C.resultPre} <span style={{ color: BLUE }}>{C.count}{C.unit}</span> {C.resultPost}</Big>
            {found.map(([src, title, views], i) => {
              const r = sp(b.found + 0.1 + i * 0.12);
              return (
                <div key={i} style={{ display: "flex", gap: 22, alignItems: "center", marginTop: 24, opacity: Math.min(1, r * 1.4), transform: `translateY(${(1 - r) * 30}px)` }}>
                  <Img src={staticFile(src)} style={{ width: 330, height: 190, borderRadius: 20, objectFit: "cover", flexShrink: 0 }} />
                  <div>
                    <div style={{ fontSize: 50, fontWeight: 900, color: GREEN, letterSpacing: -1 }}>▶ {views}</div>
                    <div style={{ fontSize: 26, fontWeight: 800, color: INK, marginTop: 6, lineHeight: 1.3 }}>{title}</div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};
