import React from 'react';
import { ArrowUpRight } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-[#fcfbfa] border-t border-zinc-200/80 pt-16 pb-12">
      <div className="max-w-7xl mx-auto px-6">
        
        <div className="grid grid-cols-1 md:grid-cols-5 gap-10 mb-16">
          
          {/* Brand Col */}
          <div className="md:col-span-2">
            <div className="flex items-center gap-2 mb-4">
              <div className="flex items-center gap-1">
                <div className="w-3.5 h-7 rounded-full bg-[#111111]"></div>
                <div className="w-3.5 h-7 rounded-full bg-[#111111]"></div>
              </div>
              <span className="font-semibold text-xl tracking-tight text-[#111111] flex items-baseline">
                rewind
                <span className="font-serif italic font-normal text-zinc-500 ml-1.5 text-lg">
                  (guard)
                </span>
              </span>
            </div>
            <p className="text-sm text-zinc-500 max-w-sm mb-6 leading-relaxed">
              An enforced approval and undo layer for AI agents. Making irreversible actions require consensus and stay reversible — outside the agent&apos;s control.
            </p>
            <div className="text-xs text-zinc-400">
              Apache 2.0 Open Source License • Built for autonomous workflows.
            </div>
          </div>

          {/* Nav Col 1 */}
          <div>
            <h4 className="text-xs font-semibold text-zinc-900 uppercase tracking-wider mb-4">
              Product
            </h4>
            <ul className="space-y-2.5 text-sm text-zinc-600">
              <li><a href="#how-it-works" className="hover:text-black transition-colors">Architecture</a></li>
              <li><a href="#simulator" className="hover:text-black transition-colors">Interactive Test</a></li>
              <li><a href="#benchmarks" className="hover:text-black transition-colors">Benchmarks</a></li>
              <li><a href="#docs" className="hover:text-black transition-colors">Docs & Install</a></li>
            </ul>
          </div>

          {/* Nav Col 2 */}
          <div>
            <h4 className="text-xs font-semibold text-zinc-900 uppercase tracking-wider mb-4">
              Integrations
            </h4>
            <ul className="space-y-2.5 text-sm text-zinc-600">
              <li><a href="#docs" className="hover:text-black transition-colors">Claude Desktop</a></li>
              <li><a href="#docs" className="hover:text-black transition-colors">Cursor</a></li>
              <li><a href="#docs" className="hover:text-black transition-colors">Windsurf</a></li>
              <li><a href="#docs" className="hover:text-black transition-colors">Any MCP Client</a></li>
            </ul>
          </div>

          {/* Nav Col 3 */}
          <div>
            <h4 className="text-xs font-semibold text-zinc-900 uppercase tracking-wider mb-4">
              Resources
            </h4>
            <ul className="space-y-2.5 text-sm text-zinc-600">
              <li><a href="https://github.com/abhinav29102005/rewind" target="_blank" rel="noreferrer" className="hover:text-black transition-colors flex items-center gap-1">GitHub <ArrowUpRight className="w-3 h-3" /></a></li>
              <li><a href="#docs" className="hover:text-black transition-colors">CLI Reference</a></li>
              <li><a href="#docs" className="hover:text-black transition-colors">MCP Tools Ref</a></li>
              <li><a href="https://github.com/abhinav29102005/rewind/blob/main/PLAN.md" target="_blank" rel="noreferrer" className="hover:text-black transition-colors flex items-center gap-1">Roadmap <ArrowUpRight className="w-3 h-3" /></a></li>
            </ul>
          </div>

        </div>

        {/* Bottom Bar */}
        <div className="pt-8 border-t border-zinc-200/60 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-zinc-500">
          <div>
            © {new Date().getFullYear()} Rewind Contributors. All rights reserved.
          </div>
          <div className="flex items-center gap-6">
            <span className="font-serif italic text-zinc-400">Prompts are advice. Rewind is physics.</span>
          </div>
        </div>

      </div>
    </footer>
  );
};
