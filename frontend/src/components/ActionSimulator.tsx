import React, { useState } from 'react';
import { 
  Play, 
  RotateCcw, 
  Check, 
  X, 
  ShieldAlert, 
  ShieldCheck, 
  Lock, 
  Database, 
  Server, 
  FileCode,
  GitBranch
} from 'lucide-react';

interface Scenario {
  title: string;
  category: string;
  icon: any;
  command: string;
  risk: 'SAFE' | 'REVERSIBLE' | 'IRREVERSIBLE';
  rules: string[];
  explanation: string;
}

const PRESET_SCENARIOS: Scenario[] = [
  {
    title: "SQL Production Drop",
    category: "Database",
    icon: Database,
    command: "DROP TABLE users_production CASCADE;",
    risk: "IRREVERSIBLE",
    rules: ["sql-drop-table", "sql-cascade-modifier"],
    explanation: "Drops schema table and deletes records without rollback log."
  },
  {
    title: "Recursive Directory Deletion",
    category: "Filesystem",
    icon: FileCode,
    command: "rm -rf src/backend/auth_service/",
    risk: "REVERSIBLE",
    rules: ["fs-rm-recursive", "fs-directory-target"],
    explanation: "Shadow git commit will capture filesystem before unlink."
  },
  {
    title: "AWS Cloud Termination",
    category: "Cloud Ops",
    icon: Server,
    command: "aws ec2 terminate-instances --instance-ids i-04a291f0",
    risk: "IRREVERSIBLE",
    rules: ["aws-ec2-terminate", "cloud-destructive-api"],
    explanation: "Shuts down and releases cloud compute instances permanently."
  },
  {
    title: "Force Git Push to Main",
    category: "Source Control",
    icon: GitBranch,
    command: "git push origin main --force",
    risk: "IRREVERSIBLE",
    rules: ["git-push-force", "git-protected-branch-main"],
    explanation: "Rewrites upstream commit history on protected default branch."
  },
  {
    title: "Safe Status & Health Check",
    category: "Read-Only",
    icon: ShieldCheck,
    command: "git status -s && uname -a",
    risk: "SAFE",
    rules: ["read-only-whitelist"],
    explanation: "Read-only inspection command with zero side effects."
  }
];

export const ActionSimulator: React.FC = () => {
  const [selectedScenario, setSelectedScenario] = useState<Scenario>(PRESET_SCENARIOS[0]);
  const [customCommand, setCustomCommand] = useState<string>(PRESET_SCENARIOS[0].command);
  const [executionState, setExecutionState] = useState<'idle' | 'running' | 'completed'>('idle');
  const [isApproved, setIsApproved] = useState<boolean>(false);
  const [isRolledBack, setIsRolledBack] = useState<boolean>(false);

  const handleSelect = (scenario: Scenario) => {
    setSelectedScenario(scenario);
    setCustomCommand(scenario.command);
    setExecutionState('idle');
    setIsApproved(false);
    setIsRolledBack(false);
  };

  const handleRun = () => {
    setExecutionState('running');
    setIsApproved(false);
    setIsRolledBack(false);
    setTimeout(() => {
      setExecutionState('completed');
    }, 450);
  };

  return (
    <section id="simulator" className="py-20 bg-white border-t border-b border-zinc-200/70">
      <div className="max-w-7xl mx-auto px-6">
        
        {/* Section Header */}
        <div className="max-w-2xl mx-auto text-center mb-14">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-zinc-100 text-zinc-700 text-xs font-semibold uppercase tracking-wider mb-3">
            Interactive Testbed
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-[#111111] tracking-tight">
            See how Rewind stops disaster in{' '}
            <span className="font-serif italic font-normal text-zinc-500">real time</span>
          </h2>
          <p className="mt-3 text-zinc-600 text-base">
            Select a high-risk operation below to test how the Policy Classifier intercepts the agent outside its context window.
          </p>
        </div>

        {/* Interactive Layout: Scenario Selector + Simulated Terminal */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          
          {/* Left: Scenarios list */}
          <div className="lg:col-span-5 flex flex-col gap-2.5">
            <span className="text-xs font-semibold text-zinc-400 uppercase tracking-wider px-1">
              Select Agent Scenario
            </span>

            {PRESET_SCENARIOS.map((s, idx) => {
              const Icon = s.icon;
              const isSelected = selectedScenario.title === s.title;

              return (
                <button
                  key={idx}
                  onClick={() => handleSelect(s)}
                  className={`p-4 rounded-xl text-left border transition-all flex items-start gap-3.5 ${
                    isSelected
                      ? 'border-zinc-900 bg-zinc-50 shadow-sm'
                      : 'border-zinc-200/80 bg-white hover:border-zinc-300'
                  }`}
                >
                  <div className={`p-2 rounded-lg mt-0.5 ${
                    s.risk === 'IRREVERSIBLE'
                      ? 'bg-red-50 text-red-600'
                      : s.risk === 'REVERSIBLE'
                      ? 'bg-blue-50 text-blue-600'
                      : 'bg-emerald-50 text-emerald-600'
                  }`}>
                    <Icon className="w-4 h-4" />
                  </div>

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center justify-between mb-1">
                      <span className="font-semibold text-sm text-zinc-900 truncate">
                        {s.title}
                      </span>
                      <span className={`text-[10px] font-bold px-2 py-0.5 rounded-full border uppercase ${
                        s.risk === 'IRREVERSIBLE'
                          ? 'bg-red-50 text-red-600 border-red-200'
                          : s.risk === 'REVERSIBLE'
                          ? 'bg-blue-50 text-blue-600 border-blue-200'
                          : 'bg-emerald-50 text-emerald-600 border-emerald-200'
                      }`}>
                        {s.risk}
                      </span>
                    </div>
                    <p className="font-mono text-xs text-zinc-500 truncate mb-1">
                      $ {s.command}
                    </p>
                    <p className="text-xs text-zinc-400 leading-normal">
                      {s.explanation}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>

          {/* Right: Simulated Interception Console */}
          <div className="lg:col-span-7 bg-[#0c0d0e] rounded-2xl border border-zinc-800 shadow-xl overflow-hidden flex flex-col">
            
            {/* Console Header */}
            <div className="px-4 py-3 bg-[#16171a] border-b border-zinc-800 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="flex gap-1.5">
                  <div className="w-2.5 h-2.5 rounded-full bg-red-500/80"></div>
                  <div className="w-2.5 h-2.5 rounded-full bg-yellow-500/80"></div>
                  <div className="w-2.5 h-2.5 rounded-full bg-green-500/80"></div>
                </div>
                <span className="text-xs font-mono text-zinc-400 ml-2">
                  mcp-proxy — session: sandbox-eval
                </span>
              </div>

              <div className="flex items-center gap-2">
                <span className="text-[11px] font-mono text-zinc-400 bg-zinc-800 px-2 py-0.5 rounded">
                  Policy: Strict-Enterprise
                </span>
              </div>
            </div>

            {/* Console Body */}
            <div className="p-5 font-mono text-xs text-zinc-200 space-y-4 min-h-[380px]">
              
              {/* Command input banner */}
              <div>
                <span className="text-zinc-500 text-[11px]"># Agent Attempting Command:</span>
                <div className="flex items-center gap-2 mt-1">
                  <span className="text-emerald-400 font-bold">$</span>
                  <input
                    type="text"
                    value={customCommand}
                    onChange={(e) => setCustomCommand(e.target.value)}
                    className="flex-1 bg-zinc-900/80 text-zinc-100 px-3 py-1.5 rounded border border-zinc-700 focus:outline-none focus:border-zinc-500 font-mono text-xs"
                  />
                  <button
                    onClick={handleRun}
                    className="px-3 py-1.5 rounded bg-blue-600 hover:bg-blue-500 text-white font-sans text-xs font-semibold flex items-center gap-1.5 transition-colors"
                  >
                    <Play className="w-3 h-3 fill-current" /> Run
                  </button>
                </div>
              </div>

              {/* Execution Output */}
              {executionState === 'running' && (
                <div className="py-8 text-center text-zinc-400 flex flex-col items-center gap-2">
                  <div className="w-5 h-5 border-2 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
                  <span>Passing through Rewind Classifier and Policy Pack Matcher...</span>
                </div>
              )}

              {executionState === 'completed' && (
                <div className="space-y-3 animate-in fade-in duration-300">
                  
                  {/* Verdict Banner */}
                  {selectedScenario.risk === 'IRREVERSIBLE' && (
                    <div className="p-4 rounded-xl bg-red-950/40 border border-red-900/60 text-red-200 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-red-400 flex items-center gap-1.5 text-sm">
                          <ShieldAlert className="w-4 h-4" /> 🚫 SYSCALL BLOCKED BY REWIND
                        </span>
                        <span className="bg-red-900/80 text-red-300 text-[10px] px-2 py-0.5 rounded font-mono">
                          IRREVERSIBLE
                        </span>
                      </div>
                      <p className="text-xs text-zinc-300">
                        Triggered rules: <span className="font-mono text-red-300">{selectedScenario.rules.join(', ')}</span>
                      </p>
                      <p className="text-xs text-zinc-400">
                        {selectedScenario.explanation}
                      </p>

                      {/* Approval Box */}
                      <div className="mt-3 pt-3 border-t border-red-900/40 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 bg-black/40 p-3 rounded-lg">
                        <div>
                          <div className="text-[11px] text-zinc-400 font-mono">Request: apr_94b12c • Mode: 2-of-2</div>
                          <div className="text-xs font-sans text-white font-medium">
                            {isApproved ? "Consensus granted! Command executed safely." : "Requires approval from Security Team"}
                          </div>
                        </div>

                        {!isApproved ? (
                          <div className="flex gap-2">
                            <button
                              onClick={() => setIsApproved(true)}
                              className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded font-sans text-xs font-semibold flex items-center gap-1"
                            >
                              <Check className="w-3.5 h-3.5" /> Approve
                            </button>
                            <button className="px-3 py-1.5 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 rounded font-sans text-xs font-semibold flex items-center gap-1">
                              <X className="w-3.5 h-3.5" /> Deny
                            </button>
                          </div>
                        ) : (
                          <span className="text-xs font-semibold text-emerald-400 flex items-center gap-1">
                            <Check className="w-3.5 h-3.5" /> Executed & Sealed in Ledger
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  {selectedScenario.risk === 'REVERSIBLE' && (
                    <div className="p-4 rounded-xl bg-blue-950/40 border border-blue-900/60 text-blue-200 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-blue-400 flex items-center gap-1.5 text-sm">
                          <RotateCcw className="w-4 h-4" /> ⚠️ REVERSIBLE ACTION (Checkpoint Created)
                        </span>
                        <span className="bg-blue-900/80 text-blue-300 text-[10px] px-2 py-0.5 rounded font-mono">
                          SNAPSHOT ACTIVE
                        </span>
                      </div>
                      <p className="text-xs text-zinc-300">
                        Shadow git commit created before execution: <span className="font-mono text-blue-300">snap_4a821</span>
                      </p>
                      
                      <div className="mt-3 pt-3 border-t border-blue-900/40 flex items-center justify-between bg-black/40 p-3 rounded-lg">
                        <div>
                          <div className="text-[11px] text-zinc-400 font-mono">Filesystem Checkpoint Ready</div>
                          <div className="text-xs font-sans text-white font-medium">
                            {isRolledBack ? "Files restored to pristine pre-action state!" : "Need to undo agent's changes?"}
                          </div>
                        </div>

                        {!isRolledBack ? (
                          <button
                            onClick={() => setIsRolledBack(true)}
                            className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded font-sans text-xs font-semibold flex items-center gap-1.5"
                          >
                            <RotateCcw className="w-3.5 h-3.5" /> Rewind to Checkpoint
                          </button>
                        ) : (
                          <span className="text-xs font-semibold text-emerald-400 flex items-center gap-1">
                            <Check className="w-3.5 h-3.5" /> Restored Successfully
                          </span>
                        )}
                      </div>
                    </div>
                  )}

                  {selectedScenario.risk === 'SAFE' && (
                    <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-900/60 text-emerald-200 space-y-2">
                      <div className="flex items-center justify-between">
                        <span className="font-bold text-emerald-400 flex items-center gap-1.5 text-sm">
                          <ShieldCheck className="w-4 h-4" /> ✅ SAFE ACTION PERMITTED
                        </span>
                        <span className="bg-emerald-900/80 text-emerald-300 text-[10px] px-2 py-0.5 rounded font-mono">
                          PASSTHROUGH
                        </span>
                      </div>
                      <p className="text-xs text-zinc-300">
                        Rule match: <span className="font-mono text-emerald-300">read-only-whitelist</span>. Executed directly without blocking.
                      </p>
                      <div className="bg-black/40 p-2.5 rounded font-mono text-[11px] text-zinc-400">
                        Linux 6.8.0-generic x86_64 GNU/Linux<br />
                        nothing to commit, working tree clean
                      </div>
                    </div>
                  )}

                </div>
              )}

              {executionState === 'idle' && (
                <div className="py-12 text-center text-zinc-500 flex flex-col items-center">
                  <Play className="w-8 h-8 mb-2 opacity-30" />
                  <p className="text-xs">Click &quot;Run&quot; above to simulate real-time agent interception.</p>
                </div>
              )}

            </div>

            {/* Console Footer */}
            <div className="px-4 py-2.5 bg-[#121316] border-t border-zinc-800 text-[11px] font-mono text-zinc-500 flex justify-between">
              <span>SHA-256 Ledger Hash: 4e82b...c91</span>
              <span>Proxy Port: 8787 (FastMCP)</span>
            </div>

          </div>

        </div>

      </div>
    </section>
  );
};
