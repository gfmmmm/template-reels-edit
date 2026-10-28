// AI 에이전트 시대 릴스 — 가로 배치판: 9:16 검은 바탕 가운데 가로 영상 띠(세로 580~1300px), 위 제목·영상 위 자막은 CapCut.
// 2분할(카드 + 아래 인물 창) 없음. 실제 시연 장면은 원본 그대로 두고 위에 작은 표시만(투명), 설명 장면은 띠 전체를 그래픽으로 채운다.
// 시각(at·beats)은 장면 시작부터의 초. 영상마다 바뀌는 글·숫자·그림은 props.
import React from "react";
import { AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";

// 영상 띠: 원래 580~1300(1080×720) → "전체 110%" 로 띠를 키움(가운데 기준 1.1배 → 542~1334, 1080×792)
export const BAND = { top: 542, h: 792 };
const BLUE = "#3B5BFD";
const INK = "#1F2329";
const SUB = "#8A9099";
const GREEN = "#12B76A";
const RED = "#EC1D1D";
const HL = "rgba(255,214,0,0.55)";
const FONT = "'Apple SD Gothic Neo', Pretendard, sans-serif";

const useT = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = f / fps;
  const sp = (at: number, cfg = { damping: 18, stiffness: 190 }) => (t < at ? 0 : spring({ frame: f - at * fps, fps, config: cfg }));
  const lin = (a: number, b: number) => interpolate(t, [a, b], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return { f, t, sp, lin };
};
const ease = (x: number) => x * x * (3 - 2 * x);

// 띠 안 좌표계(1080×720)로 그리는 틀. fill=true면 띠를 연한 회색으로 채우고 바깥은 검정
// fill은 예전 호환용 — 바탕을 칠하지 않는다(모든 그래픽은 흰 바탕 없이 인물 위에)
const Band: React.FC<{ fill?: boolean; children: React.ReactNode }> = ({ children }) => (
  <AbsoluteFill style={{ background: "transparent", fontFamily: FONT }}>
    <div style={{ position: "absolute", left: 0, top: BAND.top, width: 1080, height: BAND.h, overflow: "hidden", background: "transparent" }}>
      {children}
    </div>
  </AbsoluteFill>
);

const Chip: React.FC<{ p: number; bg: string; color?: string; size?: number; style?: React.CSSProperties; children: React.ReactNode }> = ({ p, bg, color = "#fff", size = 38, style, children }) => (
  <div style={{ display: "inline-flex", alignItems: "center", gap: 12, background: bg, color, fontSize: size, fontWeight: 900, padding: "14px 26px", borderRadius: 40,
    boxShadow: "0 10px 26px rgba(0,0,0,0.28)", opacity: p, transform: `translateY(${(1 - p) * 24}px) scale(${0.9 + 0.1 * p})`, whiteSpace: "nowrap", ...style }}>{children}</div>
);

// 실제 시연 장면 위 표시는 얼굴을 가리지 않게 영상 띠 바로 아래 검은 칸(세로 1,320~1,500px)에 두 줄로
const Below: React.FC<{ row1?: React.ReactNode; row2?: React.ReactNode }> = ({ row1, row2 }) => (
  <AbsoluteFill style={{ fontFamily: FONT }}>
    <div style={{ position: "absolute", left: 0, right: 0, top: BAND.top + BAND.h + 22, display: "flex", flexDirection: "column", alignItems: "center", gap: 14 }}>
      {row1}{row2}
    </div>
  </AbsoluteFill>
);

// ① 실제 통화: "● 실제 통화" + 지금 말하는 쪽 → 끝나면 예약 완료
export const CallOverlay: React.FC<{ label: string; turns: { who: "ai" | "them"; at: number }[]; done?: { at: number; text: string } }> = ({ label, turns, done }) => {
  const { t, sp } = useT();
  const cur = [...turns].reverse().find((x) => t >= x.at);
  const secs = Math.floor(t) + 3;
  const finished = done && t >= done.at;
  return (
    <Below
      row1={<Chip p={sp(0)} bg="#1C2340" size={34}>
        <span style={{ width: 18, height: 18, borderRadius: 9, background: finished ? GREEN : "#FF3B30", opacity: finished ? 1 : 0.55 + 0.45 * Math.abs(Math.sin(t * 4)) }} />
        {finished ? "통화 종료" : label}
        <span style={{ fontVariantNumeric: "tabular-nums", color: "#AEB6D6" }}>00:{String(Math.min(secs, done ? Math.floor(done.at) + 3 : secs)).padStart(2, "0")}</span>
      </Chip>}
      row2={finished ? <Chip p={sp(done!.at, { damping: 13, stiffness: 200 })} bg="#fff" color={INK} size={44}><span style={{ color: GREEN }}>✓</span>{done!.text}</Chip>
        : cur && cur.who === "ai" && <Chip key={cur.at} p={sp(cur.at, { damping: 15, stiffness: 260 })} bg={BLUE} size={42}>🤖 AI가 전화로 말하는 중</Chip>}
    />
  );
};

// ② 실제 장보기 시연: 위 줄은 내가 보낸 말(한 글자씩), 아래 줄은 AI가 하는 일(바뀜)
export const ShopOverlay: React.FC<{ ask: { text: string; at: number }; steps: { text: string; at: number; pay?: boolean }[]; intro?: string }> = ({ ask, steps, intro }) => {
  const { t, sp } = useT();
  const n = Math.floor(Math.min(1, Math.max(0, (t - ask.at) / 0.8)) * ask.text.length);
  const cur = [...steps].reverse().find((x) => t >= x.at);
  return (
    <Below
      row1={t < ask.at ? (intro ? <Chip p={sp(0)} bg="#1C2340" size={42}>{intro}</Chip> : null) : <Chip p={sp(ask.at)} bg={BLUE} size={42}>💬 {ask.text.slice(0, n)}{n < ask.text.length ? "|" : ""}</Chip>}
      row2={cur && <Chip key={cur.at} p={sp(cur.at, { damping: 15, stiffness: 240 })} bg={cur.pay ? "#fff" : "#1C2340"} color={cur.pay ? INK : "#fff"} size={42}>{cur.text}</Chip>}
    />
  );
};

// ③ 실제 KIWI 메시지 화면(사용자 캡처)을 띄우고, 말에 맞춰 그 줄을 형광펜으로 칠하며 다가간다 → 아낀 돈
type Box = { x: number; y: number; w: number; h: number };
export const KiwiScene: React.FC<{
  img: string; imgW: number; imgH: number; marks: { at: number; boxes: Box[]; zoom?: number }[];
  saved: { at: number; value: number; label: string };
}> = ({ img, imgW, imgH, marks, saved }) => {
  const { t, sp, lin } = useT();
  const enter = sp(0, { damping: 16, stiffness: 160 });
  const W = 1040, s0 = W / imgW, H = imgH * s0;
 // 카메라: 지금 칠하는 상자들의 가운데로 다가간다
  const active = [...marks].reverse().find((m) => t >= m.at);
  const prevI = active ? marks.indexOf(active) - 1 : -1;
  const center = (m?: { boxes: Box[] }) => {
    if (!m) return { cx: imgW / 2, cy: imgH / 2 };
    const xs = m.boxes.flatMap((b) => [b.x, b.x + b.w]), ys = m.boxes.flatMap((b) => [b.y, b.y + b.h]);
    return { cx: (Math.min(...xs) + Math.max(...xs)) / 2, cy: (Math.min(...ys) + Math.max(...ys)) / 2 };
  };
  const out = t >= saved.at;
  const k = active ? ease(lin(active.at, active.at + 0.45)) : 0;
  const a = center(prevI >= 0 ? marks[prevI] : undefined), b = center(active);
  const za = prevI >= 0 ? marks[prevI].zoom ?? 1.3 : 1, zb = active ? active.zoom ?? 1.3 : 1;
  let cx = imgW / 2, cy = a.cy + (b.cy - a.cy) * k, z = za + (zb - za) * k;
  if (out) { const o = ease(lin(saved.at, saved.at + 0.4)); cy = cy + (imgH / 2 - cy) * o; z = z + (1 - z) * o; }
  const sv = sp(saved.at + 0.15, { damping: 11, stiffness: 190 });
  const num = saved.value * lin(saved.at + 0.2, saved.at + 0.65);
  return (
    <Band fill>
      <div style={{ position: "absolute", left: 540 - cx * s0 * z, top: (out ? 300 : 210) - cy * s0 * z, width: W * z, height: H * z, opacity: enter,
        transform: `translateY(${(1 - enter) * 60}px)`, filter: out ? `blur(${3 * sv}px) brightness(${1 - 0.25 * sv})` : undefined }}>
        <Img src={staticFile(img)} style={{ width: "100%", height: "100%", borderRadius: 24, boxShadow: "0 18px 50px rgba(20,30,60,0.16)" }} />
        {marks.map((m, i) => t >= m.at && m.boxes.map((bx, j) => {
          const p = lin(m.at + j * 0.25, m.at + j * 0.25 + 0.35);
          return <div key={`${i}-${j}`} style={{ position: "absolute", left: bx.x * s0 * z, top: bx.y * s0 * z, width: bx.w * s0 * z * p, height: bx.h * s0 * z,
            background: HL, mixBlendMode: "multiply", borderRadius: 6 }} />;
        }))}
      </div>
      {out && (
        <div style={{ position: "absolute", left: 0, right: 0, top: 50, textAlign: "center", opacity: sv, transform: `scale(${0.6 + 0.4 * sv})` }}>
          <div style={{ display: "inline-block", background: "#fff", borderRadius: 44, padding: "24px 60px", border: `6px solid ${GREEN}`, boxShadow: "0 24px 60px rgba(18,183,106,0.35)" }}>
            <div style={{ fontSize: 42, fontWeight: 900, color: INK }}>{saved.label}</div>
            <div style={{ fontSize: 180, fontWeight: 900, color: GREEN, lineHeight: 1.05, fontVariantNumeric: "tabular-nums" }}>+${num.toFixed(2)}</div>
          </div>
        </div>
      )}
    </Band>
  );
};

// ④ 해외 AI 비서 로고 / ⑥ 한국 아직 ✕ — 띠 전체
export const LogosBand: React.FC<{ title: string; agents: { name: string; maker: string; img: string; at: number }[]; locked?: { at: number; text: string }; locked2?: { at: number; text: string }; or?: boolean }> = ({ title, agents, locked, locked2, or }) => {
  const { t, sp } = useT();
  const lk = locked ? sp(locked.at, { damping: 10, stiffness: 220 }) : 0;
  return (
    <Band fill>
      {title && <div style={{ position: "absolute", left: 0, right: 0, top: 26, textAlign: "center", fontSize: 50, fontWeight: 900, color: INK, opacity: sp(0) }}>{title}</div>}
      <div style={{ position: "absolute", left: 40, right: 40, top: title ? 110 : 60, display: "flex", gap: 30, justifyContent: "center", transformOrigin: "50% 0%", transform: or ? `scale(${1 - 0.45 * lk}) translateY(${-lk * 40}px)` : undefined }}>
        {agents.map((a, i) => {
          const p = sp(a.at, { damping: 12, stiffness: 200 });
          return (
            <div key={a.name} style={{ width: 290, height: 330, background: "#fff", borderRadius: 36, boxShadow: "0 18px 50px rgba(20,30,60,0.10)", padding: "24px 20px", textAlign: "center",
              opacity: p, transform: `translateY(${(1 - p) * 100 + (p > 0.99 ? Math.sin((t - a.at) * 2.4 + i) * 5 : 0)}px) scale(${0.7 + 0.3 * p})`, filter: lk > 0 ? `grayscale(${lk})` : undefined }}>
              <div style={{ width: 180, height: 180, borderRadius: 32, overflow: "hidden", margin: "0 auto" }}>
                <Img src={staticFile(a.img)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
              </div>
              <div style={{ fontSize: 50, fontWeight: 900, color: INK, marginTop: 14 }}>{a.name}</div>
              <div style={{ fontSize: 32, fontWeight: 800, color: SUB, marginTop: 4 }}>{a.maker}</div>
            </div>
          );
        })}
      </div>
      {or ? (
        <div style={{ position: "absolute", left: 0, right: 0, top: 250, display: "flex", alignItems: "center", justifyContent: "center", gap: 22 }}>
          {[locked, null, locked2].map((x, i) => {
            const at = i === 1 ? (locked2 ? locked2.at - 0.25 : 1e9) : x ? x.at : 1e9;
            if (t < at) return <div key={i} style={{ width: i === 1 ? 110 : 400 }} />;
            const q = sp(at, { damping: 10, stiffness: 230 });
            if (i === 1) return <div key={i} style={{ width: 110, height: 110, borderRadius: 55, background: "#FFD43B", color: INK, fontSize: 50, fontWeight: 900,
              display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${q})`, boxShadow: "0 10px 26px rgba(0,0,0,0.25)" }}>OR</div>;
            return <div key={i} style={{ width: 400, textAlign: "center", fontSize: 50, fontWeight: 900, lineHeight: 1.2, padding: "18px 10px", whiteSpace: "pre-line", wordBreak: "keep-all", borderRadius: 26, transform: `scale(${2 - q}) rotate(${i === 0 ? -4 : 4}deg)`, opacity: q,
              ...(i === 0 ? { color: RED, border: `9px solid ${RED}`, background: "rgba(255,255,255,0.95)" } : { color: "#fff", background: INK, boxShadow: "0 12px 30px rgba(0,0,0,0.3)" }) }}>{x!.text}</div>;
          })}
        </div>
      ) : (<>
      {locked2 && t >= locked2.at && (
        <div style={{ position: "absolute", left: 0, right: 0, top: 330, textAlign: "center", opacity: sp(locked2.at, { damping: 12, stiffness: 220 }), transform: `translateY(${(1 - sp(locked2.at)) * 30}px)` }}>
          <span style={{ display: "inline-block", fontSize: 56, fontWeight: 900, color: "#fff", background: INK, borderRadius: 24, padding: "12px 36px", boxShadow: "0 12px 30px rgba(0,0,0,0.3)" }}>✉️ {locked2.text}</span>
        </div>
      )}
      {locked && t >= locked.at && (
        <div style={{ position: "absolute", left: 0, right: 0, top: 170, textAlign: "center", opacity: lk, transform: `scale(${2 - lk})` }}>
          <span style={{ display: "inline-block", fontSize: 84, fontWeight: 900, color: RED, border: `10px solid ${RED}`, borderRadius: 28, padding: "8px 42px", background: "rgba(255,255,255,0.92)" }}>{locked.text}</span>
        </div>
      )}
      </>)}
    </Band>
  );
};

// ⑤ 비서 → 직원 (사원증이 뒤집힘) — 띠 전체, 가로로 놓인 사원증
export const EmployeeBand: React.FC<{ from: string; to: string; flipAt: number; sub: string }> = ({ from, to, flipAt, sub }) => {
  const { t, sp } = useT();
  const flip = sp(flipAt, { damping: 16, stiffness: 140 });
  const angle = flip * 180, face = angle < 90;
  return (
    <Band fill>
      <div style={{ position: "absolute", left: 190, top: 40, width: 700, height: 390, background: "#fff", borderRadius: 44, boxShadow: "0 18px 50px rgba(20,30,60,0.12)",
        border: `6px solid ${face ? "#E6E8EC" : BLUE}`, opacity: sp(0), transform: `rotate(${Math.sin(t * 2.2) * 1.5}deg) perspective(1600px) rotateY(${face ? angle : angle - 180}deg)`,
        display: "flex", alignItems: "center", gap: 40, padding: "0 56px", boxSizing: "border-box" }}>
        <div style={{ width: 200, height: 200, borderRadius: 100, flexShrink: 0, background: face ? "#EEF1FF" : BLUE, fontSize: 120, display: "flex", alignItems: "center", justifyContent: "center" }}>🤖</div>
        <div>
          <div style={{ fontSize: 30, fontWeight: 800, color: face ? SUB : BLUE, letterSpacing: 4 }}>{face ? "ASSISTANT" : "EMPLOYEE"}</div>
          <div style={{ fontSize: 96, fontWeight: 900, color: face ? INK : BLUE, lineHeight: 1.1 }}>AI {face ? from : to}</div>
          {!face && <div style={{ fontSize: 46, fontWeight: 900, color: INK, marginTop: 10, opacity: sp(flipAt + 0.35) }}>{sub}</div>}
        </div>
      </div>
    </Band>
  );
};

// ⑦ 먼저 말 거는 AI — 종이 질감 흰 바탕(두 장을 번갈아 끓는 느낌) 위 오려 낸 종이 조각, 1초 8장 스톱모션
const PAPER = "images/collage/paper_white.png";
const Cut: React.FC<{ src: string; w: number; x: number; y: number; at: number; t: number; step: number; rot?: number; children?: React.ReactNode }> = ({ src, w, x, y, at, t, step, rot = 0, children }) => {
  if (t < at) return null;
  const k = Math.min(1, (t - at) / 0.25);
  const j = ((step * 37) % 7) - 3, jr = ((step * 53) % 5) - 2;
  return (
    <div style={{ position: "absolute", left: x - w / 2 + j * 0.6, top: y + (1 - k) * 60 + jr * 0.6, width: w, transform: `rotate(${rot + jr * 0.5}deg) scale(${0.85 + 0.15 * k})`, opacity: k,
      filter: "drop-shadow(4px 8px 6px rgba(0,0,0,0.28))" }}>
      <Img src={staticFile(src)} style={{ width: "100%" }} />
      {children}
    </div>
  );
};
export const PaperProactive: React.FC<{ beats: { robot: number; talk: number; card: number; mail: number; scan: number }; talkText: string; cardText: string; mailText: string }> = ({ beats, talkText, cardText, mailText }) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const step = Math.floor(f / (fps / 8));
  const t = step / 8;
  const flip = step % 2 === 1;
  const scanX = t >= beats.scan ? Math.sin((t - beats.scan) * 5) * 110 : 0;
  return (
    <AbsoluteFill style={{ background: "#000", fontFamily: FONT }}>
      <div style={{ position: "absolute", left: 0, top: BAND.top, width: 1080, height: BAND.h, overflow: "hidden" }}>
        <Img src={staticFile(PAPER)} style={{ position: "absolute", width: 1180, left: flip ? -70 : -30, top: flip ? -420 : -360, transform: flip ? "scaleX(-1) rotate(180deg)" : undefined }} />
        <div style={{ position: "absolute", inset: 0, background: "rgba(255,253,247,0.25)" }} />
 {/* 1) 로봇이 먼저 말을 건다 */}
        <Cut src="images/collage/robot.png" w={280} x={180} y={60} at={beats.robot} t={t} step={step} rot={-4} />
        <Cut src="images/collage/bubble.png" w={420} x={470} y={8} at={beats.talk} t={t} step={step + 1} rot={2}>
          <div style={{ position: "absolute", left: 0, right: 0, top: 78, textAlign: "center", fontSize: 60, fontWeight: 900, color: INK, lineHeight: 1.1, whiteSpace: "pre-line" }}>{talkText}</div>
        </Cut>
 {/* 2) 어도비 정기결제 해지 */}
        <Cut src="images/collage/card.png" w={360} x={870} y={30} at={beats.card} t={t} step={step + 2} rot={5}>
          {t >= beats.card + 0.3 && <div style={{ position: "absolute", left: 20, right: 20, top: 70, textAlign: "center", fontSize: 46, fontWeight: 900, color: RED, border: `6px solid ${RED}`, borderRadius: 14,
            background: "rgba(255,255,255,0.85)", transform: "rotate(-8deg)", padding: "4px 0" }}>{cardText}</div>}
        </Cut>
 {/* 3) 지메일을 뒤져본다 */}
        <Cut src="images/collage/envelope.png" w={390} x={700} y={225} at={beats.mail} t={t} step={step + 3} rot={-3}>
          <div style={{ position: "absolute", left: -120, top: 70, fontSize: 56, fontWeight: 900, color: INK, transform: "rotate(-6deg)" }}>{mailText}</div>
        </Cut>
        <Cut src="images/collage/magnifier.png" w={250} x={700 + scanX} y={190} at={beats.scan} t={t} step={step + 4} rot={-20} />
      </div>
    </AbsoluteFill>
  );
};

// ⑧ 실제 화면 캡처를 영상 위에 크게(PIP) + 짚을 줄 형광펜
export const ImagePip: React.FC<{ img: string; imgW: number; imgH: number; h: number; marks: { at: number; box: Box }[]; logo?: string }> = ({ img, imgW, imgH, h, marks, logo }) => {
  const { t, sp, lin } = useT();
  const p = sp(0, { damping: 15, stiffness: 200 });
  const s0 = h / imgH, w = imgW * s0;
  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", left: 540 - w / 2, top: BAND.top + (BAND.h - h) / 2, width: w, height: h, borderRadius: 28, overflow: "hidden",
        boxShadow: "0 24px 60px rgba(0,0,0,0.55)", border: "4px solid #fff", opacity: p, transform: `scale(${0.85 + 0.15 * p}) translateY(${(1 - p) * 40}px)` }}>
        <Img src={staticFile(img)} style={{ width: "100%", height: "100%" }} />
        {marks.map((m, i) => t >= m.at && (
          <div key={i} style={{ position: "absolute", left: m.box.x * s0, top: m.box.y * s0, width: m.box.w * s0 * lin(m.at, m.at + 0.3), height: m.box.h * s0,
            border: `5px solid #FFD43B`, borderRadius: 12, background: "rgba(255,212,59,0.18)" }} />
        ))}
      </div>
      {logo && <div style={{ position: "absolute", left: 540 - w / 2 - 40, top: BAND.top + (BAND.h - h) / 2 - 34, background: "#fff", border: "6px solid #fff", borderRadius: 22,
        padding: "14px 24px", boxShadow: "0 10px 26px rgba(0,0,0,0.45)", opacity: p, transform: `rotate(-4deg) scale(${0.8 + 0.2 * p})` }}>
        <Img src={staticFile(logo)} style={{ height: 58, display: "block" }} />
      </div>}
    </AbsoluteFill>
  );
};

// ⑨ 먼저 말 거는 AI — 평소 스타일(연회색 바탕 + 흰 둥근 카드 + 파랑), 띠 전체 (종이 질감 말고 늘 쓰는 그래픽)
// 알림 "○○님! 보고 드릴게 있어요!" → 어도비 구독 해지(스위치 꺼짐) → AI가 돋보기로 Gmail을 훑다가 해지 안 된 메일 발견
const card2: React.CSSProperties = { background: "#fff", borderRadius: 32, boxShadow: "0 18px 50px rgba(20,30,60,0.10), 0 2px 8px rgba(20,30,60,0.06)" };
const back = (b: number): React.CSSProperties => ({ transform: `translateY(${-b * 30}px) scale(${1 - 0.12 * b})`, opacity: 1 - 0.75 * b, filter: `blur(${b * 3}px)` });
export const ProactiveApp: React.FC<{
  avatar: string; agent: string; notif: string; adobeLogo: string; plan: string; mails: { from: string; subject: string; hit?: boolean }[]; found: string;
  beats: { notif: number; adobe: number; off: number; mail: number; scan: number; found: number }; corner?: boolean;
}> = ({ avatar, agent, notif, adobeLogo, plan, mails, found, beats, corner }) => {
  const { t, sp, lin } = useT();
  const n = beats.notif < 0 ? 0 : sp(beats.notif, { damping: 14, stiffness: 200 });
  const ad = sp(beats.adobe), off = lin(beats.off, beats.off + 0.25), ml = sp(beats.mail);
  const scan = lin(beats.scan, beats.found);
  const rowH = 92, hitI = mails.findIndex((m) => m.hit);
  const lensY = 150 + scan * (mails.length - 0.5) * rowH;
  const fd = sp(beats.found, { damping: 12, stiffness: 220 });
  return (
    <Band fill>
 {/* 1) 알림 (notif < 0 이면 없음) */}
      {beats.notif >= 0 && <div style={{ position: "absolute", left: 90, right: 90, top: 120, ...card2, padding: "28px 34px", display: "flex", alignItems: "center", gap: 26,
        opacity: n, transform: `translateY(${(1 - n) * -140}px)`, ...(ad > 0 ? back(ad) : {}) }}>
        <Img src={staticFile(avatar)} style={{ width: 120, height: 120, borderRadius: 60, objectFit: "cover", background: "#fff", border: "4px solid #EEF1FF" }} />
        <div style={{ flex: 1 }}>
          <div style={{ display: "flex", alignItems: "center", gap: 12, fontSize: 30, fontWeight: 800, color: SUB }}>
            <span style={{ color: INK, fontWeight: 900 }}>{agent}</span> · 지금 <span style={{ marginLeft: "auto", fontSize: 34 }}>🔔</span>
          </div>
          <div style={{ fontSize: 56, fontWeight: 900, color: INK, marginTop: 8, lineHeight: 1.2 }}>{notif}</div>
        </div>
      </div>}
 {/* 2) 어도비 구독 해지 */}
      {t >= beats.adobe && (
        <div style={{ position: "absolute", ...(corner ? { left: 520, right: 40, top: 40, height: 330, transformOrigin: "100% 0%" } : { left: 150, right: 150, top: 70, height: 360 }), ...card2, padding: corner ? "30px 36px" : "36px 44px",
          boxShadow: "0 18px 50px rgba(0,0,0,0.35)", opacity: ad, transform: `translateY(${(1 - ad) * 80}px) scale(${0.85 + 0.15 * ad})`, ...(ml > 0 ? back(ml) : {}) }}>
          <Img src={staticFile(adobeLogo)} style={{ height: 66 }} />
          <div style={{ fontSize: 50, fontWeight: 900, color: INK, marginTop: 26 }}>{plan}</div>
          <div style={{ display: "flex", alignItems: "center", marginTop: 34, gap: 20 }}>
            <div style={{ fontSize: 40, fontWeight: 800, color: off >= 1 ? SUB : INK }}>정기결제</div>
            <div style={{ marginLeft: "auto", width: 132, height: 72, borderRadius: 36, background: off >= 0.5 ? "#D5D8DE" : GREEN, position: "relative" }}>
              <div style={{ position: "absolute", top: 6, left: 6 + 60 * (1 - off), width: 60, height: 60, borderRadius: 30, background: "#fff", boxShadow: "0 2px 6px rgba(0,0,0,0.2)" }} />
            </div>
          </div>
          {off > 0.6 && <div style={{ position: "absolute", right: 40, top: 40, fontSize: 46, fontWeight: 900, color: RED, border: `6px solid ${RED}`, borderRadius: 16, padding: "4px 20px",
            transform: `rotate(-8deg) scale(${sp(beats.off + 0.2, { damping: 10, stiffness: 240 })})` }}>해지 완료</div>}
        </div>
      )}
 {/* 3) Gmail을 돋보기로 훑다가 발견 */}
      {t >= beats.mail && (
        <div style={{ position: "absolute", left: 70, right: 70, top: 30, height: 470, ...card2, padding: "26px 34px", overflow: "hidden", opacity: ml, transform: `translateY(${(1 - ml) * 80}px)` }}>
          <div style={{ display: "flex", alignItems: "center", gap: 14, fontSize: 40, fontWeight: 900, color: INK }}>
            <span style={{ fontSize: 44 }}>✉️</span> Gmail
            <span style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 10, fontSize: 28, fontWeight: 800, color: BLUE, background: "#EEF1FF", padding: "8px 18px", borderRadius: 24 }}>
              <Img src={staticFile(avatar)} style={{ width: 40, height: 40, borderRadius: 20, objectFit: "cover", background: "#fff" }} />{agent}가 혼자 찾는 중</span>
          </div>
          <div style={{ position: "absolute", left: 34, right: 34, top: 110 }}>
            {mails.map((m, i) => {
              const passed = scan * mails.length > i + 0.5;
              const hit = m.hit && t >= beats.found;
              return (
                <div key={i} style={{ display: "flex", alignItems: "center", gap: 18, height: rowH, borderBottom: "2px solid #EEF0F3", padding: "0 12px",
                  background: hit ? "rgba(236,29,29,0.08)" : "transparent", outline: hit ? `5px solid ${RED}` : "none", borderRadius: hit ? 16 : 0, transform: hit ? `scale(${1 + 0.03 * fd})` : undefined }}>
                  <div style={{ width: 54, height: 54, borderRadius: 27, background: m.from ? "#FA0F00" : "#D5D8DE", color: "#fff", fontSize: 26, fontWeight: 900, display: "flex", alignItems: "center", justifyContent: "center" }}>{m.from.slice(0, 1)}</div>
                  {m.from ? <div style={{ flex: 1, fontSize: m.hit ? 40 : 34, fontWeight: m.hit ? 900 : 700, color: m.hit ? INK : SUB }}>{m.from} · {m.subject}</div>
                    : <div style={{ flex: 1 }}><div style={{ width: 420, height: 22, borderRadius: 11, background: "#DDE0E5", filter: "blur(2px)" }} /></div>}
                  {passed && !hit && <div style={{ fontSize: 34, fontWeight: 900, color: GREEN }}>✓</div>}
                  {hit && <div style={{ fontSize: 34, fontWeight: 900, color: "#fff", background: RED, borderRadius: 20, padding: "4px 16px", transform: `scale(${fd})` }}>{found}</div>}
                </div>
              );
            })}
          </div>
          {t >= beats.scan && t < beats.found + 0.4 && (
            <div style={{ position: "absolute", left: 560 + Math.sin((t - beats.scan) * 4) * 200, top: (hitI >= 0 && t >= beats.found ? 110 + (hitI + 0.5) * rowH : lensY) - 70, fontSize: 130,
              filter: "drop-shadow(0 8px 12px rgba(0,0,0,0.25))", transform: "rotate(-15deg)" }}>🔍</div>
          )}
        </div>
      )}
    </Band>
  );
};

// ⑩ 실제 메시지를 크게 확대해 왼쪽 → 오른쪽으로 천천히 지나가며 형광펜
export const KiwiPan: React.FC<{ img: string; imgW: number; imgH: number; zoom: number; cy: number; x0: number; x1: number; marks: { at: number; boxes: Box[] }[] }> = ({ img, imgW, imgH, zoom, cy, x0, x1, marks }) => {
  const { t, sp, lin } = useT();
  const { durationInFrames, fps } = useVideoConfig();
  const dur = durationInFrames / fps;
  const s = (1080 / imgW) * zoom;
  const cx = x0 + (x1 - x0) * ease(lin(0, dur));
  const enter = sp(0, { damping: 18, stiffness: 180 });
  return (
    <Band fill>
      <div style={{ position: "absolute", left: 540 - cx * s, top: 250 - cy * s, width: imgW * s, height: imgH * s, opacity: enter }}>
        <Img src={staticFile(img)} style={{ width: "100%", height: "100%" }} />
        {marks.map((m, i) => t >= m.at && m.boxes.map((bx, j) => {
          const p = lin(m.at + j * 0.35, m.at + j * 0.35 + 0.45);
          return <div key={`${i}-${j}`} style={{ position: "absolute", left: bx.x * s, top: bx.y * s, width: bx.w * s * p, height: bx.h * s, background: HL, mixBlendMode: "multiply", borderRadius: 8 }} />;
        }))}
      </div>
    </Band>
  );
};

// ⑪ AI 로봇이 내 영상 위에 톡 나타나 먼저 말을 건다(투명, 인물 위 —)
export const RobotTalk: React.FC<{ robot: string; talk: string; talkAt: number; who?: string; avatar?: string }> = ({ robot, talk, talkAt, who, avatar }) => {
  const { t, sp } = useT();
  const r = sp(0, { damping: 11, stiffness: 200 });
  const b = sp(talkAt, { damping: 13, stiffness: 220 });
  const bob = Math.sin(t * 3) * 6;
  return (
    <AbsoluteFill style={{ fontFamily: FONT }}>
      <div style={{ position: "absolute", left: 40, top: BAND.top + 150 + bob, width: 250, opacity: r, transform: `translateY(${(1 - r) * 120}px) scale(${0.6 + 0.4 * r}) rotate(${(1 - r) * -12}deg)`,
        filter: "drop-shadow(0 12px 18px rgba(0,0,0,0.45))" }}>
        <Img src={staticFile(robot)} style={{ width: "100%" }} />
      </div>
      {t >= talkAt && (
        <div style={{ position: "absolute", left: 250, top: BAND.top + 40, maxWidth: 560, background: "#fff", borderRadius: 34, borderBottomLeftRadius: 8, padding: "22px 30px",
          boxShadow: "0 16px 40px rgba(0,0,0,0.4)", opacity: b, transform: `scale(${0.6 + 0.4 * b})`, transformOrigin: "0% 100%" }}>
          {who && <div style={{ display: "flex", alignItems: "center", gap: 10, fontSize: 28, fontWeight: 800, color: SUB, marginBottom: 6 }}>
            {avatar && <Img src={staticFile(avatar)} style={{ width: 40, height: 40, borderRadius: 20, objectFit: "cover" }} />}{who} · 지금</div>}
          <div style={{ fontSize: 50, fontWeight: 900, color: INK, lineHeight: 1.2 }}>{talk}</div>
        </div>
      )}
    </AbsoluteFill>
  );
};

// ⑫ 내 영상 위에 메시지 입력 말풍선(한 글자씩 → 전송) — "햇반 떨어졌어. 장 좀 봐줘"
export const MsgTyping: React.FC<{ text: string; to?: string; sendAt: number }> = ({ text, to, sendAt }) => {
  const { t, sp, f } = useT();
  const p = sp(0, { damping: 15, stiffness: 220 });
  const sent = t >= sendAt;
  const n = Math.floor(Math.min(1, t / Math.max(0.4, sendAt - 0.15)) * text.length);
  const up = sp(sendAt, { damping: 15, stiffness: 200 });
  return (
    <AbsoluteFill style={{ fontFamily: FONT }}>
      <div style={{ position: "absolute", left: 90, right: 90, top: BAND.top + 40, opacity: p, transform: `translateY(${(1 - p) * 40}px)` }}>
        {to && <div style={{ fontSize: 28, fontWeight: 800, color: "#fff", textShadow: "0 2px 6px rgba(0,0,0,0.6)", marginBottom: 10 }}>{to}</div>}
        {sent ? (
          <div style={{ display: "flex", justifyContent: "flex-end" }}>
            <div style={{ background: BLUE, color: "#fff", fontSize: 54, fontWeight: 900, padding: "20px 32px", borderRadius: 36, borderBottomRightRadius: 8,
              boxShadow: "0 14px 34px rgba(0,0,0,0.35)", transform: `translateY(${(1 - up) * 50}px)` }}>{text}</div>
          </div>
        ) : (
          <div style={{ display: "flex", alignItems: "center", gap: 14, background: "#fff", borderRadius: 44, padding: "16px 18px 16px 34px", boxShadow: "0 14px 34px rgba(0,0,0,0.35)" }}>
            <div style={{ flex: 1, fontSize: 48, fontWeight: 800, color: INK }}>{text.slice(0, n)}<span style={{ opacity: Math.floor(f / 8) % 2 ? 0 : 1, color: BLUE }}>|</span></div>
            <div style={{ width: 70, height: 70, borderRadius: 35, background: n >= text.length ? BLUE : "#C9CED6", color: "#fff", fontSize: 38, fontWeight: 900,
              display: "flex", alignItems: "center", justifyContent: "center" }}>↑</div>
          </div>
        )}
      </div>
    </AbsoluteFill>
  );
};

// ⑬ 🤖 로봇 이모지가 내 영상 왼쪽 가운데에 팝 → 좌우로 흔들리며 말풍선
export const RobotEmojiTalk: React.FC<{ talk: string; talkAt: number }> = ({ talk, talkAt }) => {
  const { t, sp } = useT();
  const r = sp(0, { damping: 9, stiffness: 240 });
  const sway = r > 0.9 ? Math.sin(t * 6) * 14 : 0;
  const b = sp(talkAt, { damping: 13, stiffness: 220 });
  return (
    <AbsoluteFill style={{ fontFamily: FONT }}>
      <div style={{ position: "absolute", left: 50 + sway, top: BAND.top + 250, fontSize: 210, lineHeight: 1, transform: `scale(${r}) rotate(${sway * 0.6}deg)`,
        filter: "drop-shadow(0 12px 18px rgba(0,0,0,0.45))" }}>🤖</div>
      {t >= talkAt && (
        <div style={{ position: "absolute", left: 230, top: BAND.top + 80, maxWidth: 620, background: "#fff", borderRadius: 36, borderBottomLeftRadius: 8, padding: "22px 30px",
          boxShadow: "0 16px 40px rgba(0,0,0,0.4)", opacity: b, transform: `scale(${0.6 + 0.4 * b})`, transformOrigin: "0% 100%" }}>
          <div style={{ fontSize: 50, fontWeight: 900, color: INK, lineHeight: 1.22, whiteSpace: "pre-line", wordBreak: "keep-all" }}>{talk}</div>
        </div>
      )}
    </AbsoluteFill>
  );
};

// ⑭ 날개 달린 돈(💸)이 날아가며 사라짐 ("돈이 나갈 거를 막아준" 자리)
export const FlyingMoney: React.FC<{ n?: number }> = ({ n = 5 }) => {
  const { t } = useT();
  return (
    <AbsoluteFill>
      {Array.from({ length: n }).map((_, i) => {
        const st = i * 0.12, k = Math.max(0, Math.min(1, (t - st) / 1.3));
        if (t < st) return null;
        const x0 = 380 + ((i * 97) % 320), y0 = BAND.top + 520;
        return <div key={i} style={{ position: "absolute", left: x0 + Math.sin(k * 6 + i) * 60 + k * (i % 2 ? 140 : -120), top: y0 - k * 520, fontSize: 120 - i * 8,
          opacity: k < 0.15 ? k / 0.15 : 1 - Math.max(0, (k - 0.5) / 0.5), transform: `rotate(${Math.sin(k * 8 + i) * 18}deg)` }}>💸</div>;
      })}
    </AbsoluteFill>
  );
};

// ⑮ 작은 표시 한 줄(통화 확대컷의 휴대폰 오른쪽 "AI가 전화로 말하는 중") — 띠 좌표 x·y
export const SideLabel: React.FC<{ text: string; x: number; y: number; size?: number }> = ({ text, x, y, size = 34 }) => {
  const { t, sp } = useT();
  const p = sp(0.1, { damping: 14, stiffness: 220 });
  return (
    <AbsoluteFill style={{ fontFamily: FONT }}>
      <div style={{ position: "absolute", left: x, top: BAND.top + y, display: "flex", alignItems: "center", gap: 10, background: "rgba(15,20,38,0.82)", color: "#fff",
        fontSize: size, fontWeight: 800, padding: "10px 20px", borderRadius: 30, opacity: p, transform: `translateX(${(1 - p) * -20}px)`, whiteSpace: "nowrap" }}>
        <span style={{ width: 14, height: 14, borderRadius: 7, background: "#FF3B30", opacity: 0.5 + 0.5 * Math.abs(Math.sin(t * 4)) }} />{text}
      </div>
    </AbsoluteFill>
  );
};
