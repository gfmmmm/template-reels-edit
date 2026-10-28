// 모션그래픽 장면 (사용자 참고 릴스 DeDSuo4E-Km 톤): 연한 회색 바탕 + 그림자 부드러운 흰 둥근 카드 + 단순화한 앱 화면 + 파랑 포인트.
// 화면 전체를 덮는 1~3초짜리 삽입 장면. 아래 자막 자리(세로 1,050~1,200px)는 비워 둔다(CapCut 자막이 얹힌다).
import React from "react";
import { AbsoluteFill, Img, OffthreadVideo, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";

const BG = "#F3F4F6";
const BLUE = "#3B5BFD";
const INK = "#1F2329";
const SUB = "#9AA0A6";
const FONT = "'Apple SD Gothic Neo', Pretendard, sans-serif";
const card: React.CSSProperties = {
  background: "#fff", borderRadius: 36, boxShadow: "0 18px 50px rgba(20,30,60,0.10), 0 2px 8px rgba(20,30,60,0.06)",
};

// 인물 아래 창 (사용자 제안: 모션그래픽만 나올 때 내 모습을 아래에, 참고보다 조금 작게) + 입체감:
// 창 안에는 원래 영상, 그 위 같은 자리에 오려낸 인물(Vision 마스크, scripts/person_matte.swift)을 겹쳐 머리가 창 위로 튀어나온다.
// 머리 꼭대기는 자막(세로 약 1,165px까지) 아래에서 멈추게 창 위치를 잡는다. pip: public 안 영상, 오려낸 판은 같은 이름 _cut.mov
// 기본 위치(공용 규칙 IMG_0519 검수): 창 폭 486px(가로 297~783), 위끝 1,240px, 영상을 -212px 올려
// 머리 꼭대기 약 1,180px(자막 아래)·눈 약 1,340~1,470px — 얼굴이 아래 420px 띠(1,500px 아래)와 오른쪽 버튼 칸(865px 넘음)에 안 걸린다.
// 예전 기본(폭 780·위끝 1,400·-380)은 얼굴이 1,600px 안팎이라 인스타 캡션에 가렸다. 옛 크기가 필요하면 side 150·vidTop -380.
export const PersonPip: React.FC<{ pip: string; enter: number; top?: number; side?: number; vidTop?: number }> = ({ pip, enter, top = 1240, side = 297, vidTop = -212 }) => {
  const box: React.CSSProperties = { position: "absolute", left: side, right: side, top, bottom: -40 };
  const vid: React.CSSProperties = { position: "absolute", width: "100%", top: vidTop };
  const anim = { transform: `translateY(${(1 - enter) * 80}px)`, opacity: enter };
  return (
    <>
      <div style={{ ...box, ...anim, borderRadius: 44, overflow: "hidden", boxShadow: "0 18px 50px rgba(20,30,60,0.18)" }}>
        <OffthreadVideo src={staticFile(pip)} muted style={vid} />
      </div>
      <div style={{ ...box, ...anim, overflow: "visible", filter: "drop-shadow(0 10px 18px rgba(20,30,60,0.25))" }}>
        <OffthreadVideo src={staticFile(pip.replace(/\.mp4$/, "_cut.mov"))} muted transparent style={vid} />
      </div>
    </>
  );
};

/**
 * 프롬프트 입력 → 전송 → AI가 계정을 분석하는 장면.
 * prompt: 실제 프롬프트 첫 줄(지어내지 않는다), sendAt: 전송 프레임,
 * tool: 쓴 AI 이름(예: Aside), account: 분석 대상 계정
 */
export const PromptScene: React.FC<{ prompt: string; tool: string; account?: string; sendAt?: number; flowAt?: number; pip?: string; scanAt?: number; scanTotal?: number; marks?: string[] }> = ({
  prompt, tool, sendAt = 10, pip, scanAt, scanTotal = 30, marks = [],
}) => {
 // 타이핑 연출은 쓰지 않는다 — 한 문장만 쓰고 보내는 것처럼 보여 "한 줄이면 되는구나" 오해를 산다(사용자).
 // 전체 프롬프트가 붙여 넣어진 상태로 바로 뜨고, 전송 버튼이 눌린 뒤 말풍선으로 올라가 천천히 아래로 훑는다.
  const f = useCurrentFrame();
  const { fps, durationInFrames } = useVideoConfig();
  const enter = spring({ frame: f, fps, config: { damping: 22, stiffness: 300 } });
  const sent = f >= sendAt;
  const press = f >= sendAt - 3 && f < sendAt + 3 ? 0.85 : 1;
  const bubble = spring({ frame: f - sendAt, fps, config: { damping: 18, stiffness: 170 } });
  const scroll = interpolate(f, [sendAt + 10, durationInFrames], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const [first, ...rest] = prompt.split("\n");
  const scanF = scanAt === undefined ? 1e9 : scanAt * fps;
  const back = spring({ frame: f - scanF, fps, config: { damping: 20, stiffness: 150 } }) * (f >= scanF ? 1 : 0);
  const H = 560; // 말풍선 보이는 높이

  return (
    <AbsoluteFill style={{ background: BG, fontFamily: FONT }}>
      <div style={{ position: "absolute", left: 70, right: 70, top: 250, height: 790, ...card, padding: 36,
        transform: `translateY(${(1 - enter) * 60 - back * 40}px) scale(${(0.96 + 0.04 * enter) * (1 - 0.1 * back)})`, opacity: enter * (1 - 0.6 * back),
        filter: `blur(${back * 3}px)` }}>
        <div style={{ display: "flex", alignItems: "center", gap: 14 }}>
          <div style={{ width: 34, height: 34, borderRadius: 10, background: INK, color: "#fff", fontSize: 20, fontWeight: 900, display: "flex", alignItems: "center", justifyContent: "center" }}>A</div>
          <div style={{ fontSize: 30, fontWeight: 800, color: INK }}>{tool}</div>
          <div style={{ marginLeft: "auto", fontSize: 22, fontWeight: 700, color: BLUE, background: "#EEF1FF", padding: "8px 18px", borderRadius: 20 }}>Opus 5</div>
        </div>
 {/* 붙여 넣은 전체 프롬프트: 처음엔 입력창 자리에 펼쳐져 있다가 전송되면 위 말풍선으로 */}
 {/* 말풍선 높이는 글 길이에 맞춘다(사용자: 아래 빈 공간이 길다). 넘칠 때만 넘친 만큼 천천히 내린다 */}
        <div style={{ position: "absolute", left: 36, right: 36, top: sent ? 92 : 140, maxHeight: H, overflow: "hidden",
          transform: sent ? `translateY(${(1 - bubble) * 60}px)` : undefined,
          background: sent ? "#EEF1FF" : "#F6F7F9", border: sent ? "none" : "2px solid #E6E8EC", borderRadius: 28, borderTopRightRadius: sent ? 8 : 28 }}>
          <div style={{ padding: "26px 30px 70px", color: INK, transform: `translateY(calc(${-scroll} * max(0px, 100% - ${H}px)))` }}>
            <div style={{ fontSize: 36, fontWeight: 900, lineHeight: 1.35 }}>{first}</div>
            <div style={{ fontSize: 25, fontWeight: 600, lineHeight: 1.6, marginTop: 12, color: "#3A3F47", whiteSpace: "pre-wrap" }}>
 {/* 프롬프트 원문 속 핵심 조건(숫자·대상)을 굵게 + 노란 형광펜 */}
              {marks.length ? rest.join("\n").trim().split(new RegExp(`(${marks.map((m) => m.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|")})`)).map((part, i) =>
                marks.includes(part) ? <b key={i} style={{ color: INK, fontSize: 30, background: "rgba(255,212,0,0.55)", borderRadius: 6, padding: "0 4px" }}>{part}</b> : <span key={i} style={{ opacity: 0.4 }}>{part}</span>) : rest.join("\n").trim()}
            </div>
          </div>
        </div>
 {/* 입력창 + 전송 */}
        <div style={{ position: "absolute", left: 28, right: 28, bottom: 28, height: 88, borderRadius: 44, background: "#F6F7F9", border: "2px solid #E6E8EC",
          display: "flex", alignItems: "center", padding: "0 18px 0 32px" }}>
          <div style={{ fontSize: 30, fontWeight: 700, color: SUB, flex: 1 }}>{sent ? "Working…" : "메시지 입력"}</div>
          <div style={{ width: 60, height: 60, borderRadius: "50%", background: sent ? "#C9CED6" : BLUE, color: "#fff", fontSize: 30, fontWeight: 900,
            display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${press})` }}>↑</div>
        </div>
      </div>


 {/* AI가 내 계정을 훑는다(사용자 승인 A안): 내 프로필 카드 + 실제 릴스 썸네일 격자, 파란 스캔 줄이 내려가며 ✓가 켜지고 진행 숫자가 오른다 */}
      {f >= scanF && (() => {
        const sf = f - scanF;
        const left = durationInFrames - scanF;
        const inn = spring({ frame: sf, fps, config: { damping: 17, stiffness: 160 } });
        const prog = interpolate(sf, [4, left - 6], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
        const gridTop = 190, rowH = 172, rows = 3;
        const lineY = gridTop + prog * rows * rowH;
        return (
          <div style={{ position: "absolute", left: 90, right: 90, top: 300, height: 740, ...card, overflow: "hidden", padding: "28px 32px",
            opacity: inn, transform: `translateY(${(1 - inn) * 80}px) scale(${0.95 + 0.05 * inn})` }}>
            <div style={{ display: "flex", alignItems: "center", gap: 18 }}>
              <div style={{ width: 84, height: 84, borderRadius: 42, padding: 4, background: "linear-gradient(45deg,#FEDA75,#FA7E1E,#D62976,#962FBF)" }}>
                <Img src={staticFile("images/myfeed/avatar.jpg")} style={{ width: 76, height: 76, borderRadius: 38, objectFit: "cover", border: "3px solid #fff" }} />
              </div>
              <div>
                <div style={{ fontSize: 32, fontWeight: 900, color: INK }}>@my_account</div>
                <div style={{ fontSize: 22, fontWeight: 700, color: BLUE, marginTop: 4 }}>{tool}가 분석 중</div>
              </div>
            </div>
 {/* 진행 */}
            <div style={{ marginTop: 22 }}>
              <div style={{ display: "flex", justifyContent: "space-between", fontSize: 26, fontWeight: 800, color: INK }}>
                <span>최근 콘텐츠 {scanTotal}개 읽는 중</span>
                <span style={{ color: BLUE }}>{Math.round(prog * scanTotal)}/{scanTotal}</span>
              </div>
              <div style={{ height: 12, borderRadius: 6, background: "#E8EBF2", marginTop: 10 }}>
                <div style={{ width: `${prog * 100}%`, height: 12, borderRadius: 6, background: BLUE }} />
              </div>
            </div>
 {/* 릴스 격자 */}
            <div style={{ position: "absolute", left: 32, right: 32, top: gridTop, display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 10 }}>
              {Array.from({ length: 12 }).map((_, i) => {
                const rowMid = gridTop + (Math.floor(i / 4) + 0.5) * rowH;
                const done = lineY > rowMid + (i % 4) * 12;
                const pop = done ? Math.min(1, (lineY - rowMid) / 60) : 0;
                return (
                  <div key={i} style={{ position: "relative", height: rowH - 10, borderRadius: 12, overflow: "hidden" }}>
                    <Img src={staticFile(`images/myfeed/${i + 1}.jpg`)} style={{ width: "100%", height: "100%", objectFit: "cover", filter: done ? "none" : "saturate(0.6) brightness(0.95)" }} />
                    {done && <div style={{ position: "absolute", inset: 0, background: "rgba(47,85,212,0.18)" }} />}
                    {done && <div style={{ position: "absolute", right: 8, top: 8, width: 38, height: 38, borderRadius: 19, background: BLUE, color: "#fff", fontSize: 24, fontWeight: 900,
                      display: "flex", alignItems: "center", justifyContent: "center", transform: `scale(${pop})` }}>✓</div>}
                  </div>
                );
              })}
            </div>
 {/* 스캔 줄 */}
            <div style={{ position: "absolute", left: 0, right: 0, top: lineY - 60, height: 60, background: "linear-gradient(transparent, rgba(59,91,253,0.25))" }} />
            <div style={{ position: "absolute", left: 0, right: 0, top: lineY, height: 4, background: BLUE, boxShadow: `0 0 18px ${BLUE}` }} />
          </div>
        );
      })()}
      {pip && <PersonPip pip={pip} enter={enter} />}
    </AbsoluteFill>
  );
};

/**
 * 댓글 남기기 → 전송 → 프롬프트 문서가 날아온다 (마무리 행동 유도: "응원의 댓글 하나 남겨주시면 프롬프트도 보내드리고").
 * comment: 댓글 예시, docTitle: 받는 자료 이름
 */
export const CommentScene: React.FC<{ comment: string; docTitle: string; sendAt?: number; docAt?: number; pip?: string }> = ({
  comment, docTitle, sendAt = 24, docAt = 38, pip,
}) => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const enter = spring({ frame: f, fps, config: { damping: 18, stiffness: 160 } });
  const typed = comment.slice(0, Math.max(0, Math.round(interpolate(f, [4, sendAt - 4], [0, comment.length], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }))));
  const sent = f >= sendAt;
  const posted = spring({ frame: f - sendAt, fps, config: { damping: 16, stiffness: 180 } });
  const doc = spring({ frame: f - docAt, fps, config: { damping: 14, stiffness: 150 } });
  return (
    <AbsoluteFill style={{ background: BG, fontFamily: FONT }}>
      <div style={{ position: "absolute", left: 60, right: 60, top: 300, height: 380, ...card, padding: 40,
        transform: `translateY(${(1 - enter) * 60}px) scale(${0.96 + 0.04 * enter})`, opacity: enter }}>
        <div style={{ fontSize: 40, fontWeight: 900, color: INK, textAlign: "center" }}>댓글</div>
        <div style={{ height: 2, background: "#EEF0F3", margin: "22px -36px 26px" }} />
        {sent && (
          <div style={{ display: "flex", gap: 18, alignItems: "flex-start", opacity: posted, transform: `translateY(${(1 - posted) * 60}px)` }}>
            <div style={{ width: 96, height: 96, borderRadius: "50%", background: "linear-gradient(135deg,#C7D2FE,#3B5BFD)" }} />
            <div>
              <div style={{ fontSize: 32, fontWeight: 800, color: INK }}>나 <span style={{ color: SUB, fontWeight: 600 }}>· 방금</span></div>
              <div style={{ fontSize: 52, fontWeight: 900, color: INK, marginTop: 8 }}>{comment}</div>
            </div>
            <div style={{ marginLeft: "auto", fontSize: 56, color: "#ED4956", transform: `scale(${posted})` }}>♥</div>
          </div>
        )}
        <div style={{ position: "absolute", left: 28, right: 28, bottom: 28, height: 88, borderRadius: 44, background: "#F6F7F9", border: "2px solid #E6E8EC",
          display: "flex", alignItems: "center", padding: "0 18px 0 32px" }}>
          <div style={{ fontSize: 36, fontWeight: 700, color: sent ? SUB : INK, flex: 1 }}>
            {sent ? "댓글 달기..." : typed}
            {!sent && <span style={{ opacity: Math.floor(f / 6) % 2 ? 0 : 1, color: BLUE }}>|</span>}
          </div>
          <div style={{ fontSize: 30, fontWeight: 900, color: typed.length && !sent ? BLUE : "#C9CED6" }}>게시</div>
        </div>
      </div>
 {/* 받는 자료: 문서 카드가 날아와 앉는다 */}
      {f >= docAt && (
        <div style={{ position: "absolute", left: 120, right: 120, top: 712, height: 170, ...card, padding: "24px 34px", display: "flex", alignItems: "center", gap: 22,
          opacity: doc, transform: `translate(${(1 - doc) * 300}px, ${(1 - doc) * -120}px) rotate(${(1 - doc) * 12}deg)` }}>
          <div style={{ width: 96, height: 120, borderRadius: 14, background: "#EEF1FF", display: "flex", flexDirection: "column", gap: 10, padding: 16, boxSizing: "border-box" }}>
            {[1, 0.7, 0.85, 0.6].map((w, i) => <div key={i} style={{ height: 8, width: `${w * 100}%`, borderRadius: 4, background: BLUE, opacity: 0.55 }} />)}
          </div>
          <div>
            <div style={{ fontSize: 52, fontWeight: 900, color: INK }}>{docTitle}</div>
            <div style={{ fontSize: 32, fontWeight: 800, color: BLUE, marginTop: 6 }}>📩 DM으로 도착</div>
          </div>
        </div>
      )}
      {pip && <PersonPip pip={pip} enter={enter} />}
    </AbsoluteFill>
  );
};
