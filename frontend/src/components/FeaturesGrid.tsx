import React from 'react';
import { 
  ShieldCheck, 
  RotateCcw, 
  Users, 
  Hash, 
  Cpu, 
  Layers, 
  Laptop
} from 'lucide-react';

export const FeaturesGrid: React.FC = () => {
  return (
    <section id="how-it-works" className="py-24 bg-[#fcfbfa]">
      <div className="max-w-7xl mx-auto px-6">
        
        {/* Header */}
        <div className="max-w-3xl mb-16">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-zinc-200/70 text-zinc-800 text-xs font-semibold uppercase tracking-wider mb-3">
            Core Architecture
          </div>
          <h2 className="text-3xl sm:text-5xl font-extrabold text-[#111111] tracking-tight leading-[1.12]">
            Prompts are advice.{' '}
            <span className="font-serif italic font-normal text-zinc-500">
              Rewind is physics.
            </span>
          </h2>
          <p className="mt-4 text-zinc-600 text-lg leading-relaxed">
            LLMs cannot be trusted to follow instructions when manipulating production databases, deleting files, or executing cloud operations. Rewind takes the decision out of the model&apos;s hands.
          </p>
        </div>

        {/* Bento Grid */}
        <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
          
          {/* Bento Item 1: Non-bypassable by Construction (Large) */}
          <div className="md:col-span-7 rounded-3xl bg-white p-8 sm:p-10 border border-zinc-200/80 shadow-sm flex flex-col justify-between hover:shadow-md transition-shadow">
            <div>
              <div className="w-12 h-12 rounded-2xl bg-zinc-100 flex items-center justify-center text-zinc-900 mb-6">
                <ShieldCheck className="w-6 h-6" />
              </div>
              <h3 className="text-2xl font-bold text-zinc-900 mb-3">
                Non-bypassable by Construction
              </h3>
              <p className="text-zinc-600 text-base leading-relaxed mb-6">
                Most AI guardrails rely on system prompt instructions like &quot;do not delete files&quot;. These are vulnerable to context overflow, jailbreaks, and hallucinations. Rewind sits at the MCP proxy level — the model cannot execute the command because it doesn&apos;t hold the credentials.
              </p>
            </div>

            <div className="p-4 rounded-2xl bg-[#0d0e11] text-zinc-300 font-mono text-xs border border-zinc-800">
              <div className="text-zinc-500 mb-1"># Enforcement Boundary:</div>
              <div className="text-red-400 font-semibold">&gt; Agent: rm -rf /var/lib/postgresql/data</div>
              <div className="text-emerald-400">&gt; Rewind MCP: Intercepted before OS execve() [Blocked]</div>
            </div>
          </div>

          {/* Bento Item 2: Shadow Git Snapshotter */}
          <div className="md:col-span-5 rounded-3xl bg-white p-8 sm:p-10 border border-zinc-200/80 shadow-sm flex flex-col justify-between hover:shadow-md transition-shadow">
            <div>
              <div className="w-12 h-12 rounded-2xl bg-blue-50 text-blue-600 flex items-center justify-center mb-6">
                <RotateCcw className="w-6 h-6" />
              </div>
              <h3 className="text-2xl font-bold text-zinc-900 mb-3">
                Automatic Shadow Checkpoints
              </h3>
              <p className="text-zinc-600 text-base leading-relaxed mb-6">
                Every reversible file modification or directory change automatically captures a shadow git commit before execution. If the agent makes a mistake, one click reverts every single line of code.
              </p>
            </div>

            <div className="p-4 rounded-xl bg-blue-50/70 border border-blue-100 text-blue-900 text-xs font-mono">
              <span className="font-bold">Checkpoint: snap_742f9a</span>
              <div className="text-blue-700 mt-1">42 files restored in 14ms via git tree checkout</div>
            </div>
          </div>

          {/* Bento Item 3: Multi-Party Consensus & Separation of Duties */}
          <div className="md:col-span-4 rounded-3xl bg-white p-8 border border-zinc-200/80 shadow-sm flex flex-col justify-between hover:shadow-md transition-shadow">
            <div>
              <div className="w-12 h-12 rounded-2xl bg-amber-50 text-amber-600 flex items-center justify-center mb-6">
                <Users className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-zinc-900 mb-2">
                Multi-Party Consensus
              </h3>
              <p className="text-zinc-600 text-sm leading-relaxed mb-4">
                Require N-of-M approvals on sensitive resources. Enforces strict Separation of Duties: session creators are barred from approving their own session commands.
              </p>
            </div>
            <span className="text-xs font-mono font-semibold text-amber-700 bg-amber-50 p-2 rounded-lg border border-amber-200/60">
              Role Matrix: Admin, Approver, Viewer
            </span>
          </div>

          {/* Bento Item 4: Cryptographic SHA-256 Ledger */}
          <div className="md:col-span-4 rounded-3xl bg-white p-8 border border-zinc-200/80 shadow-sm flex flex-col justify-between hover:shadow-md transition-shadow">
            <div>
              <div className="w-12 h-12 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center mb-6">
                <Hash className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-zinc-900 mb-2">
                Cryptographic Ledger
              </h3>
              <p className="text-zinc-600 text-sm leading-relaxed mb-4">
                Every classified event, snapshot, and vote is hashed and chained into a tamper-evident SQLite WAL database. Mathematically verifiable from genesis.
              </p>
            </div>
            <span className="text-xs font-mono font-semibold text-emerald-700 bg-emerald-50 p-2 rounded-lg border border-emerald-200/60">
              SHA-256 Genesis Hash Chained
            </span>
          </div>

          {/* Bento Item 5: Native VS Code & Terminal Flow */}
          <div className="md:col-span-4 rounded-3xl bg-white p-8 border border-zinc-200/80 shadow-sm flex flex-col justify-between hover:shadow-md transition-shadow">
            <div>
              <div className="w-12 h-12 rounded-2xl bg-purple-50 text-purple-600 flex items-center justify-center mb-6">
                <Laptop className="w-6 h-6" />
              </div>
              <h3 className="text-xl font-bold text-zinc-900 mb-2">
                IDE Native Integration
              </h3>
              <p className="text-zinc-600 text-sm leading-relaxed mb-4">
                Approve requests without switching contexts. The Rewind VS Code Extension surfaces QuickPick prompts right in your editor when an agent gets blocked.
              </p>
            </div>
            <span className="text-xs font-mono font-semibold text-purple-700 bg-purple-50 p-2 rounded-lg border border-purple-200/60">
              VS Code QuickPick & Status Bar
            </span>
          </div>

        </div>

      </div>
    </section>
  );
};
