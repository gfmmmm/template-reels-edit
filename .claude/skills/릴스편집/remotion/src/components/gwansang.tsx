// IMG_0517 "GPT로 관상 보는 법" 장면 3종 (레퍼런스 DeXsLq8O2Cy의 셀카→프롬프트창, 얼굴 스캔, 결과지 카메라 이동을 따라 하기)
// - SelfiePrompt: 찰칵 → 셀카 카드 → GPT 입력창으로 날아 들어가 첨부 사진이 됨 → 프롬프트 붙여 넣은 상태 → 전송
// - FaceScan: 인물 영상 위 투명 레이어. 얼굴 윤곽점(맥 Vision, 프레임마다)으로 그물망·이목구비 선·대칭선·라벨
// - ReportPan: 실제 결과 이미지 위로 카메라가 칸마다 확대·이동, 점수는 0에서 올라감
// 시간(beats)은 장면 시작부터의 초. 글·이미지·좌표는 props로(영상마다 바뀜). 카드는 기울이지 않는다(메뉴얼).
import React from "react";
import { AbsoluteFill, Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig, Easing } from "remotion";

const FONT = "'Apple SD Gothic Neo', Pretendard, sans-serif";
const MINT = "#8EF0C4";

const useT = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const t = f / fps;
  const sp = (at: number, cfg = { damping: 18, stiffness: 160 }) => (t < at ? 0 : spring({ frame: f - at * fps, fps, config: cfg }));
  const lin = (a: number, b: number, ease = false) =>
    interpolate(t, [a, b], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease ? Easing.inOut(Easing.cubic) : undefined });
  return { f, fps, t, sp, lin };
};

// ───────────────────────── 1) 셀카 → 프롬프트 입력창 ─────────────────────────
export const SelfiePrompt: React.FC<{
  selfie: string; greeting?: string; prompt: string; chip?: string;
  beats: { card: number; fly: number; paste: number; send: number };
}> = ({ selfie, greeting = "무엇을 도와드릴까요?", prompt, chip = "사진 1장", beats }) => {
  const { t, sp, lin } = useT();
  const flash = 1 - lin(0, 0.22);
  const cardIn = sp(beats.card, { damping: 13, stiffness: 190 });
  const fly = lin(beats.fly, beats.fly + 0.42, true);
  const ui = lin(beats.fly - 0.08, beats.fly + 0.12);
  const landed = t >= beats.fly + 0.42;
  const chipIn = sp(beats.fly + 0.4, { damping: 14, stiffness: 220 });
  const pasted = sp(beats.paste, { damping: 20, stiffness: 200 });
  const sent = t >= beats.send;
  const glow = sent ? 0.5 + 0.5 * Math.sin((t - beats.send) * 9) : 0;

 // 입력창 자리
  const BOX = { x: 60, y: 380, w: 960, h: 620 };
  const TH = { x: 100, y: 420, s: 190 };
 // 셀카 카드: 가운데(540, 700) 크기 640 → 입력창 썸네일
  const C0 = { cx: 540, cy: 700, s: 640 };
  const C1 = { cx: TH.x + TH.s / 2, cy: TH.y + TH.s / 2, s: TH.s };
  const cx = C0.cx + (C1.cx - C0.cx) * fly;
  const cy = C0.cy + (C1.cy - C0.cy) * fly - Math.sin(Math.PI * fly) * 90;
  const size = C0.s + (C1.s - C0.s) * fly;
  const border = 18 * (1 - fly);
  const radius = 14 + 10 * fly;
  const popScale = landed ? 1 : 0.7 + 0.3 * cardIn;

  return (
    <AbsoluteFill style={{ background: "#111", fontFamily: FONT, overflow: "hidden" }}>
 {/* 멈춰 보이지 않게 장면 전체가 천천히 다가간다 */}
     <AbsoluteFill style={{ transform: `scale(${1 + 0.015 * t})`, transformOrigin: "540px 730px" }}>
 {/* 흐린 셀카 바탕 */}
      <AbsoluteFill style={{ opacity: 1 - ui }}>
        <Img src={staticFile(selfie)} style={{ width: "100%", height: "100%", objectFit: "cover", filter: "blur(38px) brightness(0.55)", transform: "scale(1.2)" }} />
      </AbsoluteFill>
 {/* GPT 화면 */}
      <AbsoluteFill style={{ background: "#212121", opacity: ui }}>
        <div style={{ position: "absolute", top: 250, width: "100%", textAlign: "center", color: "#ECECEC", fontSize: 60, fontWeight: 600, letterSpacing: -1 }}>{greeting}</div>
        <div style={{
          position: "absolute", left: BOX.x, top: BOX.y, width: BOX.w, height: BOX.h, borderRadius: 48, background: "#303030",
          boxShadow: sent ? `0 0 ${30 + 30 * glow}px rgba(255,255,255,${0.12 + 0.12 * glow}), inset 0 0 0 2px rgba(255,255,255,${0.15 + 0.2 * glow})` : "inset 0 0 0 2px rgba(255,255,255,0.08)",
        }}>
 {/* 프롬프트 — 긴 프롬프트는 붙여 넣은 상태로 (메뉴얼: 타이핑 금지) */}
          <div style={{
            position: "absolute", left: 40, right: 40, top: TH.y - BOX.y + TH.s + 28, height: 250, overflow: "hidden",
            color: "#F1F1F1", fontSize: 34, lineHeight: 1.42, whiteSpace: "pre-wrap", opacity: pasted,
            transform: `translateY(${(1 - pasted) * 14}px)`,
            WebkitMaskImage: "linear-gradient(180deg, #000 55%, transparent 100%)", maskImage: "linear-gradient(180deg, #000 55%, transparent 100%)",
          }}>{prompt}</div>
          {pasted < 0.05 && (
            <div style={{ position: "absolute", left: 40, top: TH.y - BOX.y + TH.s + 28, color: "#8E8E8E", fontSize: 34, opacity: landed ? 1 : 0 }}>무엇이든 물어보세요</div>
          )}
 {/* 아래 줄: + · 사진 1장 · 전송 */}
          <div style={{ position: "absolute", left: 32, bottom: 30, display: "flex", gap: 16, alignItems: "center" }}>
            <div style={{ width: 68, height: 68, borderRadius: 34, border: "2px solid #555", color: "#DDD", fontSize: 44, display: "flex", alignItems: "center", justifyContent: "center" }}>+</div>
            <div style={{ height: 64, padding: "0 26px", borderRadius: 32, border: "2px solid #555", color: "#DDD", fontSize: 30, display: "flex", alignItems: "center", gap: 12, opacity: chipIn, transform: `scale(${0.6 + 0.4 * chipIn})` }}>
              <span style={{ width: 14, height: 14, borderRadius: 7, background: "#4ADE80", display: "inline-block" }} />{chip}
            </div>
          </div>
          <div style={{ position: "absolute", right: 32, bottom: 30, width: 76, height: 76, borderRadius: 38, background: pasted > 0.5 ? "#FFFFFF" : "#676767", display: "flex", alignItems: "center", justifyContent: "center" }}>
            {sent ? <div style={{ width: 24, height: 24, borderRadius: 4, background: "#111" }} /> : <div style={{ color: "#111", fontSize: 42, fontWeight: 900, marginTop: -4 }}>↑</div>}
          </div>
        </div>
      </AbsoluteFill>
 {/* 셀카 카드 (날아가는 중에도 같은 사진) */}
      <div style={{
        position: "absolute", left: cx - size / 2, top: cy - size / 2, width: size, height: size,
        transform: `scale(${popScale})`, opacity: t < beats.card ? 0 : 1,
        background: "#fff", padding: border, borderRadius: radius + border, boxSizing: "border-box",
        boxShadow: `0 ${30 - 20 * fly}px ${70 - 50 * fly}px rgba(0,0,0,${0.5 - 0.3 * fly})`,
      }}>
        <Img src={staticFile(selfie)} style={{ width: "100%", height: "100%", objectFit: "cover", borderRadius: radius, display: "block" }} />
      </div>
     </AbsoluteFill>
 {/* 찰칵 */}
      <AbsoluteFill style={{ background: "#fff", opacity: flash }} />
    </AbsoluteFill>
  );
};

// ───────────────────────── 2) 얼굴 스캔 (투명 레이어) ─────────────────────────
type Mesh = { frames: number[][][]; tris: number[][]; idx: Record<string, number[]>; box: number[][] };
export const FaceScan: React.FC<{
  mesh: Mesh; pill?: string;
  labels: { text: string; sub?: string; score?: number; at: number; side: "l" | "r"; anchor: string }[];
  beats: { scan: number; lines: number; sym: number };
}> = ({ mesh, pill = "GPT가 관상 분석 중", labels, beats }) => {
  const { f, t, sp, lin } = useT();
  const i = Math.min(mesh.frames.length - 1, f);
  const P = mesh.frames[i];
  const [bx0, by0, bx1, by1] = mesh.box[i];
  const pad = 46;
  const inn = sp(0, { damping: 15, stiffness: 200 });
 // 스캔 줄: 위→아래→위
  const sweep = lin(beats.scan, beats.scan + 1.5);
  const ph = sweep < 0.5 ? sweep * 2 : 2 - sweep * 2;
  const scanY = by0 + (by1 - by0) * ph;
  const reveal = sweep < 0.5 ? scanY : by1 + 10; // 처음 내려갈 때 지나간 곳까지만 그물망
  const meshOp = 0.55 * lin(beats.scan, beats.scan + 0.3);
  const lineOn = lin(beats.lines, beats.lines + 0.25);
  const symOn = lin(beats.sym, beats.sym + 0.3);
  const poly = (k: string, close = false) => {
    const pts = (mesh.idx[k] || []).map((j) => P[j]);
    if (!pts.length) return "";
    return pts.map((p, n) => `${n ? "L" : "M"}${p[0]},${p[1]}`).join(" ") + (close ? " Z" : "");
  };
  const ctr = (k: string) => {
    const pts = (mesh.idx[k] || []).map((j) => P[j]);
    return [pts.reduce((a, p) => a + p[0], 0) / pts.length, pts.reduce((a, p) => a + p[1], 0) / pts.length];
  };
  const le = ctr("leye"), re = ctr("reye"), lp = ctr("lips"), ns = ctr("nose");
  const midX = (le[0] + re[0]) / 2;
  const dots = ".".repeat(1 + (Math.floor(f / 7) % 3));
  const corner = (x: number, y: number, dx: number, dy: number) => (
    <path d={`M${x},${y + dy * 70} L${x},${y} L${x + dx * 70},${y}`} stroke="#fff" strokeWidth={6} fill="none" strokeLinecap="round" />
  );
  return (
    <AbsoluteFill style={{ fontFamily: FONT }}>
      <svg width={1080} height={1920} style={{ position: "absolute" }}>
        <defs>
          <clipPath id="rv"><rect x={0} y={0} width={1080} height={Math.max(0, reveal)} /></clipPath>
          <filter id="glow"><feGaussianBlur stdDeviation="5" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
        </defs>
 {/* 모서리 틀 */}
        <g opacity={inn} transform={`translate(${(bx0 + bx1) / 2},${(by0 + by1) / 2}) scale(${1.15 - 0.15 * inn}) translate(${-(bx0 + bx1) / 2},${-(by0 + by1) / 2})`}>
          {corner(bx0 - pad, by0 - pad, 1, 1)}{corner(bx1 + pad, by0 - pad, -1, 1)}
          {corner(bx0 - pad, by1 + pad, 1, -1)}{corner(bx1 + pad, by1 + pad, -1, -1)}
        </g>
 {/* 그물망 */}
        <g clipPath="url(#rv)" opacity={meshOp}>
          {mesh.tris.map(([a, b, c], n) => (
            <path key={n} d={`M${P[a][0]},${P[a][1]} L${P[b][0]},${P[b][1]} L${P[c][0]},${P[c][1]} Z`} stroke="#fff" strokeWidth={1.6} fill="none" />
          ))}
        </g>
 {/* 스캔 줄 */}
        {sweep > 0 && sweep < 1 && (
          <g filter="url(#glow)">
            <line x1={bx0 - pad} x2={bx1 + pad} y1={scanY} y2={scanY} stroke={MINT} strokeWidth={5} />
          </g>
        )}
 {/* 이목구비 선 */}
        <g opacity={lineOn} stroke="#fff" strokeWidth={4.5} fill="none" filter="url(#glow)" strokeLinejoin="round">
          <path d={poly("lbrow")} /><path d={poly("rbrow")} />
          <path d={poly("leye", true)} /><path d={poly("reye", true)} />
          <path d={poly("lips", true)} />
        </g>
 {/* 대칭선 */}
        <g opacity={symOn} stroke={MINT} strokeWidth={3.5} strokeDasharray="14 10" fill="none">
          <line x1={midX} x2={midX} y1={by0 - pad + (by1 - by0 + 2 * pad) * (1 - symOn)} y2={by1 + pad} />
          <line x1={le[0] - 30} x2={re[0] + 30} y1={(le[1] + re[1]) / 2} y2={(le[1] + re[1]) / 2} />
          <line x1={bx0} x2={bx1} y1={ns[1]} y2={ns[1]} />
        </g>
        <g opacity={symOn} fill={MINT}>
          {[le, re, lp, ns].map((p, n) => <circle key={n} cx={p[0]} cy={p[1]} r={9} />)}
        </g>
 {/* 라벨 연결선 */}
        {labels.map((lb, n) => {
          const on = sp(lb.at, { damping: 13, stiffness: 240 });
          const a = ctr(lb.anchor);
          const lx = lb.side === "l" ? 270 : 800;
          return on > 0 ? <line key={n} x1={a[0]} y1={a[1]} x2={lx} y2={a[1] - 40} stroke={MINT} strokeWidth={3} strokeDasharray="6 6" opacity={on} /> : null;
        })}
      </svg>
 {/* 위 알약 */}
      <div style={{
        position: "absolute", top: 250, left: "50%", transform: `translateX(-50%) scale(${0.8 + 0.2 * inn})`, opacity: inn,
        background: "rgba(20,20,20,0.82)", color: "#fff", fontSize: 44, fontWeight: 700, padding: "20px 40px", borderRadius: 60,
        display: "flex", alignItems: "center", gap: 18, whiteSpace: "nowrap", boxShadow: "0 10px 30px rgba(0,0,0,0.35)",
      }}>
        <span style={{ color: MINT, fontSize: 46, transform: `rotate(${t * 180}deg)`, display: "inline-block" }}>✳</span>
        <span>{pill}<span style={{ display: "inline-block", width: 50, textAlign: "left" }}>{dots}</span></span>
      </div>
 {/* 라벨 */}
      {labels.map((lb, n) => {
        const on = sp(lb.at, { damping: 13, stiffness: 240 });
        const a = ctr(lb.anchor);
        const style: React.CSSProperties = lb.side === "l" ? { right: 1080 - 270 } : { left: 800 };
        return (
          <div key={n} style={{
            position: "absolute", top: a[1] - 40 - 75, ...style, opacity: on, transform: `scale(${0.5 + 0.5 * on})`,
            transformOrigin: lb.side === "l" ? "right center" : "left center",
            background: "rgba(16,18,17,0.9)", border: `4px solid ${MINT}`, borderRadius: 22, padding: "12px 26px 14px",
            display: "flex", flexDirection: "column", alignItems: "center", whiteSpace: "nowrap", minWidth: 190,
          }}>
            <span style={{ color: MINT, fontSize: 38, fontWeight: 800 }}>{lb.text}</span>
            {lb.score != null && <span style={{ color: "#fff", fontSize: 76, fontWeight: 900, lineHeight: 1.05, fontFamily: "Menlo, monospace" }}>{Math.round(lb.score * Math.min(1, Math.max(0, (t - lb.at) / 0.45)))}</span>}
          </div>
        );
      })}
    </AbsoluteFill>
  );
};

// ───────────────────────── 3) 결과지 카메라 이동 ─────────────────────────
// img는 원본 비율 그대로(src 좌표 = 원본 px, srcW 기준). 화면 폭에 맞춘 것이 배율 1.
type Shot = { at: number; box?: [number, number, number, number]; zoom?: number; fy?: number };
export const ReportPan: React.FC<{
  img: string; srcW: number; srcH: number; shots: Shot[];
  counters?: { at: number; value: number; box: [number, number, number, number]; color: string; bg: string; size: number }[];
  focusY?: number; badge?: string; bandTop?: number;
}> = ({ img, srcW, srcH, shots, counters = [], focusY = 680, badge, bandTop = 1040 }) => {
  const { t, lin, sp } = useT();
  const base = 1080 / srcW;
 // 지금 카메라: 앞 샷 → 이 샷으로 0.3초 만에 옮겨 감(사용자 10/23: 느리면 말과 싱크가 안 맞음)
  const cam = (s: Shot) => {
    if (!s.box) return { z: s.zoom ?? 0.86, cx: srcW / 2, cy: srcH / 2, fy: 1050 };
    const [x0, y0, x1, y1] = s.box;
    const z = s.zoom ?? Math.min(2.2, 980 / ((x1 - x0) * base), 760 / ((y1 - y0) * base));
    return { z, cx: (x0 + x1) / 2, cy: (y0 + y1) / 2, fy: s.fy ?? focusY };
  };
  let cur = cam(shots[0]);
  for (let n = 1; n < shots.length; n++) {
    const p = lin(shots[n].at, shots[n].at + 0.3, true);
    if (p <= 0) break;
    const nx = cam(shots[n]);
    cur = { z: cur.z + (nx.z - cur.z) * p, cx: cur.cx + (nx.cx - cur.cx) * p, cy: cur.cy + (nx.cy - cur.cy) * p, fy: cur.fy + (nx.fy - cur.fy) * p };
  }
 // 멈춰 보이지 않게: 지금 샷이 머무는 동안 천천히 다가간다(초당 3%)
  const last = [...shots].reverse().find((x) => t >= x.at) ?? shots[0];
  cur = { ...cur, z: cur.z * (1 + 0.03 * Math.max(0, t - last.at)) };
 // 첫 등장: 살짝 크게 → 제자리
  const enter = sp(0, { damping: 20, stiffness: 120 });
  const s = base * cur.z * (1.06 - 0.06 * enter);
 // 이미지 밖(빈 바탕)이 보이지 않게 가둔다
  const tx = srcW * s <= 1080 ? (1080 - srcW * s) / 2 : Math.min(0, Math.max(1080 - srcW * s, 540 - cur.cx * s));
  const ty = cur.fy - cur.cy * s; // 가두지 않는다 — 제목이 위 220px에 걸리지 않고 아래 칸이 자막·버튼 자리에 오지 않게(빈 곳은 흐린 바탕)
 // 지금 보는 칸 밖은 어둡게
  const active = [...shots].reverse().find((x) => t >= x.at + 0.15);
  const dim = active?.box ? lin(active.at + 0.15, active.at + 0.3) : 0;
  return (
    <AbsoluteFill style={{ background: "#2a2018", overflow: "hidden" }}>
      <Img src={staticFile(img)} style={{ position: "absolute", width: "100%", height: "100%", objectFit: "cover", filter: "blur(40px) brightness(0.6)", transform: "scale(1.2)" }} />
      <div style={{ position: "absolute", left: 0, top: 0, width: srcW, height: srcH, transformOrigin: "0 0", transform: `translate(${tx}px, ${ty}px) scale(${s})`, boxShadow: "0 20px 60px rgba(0,0,0,0.5)" }}>
        <Img src={staticFile(img)} style={{ width: srcW, height: srcH, display: "block" }} />
        {counters.map((c, n) => {
          
          const v = Math.round(c.value * lin(c.at, c.at + 0.4, true));
          const pulse = sp(c.at + 0.4, { damping: 8, stiffness: 260 });
          const [x0, y0, x1, y1] = c.box;
          return (
            <div key={n} style={{ position: "absolute", left: x0, top: y0, width: x1 - x0, height: y1 - y0, background: c.bg, display: "flex", alignItems: "center", justifyContent: "flex-start" }}>
              <span style={{ fontFamily: "Georgia, 'Times New Roman', serif", fontWeight: 700, fontSize: c.size, color: c.color, lineHeight: 1, transform: `scale(${1 + 0.12 * Math.sin(Math.PI * pulse)})`, transformOrigin: "left center" }}>{v}</span>
            </div>
          );
        })}
        {active?.box && (
          <div style={{
            position: "absolute", left: active.box[0] - 4, top: active.box[1] - 4, width: active.box[2] - active.box[0] + 8, height: active.box[3] - active.box[1] + 8,
            borderRadius: 10, border: `${3 / (cur.z)}px solid rgba(244,199,15,${dim})`, boxShadow: `0 0 0 4000px rgba(0,0,0,${0.5 * dim})`,
          }} />
        )}
      </div>
 {/* 자막(세로 약 1,120px) 뒤 어두운 띠 — 종이 글씨와 분리 */}
      <div style={{ position: "absolute", left: 0, right: 0, top: bandTop, height: 170, background: "linear-gradient(180deg, rgba(0,0,0,0) 0%, rgba(0,0,0,0.55) 25%, rgba(0,0,0,0.55) 75%, rgba(0,0,0,0) 100%)" }} />
      {badge && (
        <div style={{ position: "absolute", top: bandTop + 195, left: 60, background: "#FFD43B", color: "#111", fontFamily: FONT, fontWeight: 800, fontSize: 34, padding: "10px 22px", borderRadius: 14 }}>{badge}</div>
      )}
    </AbsoluteFill>
  );
};
