// 검수용 확인본 전용: CapCut 자막·상단 제목을 비슷하게 그린 투명 레이어 (최종본에는 쓰지 않는다)
import React from "react";
import { AbsoluteFill, continueRender, delayRender, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { colors, fonts } from "../brand";

const handle = delayRender("font");
Promise.all([
  new FontFace(fonts.caption, `url(${staticFile(fonts.captionFile)})`).load(),
  new FontFace("DoHyeon", `url(${staticFile("fonts/cand/6808056385679397389.ttf")})`).load(),
]).then((fs) => { fs.forEach((f) => document.fonts.add(f)); continueRender(handle); });

// 메모·리액션 글자마다 다른 글꼴(계정마다 다름) — overlay_props 의 fontFiles {"글꼴 이름": "fonts/파일.ttf"} 를 불러온다
const useExtraFonts = (files?: Record<string, string>) => {
  const [h] = React.useState(() => (files && Object.keys(files).length ? delayRender("extra-fonts") : null));
  React.useEffect(() => {
    if (h === null || !files) return;
    Promise.all(Object.entries(files).map(([fam, f]) => new FontFace(fam, `url(${staticFile(f)})`).load()))
      .then((fs) => { fs.forEach((f) => document.fonts.add(f)); continueRender(h); })
      .catch(() => continueRender(h));
  }, [h, files]);
};

type Cap = { start: number; end: number; text: string; color: string; ranges?: number[][]; big?: boolean; hidden?: boolean };
// 이모지·라벨·메모 (CapCut 글자 조각). x·y는 CapCut 좌표(-1~1, y는 위가 +), size는 자막 대비 배율
type Ov = { kind: string; text: string; start: number; end: number; x: number; y: number; size?: number; color?: string; font?: string; still?: boolean; tpl?: string; type?: number };
const C: Record<string, string> = { white: colors.white, yellow: colors.yellow, red: colors.red };
const txt = (color: string, size: number): React.CSSProperties => ({
  fontFamily: fonts.caption, fontWeight: 700, fontSize: size, color, textAlign: "center", lineHeight: 1.15,
  WebkitTextStroke: "4px #000", paintOrder: "stroke fill", textShadow: "0 0 18px rgba(0,0,0,0.95), 0 0 34px rgba(0,0,0,0.8)", whiteSpace: "pre",
});

// 부분 칠하기: ranges = [[시작 글자, 끝 글자(포함 안 함)], ...] 노랑
const Colored: React.FC<{ c: Cap }> = ({ c }) => {
  if (!c.ranges || !c.ranges.length) return <>{c.text}</>;
  const out: React.ReactNode[] = [];
  let k = 0;
  c.ranges.forEach(([a, b], i) => {
    if (a > k) out.push(<span key={`w${i}`}>{c.text.slice(k, a)}</span>);
    out.push(<span key={`y${i}`} style={{ color: colors.yellow }}>{c.text.slice(a, b)}</span>);
    k = b;
  });
  if (k < c.text.length) out.push(<span key="end">{c.text.slice(k)}</span>);
  return <>{out}</>;
};

// CapCut "흔들림"(Jiggle) 흉내: 0.2초마다 몇 px씩 툭툭
const jig = (t: number, seed: number) => {
  const k = Math.floor(t / 0.2) + seed * 7;
  return { dx: ((k * 37) % 9) - 4, dy: ((k * 53) % 9) - 4, r: ((k * 29) % 7) - 3 };
};

export const CaptionOverlay: React.FC<{ captions: Cap[]; overlays?: Ov[]; title?: string; titleDur?: number; titleFirstWhite?: boolean; titleSize?: number; titleTop?: number; captionTop?: number; titleColor?: string; titleFont?: string; bigSize?: number; bigTop?: number; memoColor?: string; fontFiles?: Record<string, string>; captionSize?: number }> = ({ captions, overlays = [], title, titleDur = 3, titleFirstWhite = true, titleSize = 150, titleTop = 170, captionTop, titleColor, titleFont, bigSize, bigTop, memoColor, fontFiles, captionSize = 84 }) => {
  useExtraFonts(fontFiles);
  const t = useCurrentFrame() / useVideoConfig().fps;
  const cur = captions.find((c) => t >= c.start && t < c.end && !c.hidden);
  return (
    <AbsoluteFill>
      {title && t < titleDur && <div style={{ position: "absolute", top: titleTop, left: 0, right: 0, ...txt(colors.yellow, titleSize), fontFamily: "DoHyeon", fontWeight: 400, lineHeight: 1.08, WebkitTextStroke: "4px #000", textShadow: "0 0 24px rgba(0,0,0,0.95), 0 0 48px rgba(0,0,0,0.85)" }}>
        {title.split("\n").map((l, k, a) => <div key={k} style={{ color: titleColor ?? (titleFirstWhite && a.length > 1 && k === 0 ? colors.white : colors.yellow), ...(titleFont ? { fontFamily: titleFont, fontWeight: 800 } : {}) }}>{l}</div>)}</div>}
 {/* 크게 자막의 크기·위치는 계정마다 다르다(자막_크게 템플릿) — overlay_props 의 bigSize·bigTop 으로 CapCut 과 같게. 없으면 예전 값(2배, 자막 줄) */}
      {cur && <div style={{ position: "absolute", top: (cur.big ? (bigTop ?? (captionTop ?? 1120) - 90) : (captionTop ?? 1120) - 45) + ((cur as any).dy ?? 0), left: 0, right: 0, ...txt(C[cur.color], cur.big ? (bigSize ?? captionSize * 2) : captionSize) }}><Colored c={cur} /></div>}
      {overlays.filter((o) => t >= o.start && t < o.end).map((o, i) => {
        if (o.kind === "tag") // 이름표: 파란 상자 + 흰 글자 (레퍼런스 후기 영상)
          return <div key={i} style={{ position: "absolute", left: 0, right: 0, top: 960 - o.y * 960 - 30, textAlign: "center" }}>
            <span style={{ background: "#1C8BE0", color: "#fff", fontFamily: fonts.caption, fontWeight: 700, fontSize: 40, padding: "4px 14px", borderRadius: 6 }}>{o.text}</span></div>;
        const j = o.kind === "memo" || o.still ? { dx: 0, dy: 0, r: 0 } : jig(t, i);
        const size = o.kind === "emoji" ? 150 * (o.size ?? 1) : 84 * (o.size ?? 1);
        const cx = 540 + o.x * 540 + j.dx, cy = 960 - o.y * 960 + j.dy;
 // 타자 움직임: "type"(글자당 초) 또는 끝 문구 틀(tpl "끝문구…") — CapCut 타자 애니메이션처럼 한 글자씩. 남은 글자는 투명으로 자리를 지켜
 // 글이 가운데서 흔들리지 않게 한다(블라인드 시험: 확인본은 끝 문구가 처음부터 다 떠 있어 CapCut 실물과 달랐다)
        const chars = [...o.text];
        const per = o.type ?? (o.tpl?.startsWith("끝문구") ? Math.min(0.08, 1.0 / Math.max(1, chars.length)) : 0);
        const nShow = per ? Math.max(1, Math.floor((t - o.start) / per) + 1) : chars.length;
        const body = nShow >= chars.length ? o.text : <>{chars.slice(0, nShow).join("")}<span style={{ opacity: 0 }}>{chars.slice(nShow).join("")}</span></>;
        return <div key={i} style={{ position: "absolute", left: cx - 500, width: 1000, top: cy - size * 0.6,
          transform: `rotate(${j.r}deg)`, ...txt(o.color ?? (o.kind === "label" ? colors.white : o.kind === "memo" ? (memoColor ?? colors.yellow) : colors.yellow), size), ...(o.font ? { fontFamily: o.font } : {}),
          ...(o.kind === "emoji" ? { WebkitTextStroke: "0", textShadow: "none", filter: "drop-shadow(0 6px 10px rgba(0,0,0,0.7))", fontFamily: "Apple Color Emoji" } : {}) }}>{body}</div>;
      })}
    </AbsoluteFill>
  );
};
