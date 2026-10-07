import React from 'react';
import { ArrowUpRight } from 'lucide-react';

export const TopBanner: React.FC = () => {
  return (
    <div className="w-full pt-3 pb-1 flex justify-center px-4 bg-[#fcfbfa]">
      <a
        href="https://github.com/abhinav29102005/rewind"
        target="_blank"
        rel="noreferrer"
        className="group inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#111111] text-white text-xs sm:text-[13px] font-normal transition-all hover:bg-black hover:scale-[1.01] shadow-pill"
      >
        <span>
          <strong className="font-semibold text-white">rewind</strong>{' '}
          <span className="font-serif italic font-normal text-zinc-300">(guard)</span>{' '}
          is the non-bypassable proxy, making irreversible actions require approval and stay reversible.
        </span>
        <span className="inline-flex items-center gap-0.5 text-zinc-300 font-medium group-hover:text-white group-hover:translate-x-0.5 transition-transform">
          GitHub <ArrowUpRight className="w-3.5 h-3.5" />
        </span>
      </a>
    </div>
  );
};
