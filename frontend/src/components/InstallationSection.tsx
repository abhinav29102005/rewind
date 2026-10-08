import React, { useState } from 'react';
import { Terminal, Copy, CheckCircle } from 'lucide-react';

export const InstallationSection: React.FC = () => {
  const [copied, setCopied] = useState(false);

  const configStr = `{
  "mcpServers": {
    "rewind-guard": {
      "command": "uv",
      "args": ["run", "rewind-mcp"],
      "env": {
        "REWIND_DB_PATH": "/absolute/path/to/audit.db"
      }
    }
  }
}`;

  const copyToClipboard = () => {
    navigator.clipboard.writeText(configStr);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <section id="installation" className="py-24 bg-zinc-950 text-white flex justify-center">
      <div className="max-w-4xl w-full px-6 flex flex-col items-center">
        <h2 className="text-3xl font-bold mb-6 tracking-tight text-center">Install the Native MCP Overlay</h2>
        <p className="text-zinc-400 text-center mb-10 max-w-2xl text-lg">
          Connect Rewind directly to Claude Desktop, Cursor, or any MCP-compatible agent. The security guardrails will run completely inside your chat natively.
        </p>

        <div className="w-full bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden shadow-2xl">
          <div className="flex items-center justify-between px-4 py-3 bg-zinc-800/50 border-b border-zinc-800">
            <div className="flex items-center gap-2">
              <Terminal className="w-4 h-4 text-zinc-400" />
              <span className="font-mono text-sm text-zinc-300">claude_desktop_config.json</span>
            </div>
            <button 
              onClick={copyToClipboard}
              className="flex items-center gap-1.5 text-xs font-medium text-zinc-400 hover:text-white transition-colors"
            >
              {copied ? <CheckCircle className="w-4 h-4 text-emerald-400" /> : <Copy className="w-4 h-4" />}
              {copied ? 'Copied!' : 'Copy'}
            </button>
          </div>
          <div className="p-6 overflow-x-auto">
            <pre className="font-mono text-sm text-blue-300">
              <code>{configStr}</code>
            </pre>
          </div>
        </div>

        <div className="mt-12 grid grid-cols-1 md:grid-cols-3 gap-8 text-center">
          <div>
            <div className="w-12 h-12 bg-blue-500/10 text-blue-400 rounded-xl flex items-center justify-center mx-auto mb-4 text-xl font-bold">1</div>
            <h3 className="text-lg font-semibold mb-2">Install Package</h3>
            <p className="text-sm text-zinc-400">Run <code className="text-blue-300 bg-blue-500/10 px-1 rounded">uv pip install -e .</code> in the rewind directory.</p>
          </div>
          <div>
            <div className="w-12 h-12 bg-blue-500/10 text-blue-400 rounded-xl flex items-center justify-center mx-auto mb-4 text-xl font-bold">2</div>
            <h3 className="text-lg font-semibold mb-2">Configure Client</h3>
            <p className="text-sm text-zinc-400">Paste the JSON configuration into your Claude Desktop or Cursor MCP settings.</p>
          </div>
          <div>
            <div className="w-12 h-12 bg-blue-500/10 text-blue-400 rounded-xl flex items-center justify-center mx-auto mb-4 text-xl font-bold">3</div>
            <h3 className="text-lg font-semibold mb-2">Chat Natively</h3>
            <p className="text-sm text-zinc-400">When an agent tries something dangerous, you will be prompted for approval in chat!</p>
          </div>
        </div>

      </div>
    </section>
  );
};
