import React, { useState, useEffect } from 'react';
import { 
  ShieldAlert, 
  RotateCcw, 
  CheckCircle2, 
  Lock, 
  Laptop,
  Check,
  ChevronRight,
  Database,
  GitBranch,
  ShieldCheck,
  Terminal
} from 'lucide-react';

interface FrameScene {
  id: number;
  tabTitle: string;
  badgeText: string;
  badgeStyle: string;
  metric1Label: string;
  metric1Val: string;
  metric1Percent: number;
  metric2Label: string;
  metric2Val: string;
  metric2Percent: number;
  terminalCommand: string;
  terminalStatus: string;
  terminalStatusColor: string;
  terminalDetail: string;
  terminalTag: string;
}

const FRAMES: FrameScene[] = [
  {
    id: 1,
    tabTitle: "1. Block & Intercept",
    badgeText: "IRREVERSIBLE BLOCKED",
    badgeStyle: "bg-red-50 text-red-600 border-red-200",
    metric1Label: "Pre-flight Intercept",
    metric1Val: "81.8 ms",
    metric1Percent: 78,
    metric2Label: "Classification Rule",
    metric2Val: "sql-drop-table",
    metric2Percent: 100,
    terminalCommand: 'DROP TABLE customers_prod CASCADE;',
    terminalStatus: "🚫 ACTION BLOCKED BY REWIND",
    terminalStatusColor: "text-red-400",
    terminalDetail: "Syscall halted before execution. Queued as apr_84f9a.",
    terminalTag: "Risk: Irreversible"
  },
  {
    id: 2,
    tabTitle: "2. Consensus Sign-Off",
    badgeText: "2-OF-2 APPROVAL PENDING",
    badgeStyle: "bg-amber-50 text-amber-700 border-amber-200",
    metric1Label: "Approver Votes",
    metric1Val: "1 of 2 Signed",
    metric1Percent: 50,
    metric2Label: "Auto-Expiry Timer",
    metric2Val: "14m 20s",
    metric2Percent: 92,
    terminalCommand: 'DROP TABLE customers_prod CASCADE;',
    terminalStatus: "⏳ MULTI-PARTY CONSENSUS REQUIRED",
    terminalStatusColor: "text-amber-400",
    terminalDetail: "Separation of duties enforced. Initiator cannot self-approve.",
    terminalTag: "Awaiting Security Lead"
  },
  {
    id: 3,
    tabTitle: "3. Cryptographic Ledger",
    badgeText: "CHAIN HASH VERIFIED",
    badgeStyle: "bg-emerald-50 text-emerald-700 border-emerald-200",
    metric1Label: "Tamper Proof Check",
    metric1Val: "Intact (0 errors)",
    metric1Percent: 100,
    metric2Label: "Hash Chained Sequence",
    metric2Val: "#1,429",
    metric2Percent: 100,
    terminalCommand: 'execute_approved_command("apr_84f9a")',
    terminalStatus: "✅ EXECUTED & SEALED IN LEDGER",
    terminalStatusColor: "text-emerald-400",
    terminalDetail: "SHA-256 hash 7d0bb3... appended to immutable SQLite WAL chain.",
    terminalTag: "Mathematical Proof Intact"
  },
  {
    id: 4,
    tabTitle: "4. Reversible Rollback",
    badgeText: "CHECKPOINT READY",
    badgeStyle: "bg-blue-50 text-blue-700 border-blue-200",
    metric1Label: "Shadow Tree Capture",
    metric1Val: "12.4 ms",
    metric1Percent: 95,
    metric2Label: "Rollback Restore Time",
    metric2Val: "6.2 ms",
    metric2Percent: 100,
    terminalCommand: 'rm -rf src/billing_service/',
    terminalStatus: "⚠️ REVERSIBLE ACTION (Checkpoint snap_3f92d)",
    terminalStatusColor: "text-blue-400",
    terminalDetail: "Shadow git commit recorded. 1-click restore brings all 48 files back.",
    terminalTag: "Instant Undo Available"
  }
];

export const HeroSection: React.FC = () => {
  const [activeFrame, setActiveFrame] = useState<number>(1);
  const [copied, setCopied] = useState<boolean>(false);

  // Simple, smooth auto-advance timer for picture-to-picture transition
  useEffect(() => {
    const timer = setInterval(() => {
      setActiveFrame((prev) => (prev % FRAMES.length) + 1);
    }, 4500);
    return () => clearInterval(timer);
  }, []);

  const handleCopyCmd = () => {
    navigator.clipboard.writeText("curl -fsSL https://raw.githubusercontent.com/abhinav29102005/rewind/main/install.sh | bash");
    setCopied(true);
    setTimeout(() => setCopied(false), 2200);
  };

  return (
    <section className="relative pt-6 pb-20 md:py-20 bg-[#fcfbfa]">
      <div className="max-w-7xl mx-auto px-6">
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-12 lg:gap-8 items-center">
          
          {/* ========================================================= */}
          {/* LEFT COLUMN: Clean, punchy typography matching ego lite  */}
          {/* ========================================================= */}
          <div className="lg:col-span-6 flex flex-col items-start pr-0 lg:pr-4">
            
            {/* Main Headline */}
            <h1 className="text-4xl sm:text-5xl lg:text-[56px] font-extrabold tracking-tight text-[#111111] leading-[1.08] mb-6">
              Fastest{' '}
              <span className="font-serif italic font-normal text-zinc-500">failsafe</span>
              <br />
              for AI agents to
              <br />
              run web automation
            </h1>

            {/* Subtitle with soft highlight pill */}
            <p className="text-[17px] sm:text-lg text-zinc-600 leading-relaxed mb-8 max-w-xl">
              <strong className="text-zinc-900 font-semibold">rewind</strong>{' '}
              <span className="font-serif italic font-normal text-zinc-500">(guard)</span>{' '}
              is the proxy built for{' '}
              <span className="bg-[#e0e7ff] text-[#1e40af] font-medium px-2 py-0.5 rounded-md inline-block">
                intercepting destructive operations
              </span>{' '}
              with your AI agents, like Codex or Claude Code, without disturbing you. Zero cost, zero config. Let them handle terminal and browser automation safely.
            </p>

            {/* CTA Buttons matching ego lite style */}
            <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 w-full sm:w-auto mb-8">
              {/* Primary Black Button */}
              <button
                onClick={handleCopyCmd}
                className="group px-6 py-3.5 rounded-xl bg-[#111111] hover:bg-black text-white text-sm font-medium flex items-center justify-center gap-3 shadow-md transition-transform active:scale-95"
              >
                <Terminal className="w-4 h-4 text-emerald-400" />
                <span>Copy 1-Line Installer</span>
                <span className="text-zinc-400 font-serif italic text-xs">
                  {copied ? "(copied!)" : "(yes, free)"}
                </span>
              </button>

              {/* Secondary Button -> Docs & Connect */}
              <a
                href="#docs"
                className="px-6 py-3.5 rounded-xl bg-[#f0ede6] hover:bg-[#e8e4dc] text-zinc-800 text-sm font-medium flex items-center justify-center gap-2.5 transition-colors border border-zinc-200/60"
              >
                <Laptop className="w-4 h-4 text-zinc-700" />
                <span>Connect Your Agent</span>
              </a>
            </div>

            {/* Quick Proof Pills */}
            <div className="flex flex-wrap items-center gap-4 text-xs text-zinc-500 font-medium mb-8">
              <div className="flex items-center gap-1.5">
                <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
                <span>FastMCP Proxy Protocol</span>
              </div>
              <span className="text-zinc-300">•</span>
              <div className="flex items-center gap-1.5">
                <Lock className="w-3.5 h-3.5 text-zinc-400" />
                <span>SHA-256 Tamper-Proof Ledger</span>
              </div>
              <span className="text-zinc-300">•</span>
              <div className="flex items-center gap-1.5">
                <RotateCcw className="w-3.5 h-3.5 text-blue-500" />
                <span>Automatic Git Rollback</span>
              </div>
            </div>

            {/* Picture-to-Picture Frame Selector Pills */}
            <div className="w-full max-w-lg pt-4 border-t border-zinc-200/80">
              <div className="text-xs font-semibold uppercase tracking-wider text-zinc-400 mb-2.5 flex items-center justify-between">
                <span>Next Action Frames</span>
                <span className="text-[11px] font-mono text-zinc-400">Click to switch frame</span>
              </div>
              <div className="grid grid-cols-4 gap-1.5 p-1 bg-zinc-100 rounded-xl border border-zinc-200/60">
                {FRAMES.map((f) => (
                  <button
                    key={f.id}
                    onClick={() => setActiveFrame(f.id)}
                    className={`text-xs py-2 px-1 rounded-lg font-medium transition-all text-center ${
                      activeFrame === f.id
                        ? 'bg-white text-zinc-900 shadow-sm font-semibold'
                        : 'text-zinc-500 hover:text-zinc-800'
                    }`}
                  >
                    Frame {f.id}
                  </button>
                ))}
              </div>
            </div>

          </div>

          {/* ========================================================= */}
          {/* RIGHT COLUMN: Stable Picture-to-Picture Fade Overlay Card */}
          {/* ========================================================= */}
          <div className="lg:col-span-6 relative">
            
            {/* Outer Container with Tennis Court Painted Background */}
            <div className="relative rounded-[32px] overflow-hidden p-5 sm:p-7 shadow-xl bg-[#1e392a] border border-[#2d523d]">
              
              {/* Rich Painterly Art Background (Stable, no motion sickness) */}
              <div className="absolute inset-0 pointer-events-none opacity-90 overflow-hidden">
                <div className="absolute inset-0 bg-gradient-to-br from-[#193b28] via-[#244f37] to-[#163524]"></div>
                
                {/* Court White Lines */}
                <div className="absolute top-0 bottom-0 left-[22%] w-[2.5px] bg-white/25"></div>
                <div className="absolute top-0 bottom-0 right-[22%] w-[2.5px] bg-white/25"></div>
                <div className="absolute top-[48%] left-0 right-0 h-[2.5px] bg-white/25"></div>

                {/* Painterly highlights */}
                <div className="absolute -top-10 -right-10 w-64 h-64 rounded-full bg-rose-500/25 blur-3xl"></div>
                <div className="absolute top-1/2 -left-12 w-64 h-64 rounded-full bg-emerald-400/20 blur-3xl"></div>

                {/* Abstract Painterly Figure (Homage to ego lite) */}
                <div className="absolute top-4 right-8 opacity-75 transform rotate-6">
                  <div className="w-12 h-12 rounded-full bg-[#fcd34d] border-2 border-white/40 shadow-md"></div>
                  <div className="w-16 h-24 bg-[#f43f5e] rounded-2xl -mt-3 ml-2 border border-white/20"></div>
                </div>
              </div>

              {/* ------------------------------------------------------------- */}
              {/* LAYER 1: Main White App Window (Stable with Fade Overlay)     */}
              {/* ------------------------------------------------------------- */}
              <div className="relative bg-white rounded-2xl shadow-xl overflow-hidden border border-zinc-200/90 z-10 min-h-[340px]">
                
                {/* Window Titlebar */}
                <div className="px-4 py-3 bg-[#faf9f8] border-b border-zinc-200/70 flex items-center justify-between">
                  <div className="flex items-center gap-1.5">
                    <div className="w-2.5 h-2.5 rounded-full bg-[#ff5f56]"></div>
                    <div className="w-2.5 h-2.5 rounded-full bg-[#ffbd2e]"></div>
                    <div className="w-2.5 h-2.5 rounded-full bg-[#27c93f]"></div>
                  </div>
                  
                  <span className="text-xs font-mono font-medium text-zinc-500">
                    rewind.control-plane:8787
                  </span>

                  <div className="w-3.5 h-3.5 rounded border border-zinc-300 flex items-center justify-center text-[9px] font-bold text-zinc-400">
                    ⊞
                  </div>
                </div>

                {/* Frame Scenes Layered with Picture-to-Picture Fade Overlay */}
                <div className="relative p-5 min-h-[290px]">
                  {FRAMES.map((f) => {
                    const isActive = f.id === activeFrame;

                    return (
                      <div
                        key={f.id}
                        className={`transition-opacity duration-700 ease-in-out ${
                          isActive 
                            ? 'opacity-100 relative pointer-events-auto' 
                            : 'opacity-0 absolute inset-0 p-5 pointer-events-none'
                        }`}
                      >
                        {/* Speed & Metric Pills matching ego lite */}
                        <div className="grid grid-cols-2 gap-3 mb-4">
                          <div className="p-3 rounded-xl bg-zinc-50 border border-zinc-100 flex flex-col justify-between">
                            <div className="flex justify-between items-center text-xs mb-1.5">
                              <span className="text-zinc-500 font-medium">{f.metric1Label}</span>
                              <span className="font-mono font-bold text-zinc-800">{f.metric1Val}</span>
                            </div>
                            <div className="w-full bg-zinc-200 h-2 rounded-full overflow-hidden">
                              <div 
                                className="h-full bg-blue-600 rounded-full transition-all duration-500" 
                                style={{ width: `${f.metric1Percent}%` }}
                              ></div>
                            </div>
                          </div>

                          <div className="p-3 rounded-xl bg-zinc-50 border border-zinc-100 flex flex-col justify-between">
                            <div className="flex justify-between items-center text-xs mb-1.5">
                              <span className="text-zinc-500 font-medium">{f.metric2Label}</span>
                              <span className="font-mono font-bold text-zinc-800">{f.metric2Val}</span>
                            </div>
                            <div className="w-full bg-zinc-200 h-2 rounded-full overflow-hidden">
                              <div 
                                className="h-full bg-blue-600 rounded-full transition-all duration-500" 
                                style={{ width: `${f.metric2Percent}%` }}
                              ></div>
                            </div>
                          </div>
                        </div>

                        {/* Space Navigation Tabs */}
                        <div className="flex items-center justify-between text-xs font-medium text-zinc-500 pb-2 border-b border-zinc-100 mb-3">
                          <div className="flex items-center gap-4">
                            <span className="text-zinc-900 font-semibold border-b-2 border-zinc-900 pb-2 -mb-2">
                              Space 1 (Prod)
                            </span>
                            <span className="hover:text-zinc-800 cursor-pointer">Personal</span>
                            <span className="hover:text-zinc-800 cursor-pointer hidden sm:inline">Summarize morning meeting...</span>
                          </div>
                          <span className="text-[11px] font-mono text-zinc-400">Work</span>
                        </div>

                        {/* Action Card Preview */}
                        <div className="border border-zinc-200 rounded-xl p-3.5 bg-[#fdfdfc]">
                          <div className="flex items-center justify-between mb-2">
                            <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full border uppercase tracking-wider ${f.badgeStyle}`}>
                              {f.badgeText}
                            </span>
                            <span className="text-[11px] font-mono text-zinc-400">
                              Frame {f.id} of 4
                            </span>
                          </div>

                          <div className="font-mono text-xs text-zinc-800 bg-zinc-100 p-2.5 rounded-lg border border-zinc-200/60 mb-2 truncate">
                            $ {f.terminalCommand}
                          </div>

                          <div className="flex items-center justify-between text-xs text-zinc-500">
                            <span className="flex items-center gap-1.5 font-medium text-zinc-700">
                              <span className="w-2 h-2 rounded-full bg-blue-600"></span>
                              {f.terminalTag}
                            </span>
                            <span className="text-zinc-400 text-[11px]">Enforced Outside Agent</span>
                          </div>
                        </div>

                      </div>
                    );
                  })}
                </div>

              </div>

              {/* ------------------------------------------------------------- */}
              {/* LAYER 2: Foreground Floating Terminal Window                   */}
              {/* ------------------------------------------------------------- */}
              <div className="relative -mt-10 sm:-mt-14 sm:ml-4 bg-[#111215] text-zinc-100 rounded-2xl p-4 shadow-2xl border border-zinc-800 z-20">
                
                {/* Terminal Titlebar */}
                <div className="flex items-center justify-between pb-2.5 mb-2.5 border-b border-zinc-800">
                  <div className="flex items-center gap-2">
                    <div className="flex items-center gap-1.5">
                      <div className="w-2.5 h-2.5 rounded-full bg-red-500/80"></div>
                      <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/80"></div>
                      <div className="w-2.5 h-2.5 rounded-full bg-green-500/80"></div>
                    </div>
                    <span className="text-[11px] font-mono text-zinc-400 ml-2">
                      terminal — rewind-agent
                    </span>
                  </div>

                  {/* Retro invader icon (signature ego lite design) */}
                  <div className="w-5 h-5 flex items-center justify-center bg-orange-500/20 text-orange-400 rounded text-xs font-mono font-bold">
                    👾
                  </div>
                </div>

                {/* Terminal Body with Fade Overlay Sync */}
                <div className="font-mono text-xs leading-relaxed space-y-2">
                  <div className="text-zinc-400 text-[11px] flex justify-between items-center">
                    <span>Claude Code v2.1 • Rewind Guardrail v0.1.0</span>
                    <span className="text-emerald-400 font-semibold text-[10px]">
                      ● ENFORCED
                    </span>
                  </div>

                  {/* Crossfading Terminal Status Box */}
                  <div className="relative min-h-[68px]">
                    {FRAMES.map((f) => {
                      const isActive = f.id === activeFrame;

                      return (
                        <div
                          key={f.id}
                          className={`transition-opacity duration-700 ease-in-out bg-zinc-950 p-3 rounded-lg border border-zinc-800 text-[11px] space-y-1 ${
                            isActive
                              ? 'opacity-100 relative pointer-events-auto'
                              : 'opacity-0 absolute inset-0 pointer-events-none'
                          }`}
                        >
                          <div className={`font-bold flex items-center gap-1.5 ${f.terminalStatusColor}`}>
                            {f.terminalStatus}
                          </div>
                          <div className="text-zinc-400 truncate">
                            {f.terminalDetail}
                          </div>
                        </div>
                      );
                    })}
                  </div>

                  {/* Terminal Prompt line */}
                  <div className="flex items-center gap-1.5 text-zinc-400 pt-1 text-[11px]">
                    <span className="text-emerald-400">&gt;</span>
                    <span className="text-zinc-300">/rewind-agent active</span>
                    <span className="w-1.5 h-3 bg-zinc-400 inline-block animate-pulse"></span>
                  </div>
                </div>

              </div>

            </div>

            {/* Clean Caption under artwork */}
            <div className="mt-3.5 flex items-center justify-between text-xs text-zinc-400 px-2 font-serif italic">
              <span>Picture frame transitions showcase real-time agent interception and undo</span>
              <a href="#installation" className="text-zinc-600 hover:text-black font-sans not-italic font-medium inline-flex items-center gap-1">
                Install MCP Overlay <ChevronRight className="w-3 h-3" />
              </a>
            </div>

          </div>

        </div>
      </div>
    </section>
  );
};
