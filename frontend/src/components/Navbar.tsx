import React from 'react';
import { Star, ShieldAlert } from 'lucide-react';

export const Navbar: React.FC = () => {
  return (
    <header className="sticky top-0 z-50 backdrop-blur-md bg-[#fcfbfa]/90 border-b border-[#f0ede6]/80 transition-colors">
      <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
        {/* Brand Logo */}
        <a href="#" className="flex items-center gap-2 group">
          <div className="flex items-center gap-1">
            <div className="w-3.5 h-7 rounded-full bg-[#111111] transition-transform group-hover:-translate-y-0.5"></div>
            <div className="w-3.5 h-7 rounded-full bg-[#111111] transition-transform group-hover:translate-y-0.5"></div>
          </div>
          <span className="font-semibold text-xl tracking-tight text-[#111111] flex items-baseline">
            rewind
            <span className="font-serif italic font-normal text-zinc-500 ml-1.5 text-lg">
              (guard)
            </span>
          </span>
        </a>

        {/* Center / Right Links */}
        <nav className="hidden md:flex items-center gap-7 text-[13.5px] font-medium text-zinc-600">
          <a href="#how-it-works" className="hover:text-black transition-colors">
            Solutions
          </a>
          <a href="#simulator" className="hover:text-black transition-colors">
            Interactive Test
          </a>
          <a href="#architecture" className="hover:text-black transition-colors">
            Architecture
          </a>
          <a href="#benchmarks" className="hover:text-black transition-colors">
            Benchmarks
          </a>
          <a href="#ledger" className="hover:text-black transition-colors">
            Ledger
          </a>
        </nav>

        {/* Actions & Social badges */}
        <div className="flex items-center gap-3">
          {/* GitHub Star Badge */}
          <a
            href="https://github.com/abhinav29102005/rewind"
            target="_blank"
            rel="noreferrer"
            className="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full border border-zinc-200 bg-white hover:bg-zinc-50 text-xs font-medium text-zinc-800 transition-colors shadow-sm"
          >
            <svg className="w-4 h-4 fill-current" viewBox="0 0 24 24">
              <path fillRule="evenodd" clipRule="evenodd" d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.53 1.032 1.53 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
            </svg>
            <span className="flex items-center gap-1 font-semibold">
              17.4k <Star className="w-3 h-3 text-amber-500 fill-amber-500" />
            </span>
          </a>

          {/* Control Plane Launch Button */}
          <a
            href="http://127.0.0.1:8787/dashboard"
            target="_blank"
            rel="noreferrer"
            className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-[#111111] hover:bg-black text-white text-xs sm:text-[13px] font-medium shadow-sm transition-transform active:scale-95"
          >
            <ShieldAlert className="w-3.5 h-3.5 text-emerald-400" />
            Control Plane
          </a>
        </div>
      </div>
    </header>
  );
};
