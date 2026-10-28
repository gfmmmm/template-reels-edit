// ChatGPT 맥 앱 장면 3종 (한 편집 사례)
// 틀은 scene.tsx와 같은 톤: 연한 회색 바탕 + 흰 둥근 카드 + 파랑 포인트, 기울기 없음, 타이핑 연출 없음.
// 화면은 사용자가 준 실제 앱 스크린샷(Chat/Work 전환, "준비되면 시작하세요.", 플러그인 목록)을 단순화해 다시 그린 것.
// 카드는 세로 330~1040px 안(자막 1,075~1,165px 자리를 비움), 아래는 인물 창(PersonPip).
// beats는 장면 시작부터의 초(말에 맞춘 시각). 영상마다 바뀌는 글은 props로.
import React from "react";
import { AbsoluteFill, OffthreadVideo, Sequence, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { PersonPip } from "./scene";

const BG = "#F3F4F6";
const BLUE = "#3B5BFD";
const INK = "#1F2329";
const SUB = "#9AA0A6";
const LINE = "#E6E8EC";
const FONT = "'Apple SD Gothic Neo', Pretendard, sans-serif";
const card: React.CSSProperties = {
  background: "#fff", borderRadius: 36, boxShadow: "0 18px 50px rgba(20,30,60,0.10), 0 2px 8px rgba(20,30,60,0.06)",
};
const TOP = 260; // 위쪽 활용도 막대는 앱 장면에서 뺐다(사용자: 퍼센트를 말할 때만 PercentBar로)
const BOTTOM = 1040;

const useT = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const sp = (at: number, cfg = { damping: 20, stiffness: 170 }) => (f < at * fps ? 0 : spring({ frame: f - at * fps, fps, config: cfg }));
  const lin = (a: number, b: number) => interpolate(f / fps, [a, b], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return { f, fps, t: f / fps, sp, lin };
};

// 위쪽 "GPT 활용도" 막대 — 단계마다 40·60·80·100%
export const LevelBadge: React.FC<{ level: number; from?: number }> = ({ level, from = 0 }) => {
  const { sp, lin } = useT();
  const inn = sp(0);
  const fill = from + (level - from) * lin(0.15, 0.9);
  return (
    <div style={{ position: "absolute", left: 90, right: 90, top: 228, height: 86, display: "flex", alignItems: "center", gap: 22, opacity: inn }}>
      <div style={{ fontSize: 40, fontWeight: 900, color: INK, whiteSpace: "nowrap" }}>GPT 활용도</div>
      <div style={{ flex: 1, height: 30, borderRadius: 15, background: "#E3E6EC", overflow: "hidden" }}>
        <div style={{ width: `${fill}%`, height: "100%", borderRadius: 15, background: BLUE }} />
      </div>
      <div style={{ fontSize: 64, fontWeight: 900, color: BLUE, width: 180, textAlign: "right" }}>{Math.round(fill)}%</div>
    </div>
  );
};

const Cursor: React.FC<{ x: number; y: number; click?: number }> = ({ x, y, click = 0 }) => (
  <div style={{ position: "absolute", left: x, top: y, zIndex: 20 }}>
    {click > 0 && click < 1 && (
      <div style={{ position: "absolute", left: -40 * click, top: -40 * click, width: 80 * click, height: 80 * click, borderRadius: "50%",
        border: `5px solid ${BLUE}`, opacity: 1 - click }} />
    )}
    <svg width="44" height="54" viewBox="0 0 22 27" style={{ filter: "drop-shadow(0 3px 4px rgba(0,0,0,0.3))" }}>
      <path d="M2 2 L2 22 L7.5 17 L11 25 L14.5 23.5 L11 15.8 L18.5 15.5 Z" fill="#111" stroke="#fff" strokeWidth="1.6" strokeLinejoin="round" />
    </svg>
  </div>
);

// 맥 앱 창 틀: 신호등 + 왼쪽 아이콘 줄
const MacWindow: React.FC<{ style?: React.CSSProperties; children: React.ReactNode; sidebar?: boolean; title?: string }> = ({ style, children, sidebar = true, title }) => (
  <div style={{ position: "absolute", ...card, overflow: "hidden", ...style }}>
    <div style={{ height: 58, display: "flex", alignItems: "center", gap: 12, padding: "0 24px", background: "#F4F4F5", borderBottom: `1px solid ${LINE}` }}>
      {["#FF5F57", "#FEBC2E", "#28C840"].map((c) => <div key={c} style={{ width: 18, height: 18, borderRadius: 9, background: c }} />)}
      {title && <div style={{ flex: 1, textAlign: "center", fontSize: 22, fontWeight: 700, color: "#6B7078", marginRight: 70 }}>{title}</div>}
    </div>
    <div style={{ position: "absolute", top: 58, bottom: 0, left: 0, right: 0, display: "flex" }}>
      {sidebar && (
        <div style={{ width: 74, background: "#F4F4F5", display: "flex", flexDirection: "column", alignItems: "center", gap: 26, paddingTop: 22 }}>
          <div style={{ width: 44, height: 44, borderRadius: 12, background: "#E4E5E8", display: "flex", alignItems: "center", justifyContent: "center", fontSize: 24 }}>⌂</div>
          {[0, 1, 2, 3].map((i) => <div key={i} style={{ width: 28, height: 28, borderRadius: i === 1 ? 14 : 8, border: "3px solid #8A8F98" }} />)}
          <div style={{ position: "absolute", bottom: 20, width: 40, height: 40, borderRadius: 20, background: "#E07BB8", color: "#fff", fontSize: 16, fontWeight: 800,
            display: "flex", alignItems: "center", justifyContent: "center" }}>TJ</div>
        </div>
      )}
      <div style={{ position: "relative", flex: 1, background: "#fff" }}>{children}</div>
    </div>
  </div>
);

// Chat / Work 전환 버튼. work: 0(Chat) → 1(Work)
const ModeToggle: React.FC<{ work: number; top?: number }> = ({ work, top = 26 }) => (
  <div style={{ position: "absolute", top, left: "50%", marginLeft: -200, width: 400, height: 74, borderRadius: 37, background: "#EFF0F2" }}>
    <div style={{ position: "absolute", top: 4, left: 4 + work * 196, width: 196, height: 66, borderRadius: 33, background: "#fff", boxShadow: "0 2px 8px rgba(0,0,0,0.12)" }} />
    {["Chat", "Work"].map((m, i) => (
      <div key={m} style={{ position: "absolute", top: 0, left: 4 + i * 196, width: 196, height: 74, display: "flex", alignItems: "center", justifyContent: "center",
        fontSize: 33, fontWeight: 800, color: (i === 1 ? work > 0.5 : work <= 0.5) ? INK : "#6B7078" }}>{m}</div>
    ))}
  </div>
);

const InputBar: React.FC<{ text: string; style?: React.CSSProperties; work?: boolean }> = ({ text, style, work }) => (
  <div style={{ position: "absolute", left: 36, right: 36, height: work ? 150 : 84, borderRadius: work ? 30 : 42, border: `2px solid ${LINE}`, background: "#fff",
    boxShadow: "0 6px 20px rgba(20,30,60,0.06)", ...style }}>
    <div style={{ position: "absolute", left: work ? 28 : 74, top: work ? 22 : 0, height: work ? "auto" : 84, display: "flex", alignItems: "center", fontSize: 33, color: "#A4A9B1", fontWeight: 700 }}>{text}</div>
    <div style={{ position: "absolute", left: 20, bottom: work ? 16 : 14, width: 54, height: 54, borderRadius: 27, background: work ? "#F1F2F4" : "transparent",
      display: "flex", alignItems: "center", justifyContent: "center", fontSize: 40, fontWeight: 300, color: INK }}>+</div>
    <div style={{ position: "absolute", right: 14, bottom: work ? 16 : 14, width: 54, height: 54, borderRadius: 27, background: BLUE, display: "flex", alignItems: "center", justifyContent: "center", gap: 4 }}>
      {[14, 24, 18, 26, 12].map((h, i) => <div key={i} style={{ width: 4, height: h, borderRadius: 2, background: "#fff" }} />)}
    </div>
  </div>
);

// ChatGPT 앱 첫 화면 (사용자 스크린샷: Chat → "준비되면 시작하세요.", Work → "어떤 작업을 할까요?")
const AppHome: React.FC<{ work: number }> = ({ work }) => (
  <>
    <ModeToggle work={work} />
    <div style={{ position: "absolute", top: 200, left: 0, right: 0, textAlign: "center", fontSize: 56, fontWeight: 800, color: INK }}>
      {work > 0.5 ? "어떤 작업을 할까요?" : "준비되면 시작하세요."}
    </div>
    <InputBar text={work > 0.5 ? "ChatGPT로 Work 시작" : "ChatGPT에게 물어보세요"} style={{ top: 310 }} work={work > 0.5} />
  </>
);

const Label: React.FC<{ text: string; color: string; bg: string; style?: React.CSSProperties; pop?: number }> = ({ text, color, bg, style, pop = 1 }) => (
  <div style={{ position: "absolute", padding: "14px 30px", borderRadius: 34, background: bg, color, fontSize: 40, fontWeight: 900, whiteSpace: "nowrap",
    transform: `scale(${pop})`, opacity: Math.min(1, pop * 2), boxShadow: "0 6px 16px rgba(20,30,60,0.12)", zIndex: 10, ...style }}>{text}</div>
);

/** ① 웹사이트가 아니라 프로그램을 깔아서: 브라우저 창이 물러나고 맥 앱 창이 들어온다. beats.app = "프로그램을" */
export const GptAppScene: React.FC<{ beats: { app: number }; level?: number; pip?: string }> = ({ beats, level, pip }) => {
  const { sp } = useT();
  const enter = sp(0, { damping: 26, stiffness: 420 });
  const app = sp(beats.app, { damping: 18, stiffness: 150 });
  const x = sp(beats.app + 0.15, { damping: 12, stiffness: 220 });
  return (
    <AbsoluteFill style={{ background: BG, fontFamily: FONT }}>
      {level !== undefined && <LevelBadge level={level} from={level - 20} />}
 {/* 브라우저 */}
      <div style={{ position: "absolute", left: 70, right: 70, top: TOP + 10, height: 560, opacity: enter * (1 - 0.55 * app),
        transform: `translateY(${(1 - enter) * 60 - app * 30}px) scale(${1 - 0.12 * app})`, filter: `grayscale(${app}) blur(${app * 2.5}px)` }}>
        <MacWindow style={{ inset: 0 }} sidebar={false}>
          <div style={{ position: "absolute", top: 18, left: 30, right: 30, height: 58, borderRadius: 29, background: "#F1F2F4", display: "flex", alignItems: "center", padding: "0 26px",
            fontSize: 34, fontWeight: 800, color: "#5F6368" }}>🔒&nbsp;&nbsp;chatgpt.com</div>
          <div style={{ position: "absolute", top: 170, left: 0, right: 0, textAlign: "center", fontSize: 50, fontWeight: 800, color: INK }}>무엇을 도와드릴까요?</div>
          <InputBar text="무엇이든 물어보세요" style={{ top: 250, left: 80, right: 80 }} />
        </MacWindow>
        <Label text="웹사이트" color="#5F6368" bg="#fff" style={{ left: -10, top: -26 }} pop={enter} />
        {x > 0 && <div style={{ position: "absolute", left: "50%", top: "45%", marginLeft: -90, marginTop: -90, width: 180, height: 180, transform: `scale(${x})`,
          color: "#EC1D1D", fontSize: 200, fontWeight: 900, lineHeight: "180px", textAlign: "center" }}>✕</div>}
      </div>
 {/* 맥 앱 */}
      {app > 0 && (
        <div style={{ position: "absolute", left: 60, right: 60, top: TOP + 130, height: 580, opacity: app, transform: `translateY(${(1 - app) * 260}px) scale(${0.9 + 0.1 * app})` }}>
          <MacWindow style={{ inset: 0 }}>
            <AppHome work={0} />
          </MacWindow>
          <Label text="✓ PC 프로그램" color="#fff" bg={BLUE} style={{ right: -10, top: -28 }} pop={app} />
        </div>
      )}
      {pip && <PersonPip pip={pip} enter={enter} />}
    </AbsoluteFill>
  );
};

// 입력하는 말은 한 글자씩 타이핑되듯 나온다. typeAt: 타이핑 시작 초, cps: 1초 글자 수
const typed = (text: string, t: number, typeAt: number, cps = 22) => {
  const n = Math.max(0, Math.min(text.length, Math.floor((t - typeAt) * cps)));
  return { shown: text.slice(0, n), typing: n < text.length && t >= typeAt };
};
const Caret: React.FC<{ on: boolean }> = ({ on }) => {
  const f = useCurrentFrame();
  return on ? <span style={{ color: BLUE, opacity: Math.floor(f / 8) % 2 ? 0.2 : 1, marginLeft: 2 }}>|</span> : null;
};
const Bubble: React.FC<{ text: string; pop: number; size?: number; typeAt?: number }> = ({ text, pop, size = 40, typeAt }) => {
  const { t } = useT();
  const ty = typeAt === undefined ? { shown: text, typing: false } : typed(text, t, typeAt);
  return (
    <div style={{ alignSelf: "flex-end", background: "#EEF1FF", color: INK, fontSize: size, fontWeight: 800, padding: "14px 24px", borderRadius: 26, borderTopRightRadius: 8,
      opacity: pop, transform: `translateY(${(1 - pop) * 30}px)`, minHeight: size * 1.4 }}>{ty.shown}<Caret on={ty.typing} /></div>
  );
};

const PptIcon: React.FC<{ s?: number }> = ({ s = 70 }) => (
  <div style={{ width: s, height: s * 1.2, borderRadius: s * 0.14, background: "#D24726", color: "#fff", fontSize: s * 0.55, fontWeight: 900,
    display: "flex", alignItems: "center", justifyContent: "center" }}>P</div>
);

/**
 * ② 채팅모드 말고 워크모드: Chat→Work 전환 클릭 → 같은 부탁("PPT 만들어줘")을 두 모드에 나란히 →
 * Chat은 글로 된 기획만, Work는 기획·디자인·제작을 거쳐 완성된 PPT 파일.
 * beats: work(전환 클릭) ppt(부탁) chat(Chat 답변) plan("기획만") workres(Work 시작) file(완성 파일)
 * content: request, planTitle, planLines[], steps[], fileName
 */
export const ChatWorkScene: React.FC<{
  beats: { work: number; ppt: number; chat: number; plan: number; workres: number; file: number };
  content: { request: string; planTitle: string; planLines: string[]; steps: string[]; fileName: string };
  pip?: string;
}> = ({ beats: b, content: c, pip }) => {
  const { t, sp, lin } = useT();
  const enter = sp(0);
  const tog = sp(b.work, { damping: 18, stiffness: 200 });
  const click = lin(b.work - 0.02, b.work + 0.4);
  const cur = lin(0.15, b.work - 0.05);
  const split = sp(b.ppt, { damping: 20, stiffness: 150 });
  const req = sp(b.ppt + 0.3);
  const chatOn = sp(b.chat);
  const planStamp = sp(b.plan, { damping: 12, stiffness: 220 });
  const workOn = sp(b.workres);
  const file = sp(b.file, { damping: 13, stiffness: 170 });
 // 완성 파일이 나오면 Work 카드가 화면 전체로 커지고 Chat 카드는 빠진다(우와 포인트를 크게 — 검수 1차)
  const col = (left: number, active: number, dim: number, width = 466, gone = 0): React.CSSProperties => ({
    position: "absolute", top: 260, height: BOTTOM - 260, left, width, ...card, overflow: "hidden",
    opacity: split * (1 - 0.45 * dim) * (1 - gone), transform: `translateY(${(1 - split) * 120}px) scale(${1 - 0.05 * dim})`,
    filter: `grayscale(${dim})`, border: active ? `4px solid ${BLUE}` : "4px solid transparent", boxSizing: "border-box",
  });
  const head = (label: string, on: boolean) => (
    <div style={{ height: 76, display: "flex", alignItems: "center", justifyContent: "center", fontSize: 40, fontWeight: 900,
      color: on ? "#fff" : INK, background: on ? BLUE : "#EFF0F2" }}>{label}</div>
  );
  return (
    <AbsoluteFill style={{ background: BG, fontFamily: FONT }}>
 {/* 1. 앱에서 Chat → Work 전환 */}
      {split < 1 && (
        <div style={{ position: "absolute", left: 60, right: 60, top: TOP, height: 560, opacity: enter * (1 - split), transform: `translateY(${(1 - enter) * 60}px) scale(${1 - 0.15 * split})` }}>
          <MacWindow style={{ inset: 0 }}>
            <AppHome work={tog} />
          </MacWindow>
          <Cursor x={interpolate(cur, [0, 1], [560, 655])} y={interpolate(cur, [0, 1], [400, 110])} click={t >= b.work ? click : 0} />
        </div>
      )}
 {/* 2. 같은 부탁을 두 모드에 */}
      {split > 0 && (
        <>
          <div style={col(60, 0, workOn, 466, file)}>
            {head("Chat 모드", false)}
            <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 16 }}>
              <Bubble text={c.request} pop={req} typeAt={b.ppt + 0.25} />
              {chatOn > 0 && (
                <div style={{ opacity: chatOn }}>
                  <div style={{ fontSize: 40, fontWeight: 900, color: INK, marginBottom: 14 }}>{c.planTitle}</div>
                  {c.planLines.map((l, i) => {
                    const p = sp(b.chat + 0.25 + i * 0.3);
                    return <div key={i} style={{ fontSize: 38, fontWeight: 800, color: "#3A3F47", lineHeight: 1.65, opacity: p, transform: `translateX(${(1 - p) * 20}px)` }}>{l}</div>;
                  })}
                </div>
              )}
            </div>
            {planStamp > 0 && <Label text="📝 기획만 줘요" color={INK} bg="#FFE27A" style={{ left: 60, bottom: 36 }} pop={planStamp} />}
          </div>
          <div style={col(554 - 494 * file, workOn > 0.5 ? 1 : 0, 0, 466 + 494 * file)}>
            {head("Work 모드", workOn > 0.5)}
            <div style={{ padding: 24, display: "flex", flexDirection: "column", gap: 16 }}>
              <Bubble text={c.request} pop={req} typeAt={b.ppt + 0.25} />
              {workOn === 0 && req > 0.5 && <div style={{ fontSize: 26, color: SUB, fontWeight: 700 }}>…</div>}
              {workOn > 0 && file < 0.05 && c.steps.map((s, i) => {
                const at = b.workres + 0.35 + i * ((b.file - b.workres - 0.6) / c.steps.length);
                const done = t >= at + 0.4;
                const p = sp(at);
                return (
                  <div key={i} style={{ display: "flex", alignItems: "center", gap: 20, fontSize: 46, fontWeight: 900, color: done ? INK : SUB, marginTop: 14, opacity: p }}>
                    <div style={{ width: 60, height: 60, borderRadius: 30, background: done ? BLUE : "#E3E6EC", color: "#fff", fontSize: 26,
                      display: "flex", alignItems: "center", justifyContent: "center" }}>{done ? "✓" : ""}</div>
                    {s}
                  </div>
                );
              })}
              {file > 0 && (
                <div style={{ opacity: file, transform: `scale(${0.8 + 0.2 * file})`, transformOrigin: "50% 0%" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 26, padding: 22, borderRadius: 26, border: `3px solid ${LINE}` }}>
                    <PptIcon s={96} />
                    <div>
                      <div style={{ fontSize: 54, fontWeight: 900, color: INK }}>{c.fileName}</div>
                      <div style={{ fontSize: 32, fontWeight: 700, color: SUB, marginTop: 6 }}>PowerPoint 파일 · 바로 열기</div>
                    </div>
                  </div>
                  <div style={{ position: "relative", height: 330, marginTop: 26 }}>
                    {[0, 1, 2].map((i) => {
                      const p = sp(b.file + 0.2 + i * 0.15, { damping: 14, stiffness: 200 });
                      return (
                        <div key={i} style={{ position: "absolute", left: 20 + i * 250, top: 10 + i * 30, width: 380, height: 214, borderRadius: 16, background: "#fff",
                          border: `2px solid ${LINE}`, boxShadow: "0 8px 20px rgba(20,30,60,0.12)", overflow: "hidden", opacity: p, transform: `translateY(${(1 - p) * 40}px)` }}>
                          <div style={{ height: 44, background: "#D24726" }} />
                          <div style={{ margin: "16px 18px 0", height: 14, width: "70%", borderRadius: 7, background: "#3A3F47" }} />
                          <div style={{ margin: "12px 18px 0", height: 10, width: "85%", borderRadius: 5, background: "#D5D8DE" }} />
                          <div style={{ margin: "8px 18px 0", height: 10, width: "60%", borderRadius: 5, background: "#D5D8DE" }} />
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
            {file > 0 && <Label text="✓ 완성된 PPT 파일" color="#fff" bg={BLUE} style={{ left: "50%", bottom: 40, marginLeft: -230, fontSize: 52 }} pop={sp(b.file + 0.5, { damping: 12, stiffness: 220 })} />}
          </div>
        </>
      )}
      {pip && <PersonPip pip={pip} enter={enter} />}
    </AbsoluteFill>
  );
};

// 플러그인 아이콘 (단순화)
const PlugIcon: React.FC<{ kind: string; s?: number }> = ({ kind, s = 40 }) => {
  if (kind === "Google Calendar")
    return <div style={{ width: s, height: s, borderRadius: s * 0.18, background: "#fff", border: "3px solid #4285F4", color: "#4285F4", fontSize: s * 0.45, fontWeight: 900,
      display: "flex", alignItems: "center", justifyContent: "center", boxSizing: "border-box" }}>31</div>;
  if (kind === "Gmail")
    return <div style={{ width: s, height: s * 0.78, borderRadius: s * 0.12, background: "#fff", border: "3px solid #EA4335", color: "#EA4335", fontSize: s * 0.5, fontWeight: 900,
      display: "flex", alignItems: "center", justifyContent: "center", boxSizing: "border-box" }}>M</div>;
  if (kind === "Google Drive")
    return <svg width={s} height={s} viewBox="0 0 40 36"><path d="M13 2h14l13 22-7 12z" fill="#FBBC04" /><path d="M13 2 0 24l7 12L20 14z" fill="#0F9D58" /><path d="M7 36h26l7-12H14z" fill="#4285F4" /></svg>;
  return <div style={{ width: s, height: s, borderRadius: s / 2, background: "#1A73E8", color: "#fff", fontSize: s * 0.5, display: "flex", alignItems: "center", justifyContent: "center" }}>👤</div>;
};

/**
 * ③ 플러그인: Work 입력창 + 버튼 → 플러그인 목록(사용자 스크린샷 그대로) → 지메일·캘린더 연결 →
 * "나 내일 일정 어떻게 돼?" → 캘린더 확인 → 답(일정 내용은 흐리게 — 지어내지 않고 개인정보도 가린다).
 * beats: plus, gmail, cal, ask, check, answer
 */
export const PluginScene: React.FC<{
  beats: { plus: number; gmail: number; cal: number; ask: number; check: number; answer: number };
  content: { question: string; plugins: string[]; connect: string[]; answerTitle: string };
  level?: number; pip?: string;
}> = ({ beats: b, content: c, level, pip }) => {
  const { t, sp, lin } = useT();
  const enter = sp(0);
  const menu = sp(b.plus, { damping: 20, stiffness: 220 }) * (1 - sp(b.ask, { damping: 20, stiffness: 200 }));
  const chat = sp(b.ask);
  const cur = lin(0.1, b.plus - 0.05);
  const connAt = (p: string) => (p === "Gmail" ? b.gmail : b.cal);
  const checking = t >= b.check && t < b.answer;
  const ans = sp(b.answer);
  return (
    <AbsoluteFill style={{ background: BG, fontFamily: FONT }}>
      {level !== undefined && <LevelBadge level={level} from={level - 20} />}
      <div style={{ position: "absolute", left: 60, right: 60, top: TOP, height: BOTTOM - TOP, opacity: enter, transform: `translateY(${(1 - enter) * 60}px)` }}>
        <MacWindow style={{ inset: 0 }}>
          <ModeToggle work={1} top={20} />
 {/* 입력창: 처음엔 가운데, 질문하면 아래로 */}
          <InputBar text="ChatGPT로 Work 시작" work style={{ top: 110, opacity: 1 - chat }} />
 {/* 연결된 플러그인 표시 */}
          <div style={{ position: "absolute", left: 150, top: 206, display: "flex", gap: 10, opacity: 1 - chat }}>
            {c.connect.map((p) => t >= connAt(p) + 0.3 && <div key={p} style={{ transform: `scale(${sp(connAt(p) + 0.3)})` }}><PlugIcon kind={p} s={34} /></div>)}
          </div>
 {/* 플러그인 목록 */}
          {menu > 0.01 && (
            <div style={{ position: "absolute", left: 36, right: 36, top: 272, borderRadius: 26, background: "#fff", border: `2px solid ${LINE}`, padding: "12px 0",
              boxShadow: "0 14px 34px rgba(20,30,60,0.14)", opacity: menu, transform: `translateY(${(1 - menu) * -20}px)` }}>
              <div style={{ fontSize: 28, fontWeight: 800, color: SUB, padding: "0 28px 8px" }}>플러그인</div>
              {c.plugins.map((p) => {
                const on = c.connect.includes(p) && t >= connAt(p);
                const tg = c.connect.includes(p) ? sp(connAt(p), { damping: 18, stiffness: 260 }) : 0;
                return (
                  <div key={p} style={{ display: "flex", alignItems: "center", gap: 20, height: 72, padding: "0 28px", background: on ? "#EEF1FF" : "transparent" }}>
                    <PlugIcon kind={p} s={46} />
                    <div style={{ fontSize: 36, fontWeight: 800, color: INK, flex: 1 }}>{p}</div>
                    {c.connect.includes(p) && (
                      <div style={{ width: 76, height: 42, borderRadius: 21, background: on ? BLUE : "#D5D8DE", position: "relative" }}>
                        <div style={{ position: "absolute", top: 4, left: 4 + 34 * tg, width: 34, height: 34, borderRadius: 17, background: "#fff" }} />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
 {/* 대화 */}
          {chat > 0 && (
            <div style={{ position: "absolute", left: 36, right: 36, top: 110, display: "flex", flexDirection: "column", gap: 22, opacity: chat }}>
              <Bubble text={c.question} pop={chat} size={44} typeAt={b.ask} />
              {t >= b.check && (
                <div style={{ display: "flex", alignItems: "center", gap: 14, fontSize: 36, fontWeight: 800, color: checking ? SUB : BLUE }}>
                  <PlugIcon kind="Google Calendar" s={46} />
                  {checking ? "Google Calendar 확인 중…" : "✓ Google Calendar 확인함"}
                </div>
              )}
              {ans > 0 && (
                <div style={{ opacity: ans, transform: `translateY(${(1 - ans) * 30}px)`, borderRadius: 26, border: `3px solid ${LINE}`, padding: "20px 24px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 16, fontSize: 44, fontWeight: 900, color: INK, marginBottom: 12 }}>
                    <PlugIcon kind="Google Calendar" s={52} />{c.answerTitle}
                  </div>
 {/* 일정 내용은 사용자 캘린더라 흐리게(지어내지 않고 개인정보도 가린다) */}
                  {[0, 1, 2].map((i) => (
                    <div key={i} style={{ display: "flex", alignItems: "center", gap: 20, height: 74, opacity: sp(b.answer + 0.15 + i * 0.2) }}>
                      <div style={{ width: 12, height: 58, borderRadius: 6, background: ["#4285F4", "#0F9D58", "#F4B400"][i] }} />
                      <div style={{ width: 130, height: 30, borderRadius: 15, background: "#C9CED6", filter: "blur(4px)" }} />
                      <div style={{ width: [400, 320, 360][i], height: 30, borderRadius: 15, background: "#8A9099", filter: "blur(4px)" }} />
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
          {t < b.cal + 0.6 && <Cursor x={interpolate(cur, [0, 1], [420, 48])} y={interpolate(cur, [0, 1], [420, 222])} click={t >= b.plus && t < b.ask ? lin(b.plus - 0.02, b.plus + 0.4) : 0} />}
        </MacWindow>
      </div>
      {pip && <PersonPip pip={pip} enter={enter} />}
    </AbsoluteFill>
  );
};

/**
 * ④ GPT 앱에서 명령 → 그 창 안에서 실제 화면 기록 재생 (위엔 자료화면 창, 아래엔 인물 — 화면 기록을 창 크기에 맞춰 좌우가 덜 잘리게).
 * prompt: 말풍선(실제 명령), chip: 명령 뒤에 붙는 작은 표시(예: "⏰ 매일 오전 9:00 예약"), chipAt
 * video: public 안 화면 기록, from: 원본 시작 초, rate: 배속(척척 처리하는 느낌은 6~9배), showAt: 창 안에 화면 기록이 들어오는 시각
 * cropTop: 화면 기록 위쪽에서 잘라낼 비율(앱 제목 줄·브라우저 탭 줄), badge: 화면 기록 위 작은 표시(예: "▶▶ 8배속")
 */
export const RecScene: React.FC<{
  prompt: string; chip?: string; chipAt?: number; video: string; from: number; rate?: number; showAt: number;
  srcW: number; srcH: number; cropTop?: number; badge?: string; pip?: string; clips?: (number | number[])[][]; shots?: { a: number; d: number; rate?: number; f0?: number[]; f1?: number[] }[]; typeEnd?: number; control?: { at: number; query: string; site: string; label: string };
}> = ({ prompt, chip, chipAt = 0, video, from, rate = 1, showAt, srcW, srcH, cropTop = 0, badge, pip, clips, shots, typeEnd, control }) => {
  const { t, sp } = useT();
  const enter = sp(0, { damping: 24, stiffness: 380 });
  const bub = sp(0.15);
  const ch = chip ? sp(chipAt, { damping: 12, stiffness: 220 }) : 0;
  const rec = sp(showAt, { damping: 20, stiffness: 170 });
  const winW = 960, top = 260, h = BOTTOM - top, bodyTop = 58;
  const vidW = winW - 8, vidH = (vidW * srcH) / srcW;
  return (
    <AbsoluteFill style={{ background: BG, fontFamily: FONT }}>
      <div style={{ position: "absolute", left: 60, width: winW, top, height: h, opacity: enter, transform: `translateY(${(1 - enter) * 50}px) scale(${1 + 0.03 * Math.min(1, t / Math.max(1, showAt))})`, transformOrigin: "50% 30%" }}>
        <MacWindow style={{ inset: 0 }} sidebar={false} title="ChatGPT">
          <ModeToggle work={1} top={20} />
          <div style={{ position: "absolute", left: 36, right: 36, top: 120, display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 20 }}>
            <div style={{ maxWidth: 760, background: "#EEF1FF", color: INK, fontSize: 40, fontWeight: 800, lineHeight: 1.4, padding: "20px 28px", borderRadius: 30, borderTopRightRadius: 8,
              opacity: bub, transform: `translateY(${(1 - bub) * 30}px)`, minHeight: 56 }}>{typed(prompt, t, 0.15, prompt.length / Math.max(0.6, (typeEnd ?? (chip ? chipAt : showAt)) - 0.4)).shown}<Caret on={typed(prompt, t, 0.15, prompt.length / Math.max(0.6, (typeEnd ?? (chip ? chipAt : showAt)) - 0.4)).typing} /></div>
            {chip && ch > 0 && <div style={{ fontSize: 36, fontWeight: 900, color: "#fff", background: BLUE, padding: "12px 26px", borderRadius: 30, transform: `scale(${ch})` }}>{chip}</div>}
          </div>
 {/* control: "GPT가 내 컴퓨터를 직접 조작" 그래픽 — 창 안에 작은 브라우저, GPT 커서가 검색창을 눌러 검색어를 치고 검색 버튼을 누르면 결과 칸이 뜬다. 그 뒤 실제 화면 기록 */}
          {control && t >= control.at && t < showAt && (() => {
            const lt = t - control.at;
            const inn = sp(control.at, { damping: 20, stiffness: 200 });
            const W = winW - 8, bx = 60, by = 150, bw = W - 120;
            const pts = [[W - 120, 560], [bx + 120, by + 120], [bx + 120, by + 120], [bx + bw - 70, by + 120], [bx + bw - 70, by + 120]];
            const keys = [0, 0.45, 1.25, 1.55, 9];
            const seg = keys.findIndex((k, i) => lt >= k && lt < keys[i + 1]);
            const i0 = Math.max(0, seg), p0 = pts[i0], p1 = pts[Math.min(i0 + 1, pts.length - 1)];
            const qq = Math.min(1, (lt - keys[i0]) / Math.max(0.01, keys[i0 + 1] - keys[i0]));
            const e = qq * qq * (3 - 2 * qq);
            const cx = p0[0] + (p1[0] - p0[0]) * e, cy = p0[1] + (p1[1] - p0[1]) * e;
            const q = control.query.slice(0, Math.max(0, Math.min(control.query.length, Math.floor((lt - 0.5) * 9))));
            const clickA = lt >= 0.45 && lt < 0.8 ? (lt - 0.45) / 0.35 : 0, clickB = lt >= 1.55 && lt < 1.9 ? (lt - 1.55) / 0.35 : 0;
            const grid = lt >= 1.65;
            return (
              <div style={{ position: "absolute", left: 4, right: 4, top: 4, bottom: 4, borderRadius: 18, background: "#F3F4F6", overflow: "hidden", opacity: inn }}>
                <div style={{ position: "absolute", left: 0, right: 0, top: 26, textAlign: "center" }}>
                  <span style={{ fontSize: 36, fontWeight: 900, color: "#fff", background: BLUE, padding: "10px 26px", borderRadius: 30 }}>{control.label}</span>
                </div>
                <div style={{ position: "absolute", left: bx, width: bw, top: by - 30, bottom: 30, borderRadius: 22, background: "#fff", boxShadow: "0 10px 30px rgba(20,30,60,0.12)", overflow: "hidden" }}>
                  <div style={{ height: 50, background: "#F4F4F5", display: "flex", alignItems: "center", gap: 10, padding: "0 18px" }}>
                    {["#FF5F57", "#FEBC2E", "#28C840"].map((c) => <div key={c} style={{ width: 14, height: 14, borderRadius: 7, background: c }} />)}
                    <div style={{ marginLeft: 14, flex: 1, height: 32, borderRadius: 16, background: "#fff", fontSize: 22, fontWeight: 700, color: "#5F6368", display: "flex", alignItems: "center", paddingLeft: 16 }}>{control.site}</div>
                  </div>
                  <div style={{ margin: "40px 40px 0", height: 80, borderRadius: 40, border: `3px solid ${lt >= 0.45 ? BLUE : LINE}`, display: "flex", alignItems: "center", padding: "0 30px",
                    fontSize: 38, fontWeight: 800, color: INK }}>
                    {q || <span style={{ color: "#B4B8BF" }}>검색어를 입력하세요</span>}<Caret on={lt >= 0.45 && lt < 1.6} />
                    <div style={{ marginLeft: "auto", fontSize: 38 }}>🔍</div>
                  </div>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 16, margin: "30px 40px" }}>
                    {Array.from({ length: 8 }).map((_, i) => {
                      const pp = grid ? Math.min(1, Math.max(0, (lt - 1.65 - i * 0.05) / 0.2)) : 0;
                      return <div key={i} style={{ height: 150, borderRadius: 14, background: ["#2B2D31", "#B9BCC2", "#3A3D44", "#D7D9DD"][i % 4], opacity: pp, transform: `scale(${0.8 + 0.2 * pp})` }} />;
                    })}
                  </div>
                </div>
 {/* GPT 커서 */}
                <div style={{ position: "absolute", left: cx, top: cy, zIndex: 5 }}>
                  {(clickA > 0 || clickB > 0) && <div style={{ position: "absolute", left: -40 * (clickA || clickB), top: -40 * (clickA || clickB), width: 80 * (clickA || clickB), height: 80 * (clickA || clickB),
                    borderRadius: "50%", border: `5px solid ${BLUE}`, opacity: 1 - (clickA || clickB) }} />}
                  <svg width="48" height="58" viewBox="0 0 22 27" style={{ filter: "drop-shadow(0 3px 4px rgba(0,0,0,0.3))" }}>
                    <path d="M2 2 L2 22 L7.5 17 L11 25 L14.5 23.5 L11 15.8 L18.5 15.5 Z" fill={BLUE} stroke="#fff" strokeWidth="1.6" strokeLinejoin="round" /></svg>
                  <div style={{ position: "absolute", left: 40, top: 46, fontSize: 24, fontWeight: 900, color: "#fff", background: BLUE, padding: "4px 12px", borderRadius: 12, whiteSpace: "nowrap" }}>GPT</div>
                </div>
              </div>
            );
          })()}
 {/* 화면 기록: 창 본문을 덮으며 아래에서 올라온다. 폭은 창에 맞춰 좌우를 자르지 않는다 */}
          {t >= showAt && (
            <div style={{ position: "absolute", left: 4, right: 4, top: 4, bottom: 4, overflow: "hidden", borderRadius: 18, background: "#fff",
              transform: `translateY(${(1 - rec) * (h - bodyTop)}px)` }}>
              <div style={{ position: "absolute", left: 0, top: -cropTop * vidH, width: vidW, height: vidH }}>
 {/* Sequence로 감싸야 화면 기록이 "들어오는 순간"부터 from초에서 재생된다(안 감싸면 장면 시작부터 시간이 흘러 있음) */}
 {/* clips: 원본에서 [시작, 끝] 구간만 이어 붙여 같은 배속으로(멈춰 있는 구간은 건너뜀 — 척척 처리하는 느낌) */}
 {/* 구간마다 focus [x, y, 배율](원본 기준 0~1)를 주면 그 자리로 확대 — 작은 곳만 바뀌는 화면(옵션 고르기)이 멈춘 것처럼 보이지 않게 */}
 {/* shots: 말 한 마디마다 한 컷("가격을 비교하고 / 리뷰를 보고 / 장바구니에 담는" 각각을 화면에). 
                    a: 원본 시작 초, d: 보여 줄 길이, rate: 배속, f0→f1: [x, y, 배율] 기준점·배율이 컷 동안 천천히 바뀐다(멈춘 화면도 움직여 보이게) */}
                {shots && shots.reduce<{ at: number; els: React.ReactNode[] }>((acc, sh, k) => {
                  const st = showAt + acc.at;
                  const f0 = sh.f0 ?? [0.5, 0.5, 1], f1 = sh.f1 ?? f0;
                  const q = interpolate(t, [st, st + sh.d], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: (x) => x * (2 - x) });
                  const L = (i: number) => f0[i] + (f1[i] - f0[i]) * q;
                  acc.els.push(
                    <Sequence key={k} from={Math.round(st * 30)} durationInFrames={Math.max(1, Math.round(sh.d * 30))} layout="none">
                      <div style={{ position: "absolute", width: vidW, height: vidH, transform: `scale(${L(2)})`, transformOrigin: `${L(0) * vidW}px ${L(1) * vidH}px` }}>
                        <OffthreadVideo src={staticFile(video)} muted playbackRate={sh.rate ?? 1} startFrom={Math.round(sh.a * 30)} style={{ width: vidW, height: vidH }} />
                      </div>
                    </Sequence>);
                  acc.at += sh.d;
                  return acc;
                }, { at: 0, els: [] }).els}
                {!shots && (clips ?? [[from, 1e6]]).reduce<{ at: number; prev: number; els: React.ReactNode[] }>((acc, c, k) => {
                  const [a, z] = c as number[];
                  const fc = (c[2] as number[] | undefined) ?? [0.5, 0.5, 1];
                  const len = (z - a) / rate;
                  const st = showAt + acc.at;
                  const zs = interpolate(t, [st, st + 0.3], [acc.prev, fc[2]], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: (x) => 1 - Math.pow(1 - x, 3) });
                  acc.els.push(
                    <Sequence key={k} from={Math.round(st * 30)} durationInFrames={clips ? Math.max(1, Math.round(len * 30)) : undefined} layout="none">
                      <div style={{ position: "absolute", width: vidW, height: vidH, transform: `scale(${zs})`, transformOrigin: `${fc[0] * vidW}px ${fc[1] * vidH}px` }}>
                        <OffthreadVideo src={staticFile(video)} muted playbackRate={rate} startFrom={Math.round(a * 30)} style={{ width: vidW, height: vidH }} />
                      </div>
                    </Sequence>);
                  acc.at += len;
                  acc.prev = fc[2];
                  return acc;
                }, { at: 0, prev: 1, els: [] }).els}
              </div>
              {badge && (
                <div style={{ position: "absolute", right: 18, top: 18, display: "flex", alignItems: "center", gap: 12, fontSize: 34, fontWeight: 900, color: "#111",
                  background: "#FFD43B", padding: "10px 22px 10px 16px", borderRadius: 24, boxShadow: "0 6px 16px rgba(0,0,0,0.25)" }}>
                  <svg width="40" height="36" viewBox="0 0 40 36"><path d="M20 2 L38 34 L2 34 Z" fill="#111" stroke="#111" strokeWidth="3" strokeLinejoin="round" />
                    <rect x="18" y="12" width="4" height="12" rx="2" fill="#FFD43B" /><circle cx="20" cy="29" r="2.4" fill="#FFD43B" /></svg>
                  {badge}
                </div>
              )}
            </div>
          )}
        </MacWindow>
      </div>
      {pip && <PersonPip pip={pip} enter={enter} />}
    </AbsoluteFill>
  );
};

/**
 * ⑤ 퍼센트 막대: "10%", "40%"처럼 퍼센트를 말할 때 막대가 딱 그만큼 차오르며 숫자가 올라간다.
 * 인물 위에 얹는 투명 카드 — 자막(세로 약 1,120px) 바로 아래 가운데. 크기는 1.2배(사용자가 CapCut에서 키운 크기) → 가로 약 120~960px, 세로 약 1,190~1,400px.
 * level: 0~100, label: 왼쪽 글, low: 낮은 값(빨강)으로 칠할지
 */
export const PercentBar: React.FC<{ level: number; label?: string; low?: boolean }> = ({ level, label = "GPT 활용도", low }) => {
  const { sp, lin } = useT();
  const inn = sp(0, { damping: 14, stiffness: 260 });
  const fill = level * (1 - Math.pow(1 - lin(0.08, 0.6), 3));
  const col = low ? "#EC1D1D" : BLUE;
  return (
    <AbsoluteFill style={{ fontFamily: FONT }}>
      <div style={{ position: "absolute", left: 190, width: 700, top: 1205, padding: "22px 30px 28px", borderRadius: 34, background: "rgba(255,255,255,0.96)",
        boxShadow: "0 14px 36px rgba(0,0,0,0.28)", transform: `scale(${1.2 * (0.85 + 0.15 * inn)})`, transformOrigin: "50% 50%", opacity: Math.min(1, inn * 1.5), boxSizing: "border-box" }}>
        <div style={{ display: "flex", alignItems: "baseline", justifyContent: "space-between" }}>
          <div style={{ fontSize: 38, fontWeight: 900, color: INK }}>{label}</div>
          <div style={{ fontSize: 72, fontWeight: 900, color: col, lineHeight: 1 }}>{Math.round(fill)}%</div>
        </div>
        <div style={{ position: "relative", height: 34, borderRadius: 17, background: "#E3E6EC", marginTop: 14, overflow: "hidden" }}>
          <div style={{ width: `${fill}%`, height: "100%", borderRadius: 17, background: col }} />
          {[25, 50, 75].map((m) => <div key={m} style={{ position: "absolute", left: `${m}%`, top: 0, bottom: 0, width: 3, background: "rgba(255,255,255,0.7)" }} />)}
        </div>
      </div>
    </AbsoluteFill>
  );
};
