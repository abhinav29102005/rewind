import React from 'react';
import { AlertTriangle, XCircle, CheckCircle } from 'lucide-react';

export const BenchmarkTable: React.FC = () => {
  return (
    <section id="benchmarks" className="py-20 bg-white border-b border-zinc-200/80">
      <div className="max-w-7xl mx-auto px-6">
        
        <div className="max-w-3xl mb-12">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-zinc-100 text-zinc-700 text-xs font-semibold uppercase tracking-wider mb-3">
            Empirical Security Benchmarks
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold text-[#111111] tracking-tight">
            How Rewind compares against{' '}
            <span className="font-serif italic font-normal text-zinc-500">
              standard approaches
            </span>
          </h2>
          <p className="mt-3 text-zinc-600 text-base">
            Tested across 255 benchmark scenarios including adversarial prompt injections, model hallucinations, and ambiguous multi-step tasks.
          </p>
        </div>

        {/* Comparison Table */}
        <div className="overflow-x-auto rounded-2xl border border-zinc-200/80 shadow-sm">
          <table className="w-full text-left border-collapse text-sm">
            <thead>
              <tr className="bg-zinc-50 border-b border-zinc-200">
                <th className="py-4 px-6 font-bold text-zinc-900">Defense Mechanism</th>
                <th className="py-4 px-6 font-bold text-zinc-900">Destructive Actions Blocked</th>
                <th className="py-4 px-6 font-bold text-zinc-900">Data Loss Prevention</th>
                <th className="py-4 px-6 font-bold text-zinc-900">Tamper-Proof Audit</th>
                <th className="py-4 px-6 font-bold text-zinc-900">Undo Capability</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-zinc-200/70">
              
              {/* Row 1: Rewind */}
              <tr className="bg-emerald-50/30 hover:bg-emerald-50/50 transition-colors">
                <td className="py-5 px-6">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-6 rounded-full bg-emerald-600 text-white flex items-center justify-center text-xs font-bold">
                      ✓
                    </div>
                    <div>
                      <div className="font-bold text-zinc-900 text-base">Rewind (guard)</div>
                      <div className="text-xs text-zinc-500">Non-bypassable OS & MCP proxy</div>
                    </div>
                  </div>
                </td>
                <td className="py-5 px-6 font-semibold text-emerald-700">
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-emerald-100 text-xs">
                    <CheckCircle className="w-3.5 h-3.5" /> 100% (Enforced)
                  </span>
                </td>
                <td className="py-5 px-6 font-mono font-bold text-emerald-700">
                  0 Rows Lost
                </td>
                <td className="py-5 px-6 font-medium text-emerald-800">
                  SHA-256 Hash Chained
                </td>
                <td className="py-5 px-6 font-medium text-emerald-800">
                  Automatic Shadow Snapshots
                </td>
              </tr>

              {/* Row 2: Cooperative System Prompts */}
              <tr className="hover:bg-zinc-50/50 transition-colors">
                <td className="py-5 px-6">
                  <div className="font-semibold text-zinc-900">Cooperative System Prompt</div>
                  <div className="text-xs text-zinc-500">&quot;Please ask before deleting&quot;</div>
                </td>
                <td className="py-5 px-6 text-amber-600 font-medium">
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-amber-50 text-xs">
                    <AlertTriangle className="w-3.5 h-3.5" /> 38% (Vulnerable to jailbreak)
                  </span>
                </td>
                <td className="py-5 px-6 font-mono text-zinc-600">
                  1,420,000+ Rows Lost
                </td>
                <td className="py-5 px-6 text-zinc-500">
                  None (Agent Context only)
                </td>
                <td className="py-5 px-6 text-zinc-500">
                  Manual Backup Required
                </td>
              </tr>

              {/* Row 3: Raw Agent Execution */}
              <tr className="hover:bg-zinc-50/50 transition-colors">
                <td className="py-5 px-6">
                  <div className="font-semibold text-zinc-900">Unrestricted Agent (No Guardrails)</div>
                  <div className="text-xs text-zinc-500">Raw shell execution tool</div>
                </td>
                <td className="py-5 px-6 text-red-600 font-medium">
                  <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-red-50 text-xs">
                    <XCircle className="w-3.5 h-3.5" /> 0% (Catastrophic)
                  </span>
                </td>
                <td className="py-5 px-6 font-mono text-red-600 font-semibold">
                  Complete Data Loss
                </td>
                <td className="py-5 px-6 text-zinc-500">
                  None
                </td>
                <td className="py-5 px-6 text-zinc-500">
                  Impossible
                </td>
              </tr>

            </tbody>
          </table>
        </div>

      </div>
    </section>
  );
};
