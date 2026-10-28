// 릴스편집 자료화면 카드 — 색·글꼴·위치는 brand.ts 값만 쓴다.
// 모든 카드는 1080×1920 투명 배경, 인물 영상 위에 얹는다.
import React from "react";
import { AbsoluteFill, Img, interpolate, OffthreadVideo, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { broll, chapterCard, colors, fonts, safeZone } from "../brand";

// 상단 제목(세로 230~420px)이 있는 영상은 큰 카드를 그 아래부터 시작해야 제목에 가리지 않는다
const TITLE_BOTTOM = 425;

const pop = (frame: number, fps: number) =>
  spring({ frame, fps, durationInFrames: Math.round(broll.popInSec * fps * 2), config: { damping: 14, stiffness: 220 } });

// 1) 프롬프트 입력 화면 — 화면 위쪽(안전 영역 안)에 채팅 창, 실제 프롬프트가 타자 치듯 입력된다
// 글자가 작으면 휴대폰에서 못 읽는다 → 큰 글자로, 입력 중인 줄이 항상 보이게 아래 정렬. 말과 맞는 구절은 노란 형광펜.
const marked = (text: string, highlights: string[], on: boolean) => {
  if (!on || highlights.length === 0) return text;
  const parts: React.ReactNode[] = [];
  let rest = text;
  let k = 0;
  while (rest.length) {
    const hits = highlights.map((h) => [rest.indexOf(h), h] as const).filter(([i]) => i >= 0).sort((a, b) => a[0] - b[0]);
    if (!hits.length) { parts.push(rest); break; }
    const [i, h] = hits[0];
    parts.push(rest.slice(0, i));
    parts.push(<span key={k++} style={{ background: colors.yellow, borderRadius: 6, padding: "0 4px" }}>{h}</span>);
    rest = rest.slice(i + h.length);
  }
  return parts;
};

export const PromptCard: React.FC<{ title: string; prompt: string; highlights?: string[]; hlTimes?: number[]; showAfter?: "top" | "bottom"; typeUntil?: number }> = ({ title, prompt, highlights = [], hlTimes = [] }) => {
 // 프롬프트를 처음부터 다 타자 치면 정신없다(사용자 피드백) → 붙여 넣은 상태로 들어오고,
 // 말에 맞춰 형광펜이 하나씩 칠해진다(hlTimes: 카드 시작 기준 초). 형광펜이 칠해진 구절이 보이게 스크롤.
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const s = pop(frame, fps);
  const t = frame / fps;
  const on = highlights.filter((_, i) => t >= (hlTimes[i] ?? 0.4 + i * 0.6));
  const dots = ".".repeat(1 + (Math.floor(frame / 8) % 3));
  const lastOn = on[on.length - 1];
  const focus = lastOn ? prompt.indexOf(lastOn) / Math.max(1, prompt.length) : 0;
  const scroll = interpolate(focus, [0, 1], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill>
      <div style={{
        position: "absolute", left: safeZone.side, right: safeZone.side, top: TITLE_BOTTOM + 15, height: 545,
        background: colors.white, borderRadius: 34, boxShadow: "0 18px 50px rgba(0,0,0,0.35)",
        transform: `scale(${0.9 + 0.1 * s})`, opacity: s, overflow: "hidden", fontFamily: fonts.heading,
      }}>
        <div style={{ height: 70, background: "#F2F2F4", display: "flex", alignItems: "center", padding: "0 28px", gap: 12 }}>
          {["#FF5F57", "#FEBC2E", "#28C840"].map((c) => <div key={c} style={{ width: 18, height: 18, borderRadius: 9, background: c }} />)}
          <div style={{ marginLeft: 18, fontSize: 28, fontWeight: 700, color: "#333" }}>{title}</div>
        </div>
        <div style={{ position: "absolute", top: 70, left: 0, right: 0, bottom: 74, padding: "22px 28px", overflow: "hidden" }}>
          <div style={{
            background: "#ECECEE", borderRadius: 26, padding: "22px 26px", marginLeft: 60,
            fontSize: 38, lineHeight: 1.38, color: "#111", whiteSpace: "pre-wrap", fontWeight: 600,
            borderLeft: `8px solid ${colors.yellow}`, transform: `translateY(${-scroll * 55}%)`,
          }}>
            {marked(prompt, on, true)}
          </div>
        </div>
        <div style={{ position: "absolute", left: 30, bottom: 18, fontSize: 32, color: "#666", fontWeight: 700 }}>
          {t > durationInFrames / fps - 1.2 ? `Working${dots}` : "프롬프트 입력"}
        </div>
      </div>
    </AbsoluteFill>
  );
};

// 2) 번호 장 카드 — 번호를 매기는 영상에서만. 인물 위를 진회색으로 덮고 가운데 흰 글자
export const ChapterCard: React.FC<{ num: number; title: string }> = ({ num, title }) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const s = pop(frame, fps);
  const out = interpolate(frame, [durationInFrames - 3, durationInFrames], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ opacity: out }}>
 {/* 어두운 덮개만 반투명, 글자는 완전히 불투명 (사용자: 글자가 비쳐 보였다) */}
      <AbsoluteFill style={{ background: chapterCard.overlay, opacity: chapterCard.overlayOpacity }} />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <div style={{
          marginTop: -260, transform: `scale(${0.85 + 0.15 * s})`, textAlign: "center", fontFamily: fonts.heading,
          fontWeight: 900, color: colors.yellow, fontSize: 76, lineHeight: 1.25, maxWidth: 1000,
          WebkitTextStroke: "2px #000", textShadow: "0 4px 18px rgba(0,0,0,0.6)",
        }}>
          {num}. {title}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// 3) 아이콘 팝 — 자막 바로 아래 가슴 앞. 아이콘 여러 개면 가로로 나란히(합친 폭 650px 이하)
export const IconPop: React.FC<{ icons: string[]; labels?: string[] }> = ({ icons, labels }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const w = icons.length === 1 ? 330 : Math.min(broll.iconWidth.max, Math.floor(broll.maxWidth / icons.length) - 20);
  return (
    <AbsoluteFill>
      <div style={{ position: "absolute", top: broll.yRange.from + 20, left: 0, right: 0, display: "flex", justifyContent: "center", gap: 20 }}>
        {icons.map((src, i) => {
          const s = pop(frame - i * 4, fps);
          return (
            <div key={src} style={{ textAlign: "center", transform: `scale(${s})` }}>
              {labels?.[i] && <div style={{ fontFamily: fonts.heading, fontWeight: 900, fontSize: 44, color: colors.lime, WebkitTextStroke: "2px #000" }}>{labels[i]}</div>}
              <Img src={staticFile(src)} style={{ width: w, height: w, objectFit: "contain", filter: "drop-shadow(0 8px 14px rgba(0,0,0,0.35))" }} />
            </div>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};

// 4) 아래쪽 정보 카드 — 화면 아래쪽(자막 아래 ~ 화면 끝)을 덮는 흰 판. 소품이 튀는 구간을 가릴 때
export const BottomInfoCard: React.FC<{ steps: { icon: string; text: string; from: number }[] }> = ({ steps }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = pop(frame, fps);
  const cur = [...steps].reverse().find((st) => frame >= st.from * fps) ?? steps[0];
  const k = pop(frame - cur.from * fps, fps);
  return (
    <AbsoluteFill>
      <div style={{
        position: "absolute", left: 0, right: 0, top: 1185, bottom: 0, background: colors.white,
        borderTopLeftRadius: 44, borderTopRightRadius: 44, boxShadow: "0 -12px 40px rgba(0,0,0,0.3)",
        transform: `translateY(${(1 - s) * 300}px)`, fontFamily: fonts.heading,
      }}>
        <div style={{ position: "absolute", top: 40, height: 260, left: safeZone.side + 20, right: safeZone.rightButtons.width, display: "flex", alignItems: "center", justifyContent: "center", gap: 30, transform: `scale(${0.9 + 0.1 * k})` }}>
          <Img src={staticFile(cur.icon)} style={{ width: 210, height: 210, objectFit: "contain" }} />
          <div style={{ fontSize: 76, fontWeight: 900, color: colors.dark, lineHeight: 1.15, whiteSpace: "pre-line" }}>{cur.text}</div>
        </div>
      </div>
    </AbsoluteFill>
  );
};

// 5) 화면녹화 전체 화면 — 진회색 바탕 가운데에 둥근 모서리로. 위 가림 영역 아래부터 시작
export const ScreenRecCard: React.FC<{ src: string; width?: number }> = ({ src, width = 860 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const s = pop(frame, fps);
  return (
    <AbsoluteFill style={{ background: colors.dark, opacity: Math.min(1, s * 1.5) }}>
      <div style={{
        position: "absolute", top: TITLE_BOTTOM + 15, left: (1080 - width) / 2, width,
        borderRadius: 34, overflow: "hidden", boxShadow: "0 18px 50px rgba(0,0,0,0.5)",
        transform: `scale(${0.92 + 0.08 * s})`,
      }}>
        <OffthreadVideo src={staticFile(src)} muted style={{ width: "100%", display: "block" }} />
      </div>
    </AbsoluteFill>
  );
};
