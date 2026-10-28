// 카드 목록은 src/plan.json에서 읽는다 (영상마다 [결과폴더]/broll-plan.json을 복사해 넣는다).
// 카드마다 Composition 하나 → 카드별로 따로 렌더해 CapCut에 올린다.
import React from "react";
import { Composition } from "remotion";
import { canvas } from "./brand";
import { BottomInfoCard, ChapterCard, IconPop, PromptCard, ScreenRecCard } from "./components/cards";
import { CaptionOverlay } from "./components/overlay";
import { CommentScene, PromptScene } from "./components/scene";
import { ReportScene } from "./components/report";
import { AffirmScene } from "./components/affirm";
import { FearScene, AffirmListScene } from "./components/fear";
import { FlowScene, ReelsHuntScene, RevenueScene } from "./components/scene2";
import { ChatWorkScene, GptAppScene, PercentBar, PluginScene, RecScene } from "./components/gptapp";
import { BenefitScene, CommentPop, NumberPop, ReportFocusScene, FilterHookScene, HookPromptMini, HookSplitScene, IconPairPop, ListCardScene, PolicyIntroScene } from "./components/hooks";
import { AgentLogos, CallScene, EmployeeScene, ProactiveScene, ShopScene } from "./components/agent1023";
import { CallOverlay, EmployeeBand, ImagePip, KiwiPan, KiwiScene, LogosBand, PaperProactive, ProactiveApp, RobotTalk, ShopOverlay, MsgTyping, RobotEmojiTalk, FlyingMoney, SideLabel } from "./components/agent1023b";
import plan from "./plan.json";
import { FaceScan, ReportPan, SelfiePrompt } from "./components/gwansang";
import { CollageChapter, CollageScreen, PaperCollage } from "./components/collage";
import { CFlow, CPrompt, CReels, CReport, CRevenue } from "./components/collage_scenes";
const CSCENE: Record<string, React.FC<any>> = { CPrompt, CReport, CRevenue, CFlow, CReels };

const C: Record<string, React.FC<any>> = { PromptCard, ChapterCard, IconPop, BottomInfoCard, ScreenRecCard, PromptScene, CommentScene, ReportScene, RevenueScene, FlowScene, ReelsHuntScene, AffirmScene, FearScene, AffirmListScene, GptAppScene, ChatWorkScene, PluginScene, RecScene, PercentBar, SelfiePrompt, FaceScan, ReportPan, CallScene, ShopScene, ProactiveScene, AgentLogos, EmployeeScene, FilterHookScene, HookSplitScene, ListCardScene, BenefitScene, IconPairPop, HookPromptMini, PolicyIntroScene, NumberPop, CommentPop, ReportFocusScene, CallOverlay, ShopOverlay, KiwiScene, LogosBand, EmployeeBand, PaperProactive, ImagePip, ProactiveApp, KiwiPan, RobotTalk, MsgTyping, RobotEmojiTalk, FlyingMoney, SideLabel };

const CardAny: React.FC<{ component: string; props: Record<string, unknown> }> = ({ component, props }) => {
  const Comp = C[component];
  return <Comp {...props} />;
};

type Card = { id: string; component: string; start: number; end: number; props: Record<string, unknown> };

export const RemotionRoot: React.FC = () => (
  <>
    {(plan.cards as Card[]).map((c) => (
      <Composition
        key={c.id}
        id={c.id}
        component={C[c.component]}
        durationInFrames={Math.max(1, Math.round((c.end - c.start) * canvas.fps))}
        fps={canvas.fps}
        width={canvas.width}
        height={canvas.height}
        defaultProps={c.props}
      />
    ))}
    {(plan as any).overlay && (
      <Composition id="check-overlay" component={CaptionOverlay as React.FC<any>}
        durationInFrames={Math.round((plan as any).overlay.duration * canvas.fps)} fps={canvas.fps}
        width={canvas.width} height={canvas.height} defaultProps={(plan as any).overlay} />
    )}
 {/* 시안: 프롬프트 입력 → 전송 → AI 분석 (참고 릴스 톤) */}
    <Composition id="draft-prompt1" component={PromptScene as React.FC<any>} durationInFrames={91} fps={30} width={1080} height={1920}
      defaultProps={{ prompt: "내 계정을 분석하고 컨설팅해줘.", tool: "Aside", account: "@my_account", sendAt: 26, flowAt: 40, pip: "videos/pip_d01.mp4" }} />
 {/* 여러 편집이 동시에 돌 수 있어 plan.json을 같이 쓰면 서로 덮어쓴다(실제로 겹침).
        → 영상마다 --props 파일로 렌더하는 공용 컴포지션. props: {component, props, duration} / 확인용 자막 레이어는 overlay-any */}
    <Composition id="card-any" component={CardAny as React.FC<any>} durationInFrames={30} fps={canvas.fps} width={canvas.width} height={canvas.height}
      defaultProps={{ component: "ChapterCard", props: { num: 1, title: "" }, duration: 1 }}
      calculateMetadata={({ props }: any) => ({ durationInFrames: Math.max(1, Math.round(props.duration * canvas.fps)) })} />
    <Composition id="overlay-any" component={CaptionOverlay as React.FC<any>} durationInFrames={30} fps={canvas.fps} width={canvas.width} height={canvas.height}
      defaultProps={{ duration: 1, captions: [] }}
      calculateMetadata={({ props }: any) => ({ durationInFrames: Math.max(1, Math.round(props.duration * canvas.fps)) })} />
 {/* 콜라주판 공용: --props {kind: "screen"|"chapter", duration, ...} */}
    <Composition id="collage-any" component={((p: any) => { if (p.kind === "chapter") return <CollageChapter {...p} />; if (p.kind === "scene") { const S = CSCENE[p.scene]; return <S {...p.props} pip={p.pip} pipEnter={p.pipEnter} />; } return <CollageScreen {...p} />; }) as React.FC<any>}
      durationInFrames={30} fps={canvas.fps} width={canvas.width} height={canvas.height} defaultProps={{ kind: "chapter", num: 1, title: "", duration: 1 }}
      calculateMetadata={({ props }: any) => ({ durationInFrames: Math.max(1, Math.round(props.duration * canvas.fps)) })} />
  </>
);
