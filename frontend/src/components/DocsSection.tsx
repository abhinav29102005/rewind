import React, { useState } from 'react';
import { Copy, CheckCircle, Terminal, ChevronRight, Monitor, Code2, Wind, Plug, Download, ShieldCheck, Zap, Sparkles } from 'lucide-react';

type TabId = 'antigravity' | 'vscode' | 'claude' | 'cursor' | 'windsurf' | 'zed' | 'any';

interface TabConfig {
  id: TabId;
  label: string;
  icon: React.ReactNode;
  configPath: string;
  configPathMac?: string;
  cliCmd: string;
  description: string;
  extraNote?: string;
  perProject?: string;
  jsonConfig?: string;
}

const TABS: TabConfig[] = [
  {
    id: 'antigravity',
    label: 'Antigravity (AGY)',
    icon: <Sparkles className="w-4 h-4 text-cyan-400" />,
    configPath: '~/.gemini/config/mcp_config.json',
    configPathMac: '~/.gemini/config/mcp_config.json',
    cliCmd: './scripts/setup-agent.sh --agent antigravity',
    description: 'Natively connect Rewind to Google Antigravity IDE. Automatically secures the agent loop, CLI commands, and subagent workflows.',
    extraNote: 'Works with both global (~/.gemini/config/mcp_config.json) and workspace (.agents/mcp_config.json) configurations.',
    perProject: 'Also auto-installs the Rewind Guard extension into the Antigravity editor for pending approval badges.',
  },
  {
    id: 'vscode',
    label: 'VS Code & Roo/Cline',
    icon: <Code2 className="w-4 h-4 text-blue-400" />,
    configPath: '~/.config/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/cline_mcp_settings.json',
    configPathMac: '~/Library/Application Support/Code/User/globalStorage/rooveterinaryinc.roo-cline/settings/cline_mcp_settings.json',
    cliCmd: './scripts/setup-agent.sh --agent vscode',
    description: 'Installs the Rewind VS Code Extension (.vsix) and configures MCP guardrails for Roo Code, Cline, and Copilot Chat.',
    extraNote: 'Run: code --install-extension vscode-extension/rewind-guard-0.1.0.vsix to install the sidebar approval UI.',
  },
  {
    id: 'cursor',
    label: 'Cursor',
    icon: <Terminal className="w-4 h-4" />,
    configPath: '~/.config/Cursor/User/globalStorage/cursor.mcp/config.json',
    configPathMac: '~/Library/Application Support/Cursor/User/globalStorage/cursor.mcp/config.json',
    cliCmd: './scripts/setup-agent.sh --agent cursor',
    description: 'Add Rewind as an MCP server to Cursor so every destructive action by the AI agent requires your approval — right inside the chat.',
    perProject: 'You can also scope it per-project by creating a .cursor/mcp.json in any project root (run: ./scripts/setup-agent.sh --agent cursor-project).',
  },
  {
    id: 'claude',
    label: 'Claude Desktop',
    icon: <Monitor className="w-4 h-4" />,
    configPath: '~/.config/Claude/claude_desktop_config.json',
    configPathMac: '~/Library/Application Support/Claude/claude_desktop_config.json',
    cliCmd: './scripts/setup-agent.sh --agent claude',
    description: 'Connect Rewind to Claude Desktop so every dangerous action your AI takes is intercepted and approved — directly in the chat window.',
    extraNote: 'Restart Claude Desktop after saving the config to load the Rewind MCP server.',
  },
  {
    id: 'windsurf',
    label: 'Windsurf',
    icon: <Wind className="w-4 h-4" />,
    configPath: '~/.codeium/windsurf/mcp_config.json',
    cliCmd: './scripts/setup-agent.sh --agent windsurf',
    description: "Connect Rewind to Windsurf's Cascade agent via MCP to enforce approval gates on dangerous operations.",
    extraNote: 'Restart Windsurf to refresh Cascade MCP connections.',
  },
  {
    id: 'zed',
    label: 'Zed Editor',
    icon: <Zap className="w-4 h-4" />,
    configPath: '~/.config/zed/settings.json',
    cliCmd: './scripts/setup-agent.sh --agent zed',
    description: "Connect Rewind to Zed's assistant context servers for native command execution guardrails.",
    extraNote: 'Added under the context_servers key in Zed settings.',
    jsonConfig: `{
  "context_servers": {
    "rewind-guard": {
      "command": {
        "path": "uv",
        "args": ["--directory", "/path/to/rewind", "run", "rewind-mcp"]
      }
    }
  }
}`
  },
  {
    id: 'any',
    label: 'Any MCP Client',
    icon: <Plug className="w-4 h-4" />,
    configPath: 'your-agent/mcp_config.json',
    cliCmd: './scripts/setup-agent.sh --print',
    description: 'Rewind runs as a standard MCP server on stdio. Any agent or client that speaks MCP connects seamlessly.',
  },
];

const STANDARD_MCP_CONFIG = `{
  "mcpServers": {
    "rewind-guard": {
      "command": "uv",
      "args": [
        "--directory",
        "/path/to/rewind",
        "run",
        "rewind-mcp"
      ]
    }
  }
}`;

const TOOLS_REF = [
  { name: 'execute_command', args: 'command, session_id?', desc: 'Run a shell command through the guardrail pipeline. Classifies as safe/reversible/irreversible.' },
  { name: 'approve_request', args: 'request_id', desc: 'Approve a blocked destructive action directly from the chat prompt.' },
  { name: 'execute_approved_command', args: 'request_id', desc: 'Execute a previously approved action with cryptographic hash verification.' },
  { name: 'preview_rollback', args: 'snapshot_id', desc: 'Show the git file diff that would be restored by rolling back to a snapshot.' },
  { name: 'rollback_snapshot', args: 'snapshot_id', desc: 'Restore filesystem state cleanly to the pre-action checkpoint.' },
];

const POLICY_PACKS = [
  { name: 'Filesystem', examples: 'rm -rf, shred, dd, chmod 777', risk: 'Irreversible / Reversible', mitigation: 'Automatic Git snapshot or block' },
  { name: 'Database (SQL)', examples: 'DROP TABLE, TRUNCATE, DELETE without WHERE', risk: 'Irreversible', mitigation: 'Block until human approval in chat' },
  { name: 'Git Operations', examples: 'git push --force, git reset --hard', risk: 'Irreversible', mitigation: 'Protected branch consensus check' },
  { name: 'Cloud Infrastructure', examples: 'aws ec2 terminate, terraform destroy', risk: 'Irreversible', mitigation: 'Credential brokerage & multi-party gate' },
  { name: 'Docker / Containers', examples: 'docker rm -f, docker system prune -af', risk: 'Irreversible', mitigation: 'Halt daemon commands & log audit chain' },
];

const CLI_COMMANDS = [
  { cmd: 'uv run rewind --help', desc: 'Show all CLI commands' },
  { cmd: 'uv run rewind integrate', desc: 'Interactive agent incorporation wizard' },
  { cmd: 'uv run rewind integrate --agent antigravity', desc: 'Directly connect Antigravity IDE to Rewind' },
  { cmd: 'uv run rewind integrate --agent cursor', desc: 'Directly connect Cursor to Rewind' },
  { cmd: 'uv run rewind-mcp', desc: 'Start the MCP guardrail server on stdio' },
  { cmd: 'uv run rewind policy list', desc: 'Show loaded policy packs and rule counts' },
  { cmd: 'uv run rewind policy test --tool shell "rm -rf /"', desc: 'Test classification of any shell or SQL statement' },
  { cmd: 'uv run rewind session start', desc: 'Start a new team-audited session' },
  { cmd: 'uv run rewind rollback <snapshot_id>', desc: 'Restore files from a snapshot checkpoint' },
];

export const DocsSection: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabId>('antigravity');
  const [copiedConfig, setCopiedConfig] = useState(false);
  const [copiedInstall, setCopiedInstall] = useState(false);
  const [copiedAgentCmd, setCopiedAgentCmd] = useState(false);

  const tab = TABS.find(t => t.id === activeTab)!;
  const configText = tab.jsonConfig || STANDARD_MCP_CONFIG;

  const copyConfig = () => {
    navigator.clipboard.writeText(configText);
    setCopiedConfig(true);
    setTimeout(() => setCopiedConfig(false), 2000);
  };

  const installCmd = 'curl -fsSL https://raw.githubusercontent.com/abhinav29102005/rewind/main/install.sh | bash';
  const copyInstall = () => {
    navigator.clipboard.writeText(installCmd);
    setCopiedInstall(true);
    setTimeout(() => setCopiedInstall(false), 2000);
  };

  const copyAgentCmd = () => {
    navigator.clipboard.writeText(tab.cliCmd);
    setCopiedAgentCmd(true);
    setTimeout(() => setCopiedAgentCmd(false), 2000);
  };

  return (
    <section id="docs" className="py-20 bg-zinc-950 text-white border-t border-zinc-800">
      <div className="max-w-6xl mx-auto px-6">

        {/* ── Section Header ── */}
        <div className="text-center mb-16">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-blue-500/10 border border-blue-500/20 text-blue-400 text-xs font-semibold mb-4">
            <ShieldCheck className="w-3.5 h-3.5" />
            Complete Documentation &amp; Setup Guide
          </div>
          <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight mb-4">
            Connect Rewind to Any Agent
          </h2>
          <p className="text-zinc-400 max-w-2xl mx-auto text-base">
            Rewind acts as an overlay between your AI agent and the operating system.
            Choose your IDE or agent below to configure it in seconds.
          </p>
        </div>

        {/* ── One-Command Install Banner ── */}
        <div className="bg-gradient-to-r from-blue-950/60 to-zinc-900 border border-blue-500/30 rounded-2xl p-6 mb-12 flex flex-col md:flex-row items-center justify-between gap-4">
          <div className="flex-1">
            <div className="text-xs font-semibold uppercase tracking-wider text-blue-400 mb-1">One-Command Install</div>
            <div className="font-mono text-sm text-zinc-200 bg-black/50 px-4 py-2.5 rounded-lg border border-zinc-700/60 break-all select-all">
              {installCmd}
            </div>
            <div className="text-xs text-zinc-400 mt-2 flex items-center gap-2">
              <span>Checks Python &ge; 3.11</span>
              <span>•</span>
              <span>Installs uv &amp; dependencies</span>
              <span>•</span>
              <span>Configures your agent</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={copyInstall}
              className="px-5 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-medium text-sm flex items-center gap-2 transition-all shrink-0 shadow-lg shadow-blue-600/20 active:scale-95"
            >
              {copiedInstall ? <CheckCircle className="w-4 h-4 text-emerald-300" /> : <Copy className="w-4 h-4" />}
              <span>{copiedInstall ? 'Copied!' : 'Copy Installer'}</span>
            </button>
            <a
              href="https://raw.githubusercontent.com/abhinav29102005/rewind/main/install.sh"
              download="install.sh"
              className="px-4 py-3 rounded-xl bg-zinc-800 hover:bg-zinc-700 text-zinc-200 font-medium text-sm flex items-center gap-2 border border-zinc-700 transition-colors shrink-0"
              title="Download install.sh script directly"
            >
              <Download className="w-4 h-4" />
              <span className="hidden sm:inline">Download .sh</span>
            </a>
          </div>
        </div>

        {/* ── Agent Tabs ── */}
        <div className="flex flex-wrap gap-2 mb-8 p-1.5 bg-zinc-900 rounded-xl border border-zinc-800 max-w-full">
          {TABS.map(t => (
            <button
              key={t.id}
              onClick={() => setActiveTab(t.id)}
              className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-all ${
                activeTab === t.id
                  ? 'bg-blue-600 text-white shadow-sm'
                  : 'text-zinc-400 hover:text-white hover:bg-zinc-800/60'
              }`}
            >
              {t.icon}
              <span>{t.label}</span>
            </button>
          ))}
        </div>

        {/* ── Tab Content Card ── */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-2xl p-6 sm:p-8 mb-16 shadow-xl">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-6 pb-6 border-b border-zinc-800">
            <div>
              <h3 className="text-xl font-bold text-white flex items-center gap-2.5">
                {tab.icon}
                <span>Setup for {tab.label}</span>
              </h3>
              <p className="text-zinc-400 text-sm mt-1">{tab.description}</p>
            </div>
            
            {/* Quick CLI Incorporator */}
            <div className="bg-zinc-950 border border-zinc-800 px-3.5 py-2 rounded-xl flex items-center gap-3">
              <span className="text-xs text-zinc-500 font-mono">1-Click CLI:</span>
              <code className="text-xs font-mono text-cyan-300">{tab.cliCmd}</code>
              <button
                onClick={copyAgentCmd}
                className="text-zinc-400 hover:text-white transition-colors p-1"
                title="Copy incorporation command"
              >
                {copiedAgentCmd ? <CheckCircle className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              </button>
            </div>
          </div>

          {/* Config file path */}
          <div className="mb-6 space-y-2">
            <div className="text-xs font-semibold uppercase tracking-wider text-zinc-400">Configuration Location</div>
            <div className="font-mono text-xs bg-zinc-950 text-zinc-300 p-3 rounded-lg border border-zinc-800 select-all">
              <span className="text-zinc-500">Config:</span> {tab.configPath}
              {tab.configPathMac && tab.configPathMac !== tab.configPath && (
                <>
                  <br />
                  <span className="text-zinc-500">macOS:</span> {tab.configPathMac}
                </>
              )}
            </div>
          </div>

          {/* JSON snippet */}
          <div className="mb-6">
            <div className="flex items-center justify-between mb-2">
              <span className="text-xs font-semibold uppercase tracking-wider text-zinc-400">Add to config file</span>
              <button
                onClick={copyConfig}
                className="flex items-center gap-1.5 text-xs text-blue-400 hover:text-blue-300 transition-colors font-medium"
              >
                {copiedConfig ? <CheckCircle className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
                <span>{copiedConfig ? 'Copied to clipboard!' : 'Copy JSON'}</span>
              </button>
            </div>
            <pre className="bg-zinc-950 p-4 rounded-xl text-xs font-mono text-emerald-400 border border-zinc-800 overflow-x-auto leading-relaxed">
              <code>{configText}</code>
            </pre>
          </div>

          {/* Notes */}
          <div className="space-y-2 text-sm text-zinc-400">
            {tab.extraNote && (
              <p className="flex items-start gap-2 text-amber-300/90 bg-amber-950/20 border border-amber-800/30 p-3 rounded-lg text-xs">
                <span className="mt-0.5">ℹ</span> {tab.extraNote}
              </p>
            )}
            {tab.perProject && (
              <p className="flex items-start gap-2 text-zinc-400 text-xs bg-zinc-950/50 p-3 rounded-lg border border-zinc-800/50">
                <span className="mt-0.5">📁</span> {tab.perProject}
              </p>
            )}
          </div>
        </div>

        {/* ── How It Works Flow ── */}
        <div className="mb-16">
          <h3 className="text-lg font-bold mb-6 flex items-center gap-2">
            <ChevronRight className="w-5 h-5 text-cyan-400" />
            How It Works in Your Chat &amp; IDE
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[
              { step: '1', title: 'Agent Acts', desc: 'You ask your AI to run an action (e.g. "delete production records" or "purge docker")', color: 'bg-zinc-900' },
              { step: '2', title: 'Rewind Intercepts', desc: 'Rewind policy engine halts the syscall before execution and evaluates risk.', color: 'bg-zinc-900' },
              { step: '3', title: 'Approval in Chat & UI', desc: 'If irreversible, the agent tells you the exact rule and requests human consent or VS Code badge click.', color: 'bg-zinc-900' },
              { step: '4', title: 'Undo & Audit', desc: 'On approval, executes and records to tamper-evident SHA-256 WAL. Instant rollback ready.', color: 'bg-zinc-900' },
            ].map(s => (
              <div key={s.step} className={`${s.color} rounded-xl p-5 border border-zinc-800`}>
                <div className="w-8 h-8 rounded-lg bg-blue-500/10 text-blue-400 flex items-center justify-center text-sm font-bold mb-3">
                  {s.step}
                </div>
                <h4 className="font-semibold text-white mb-1">{s.title}</h4>
                <p className="text-zinc-400 text-sm leading-relaxed">{s.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* ── Policy Packs Reference ── */}
        <div className="mb-16">
          <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
            <ShieldCheck className="w-5 h-5 text-emerald-400" />
            Built-In Policy Packs
          </h3>
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-800 text-zinc-400 text-xs uppercase tracking-wider">
                  <th className="text-left p-4 font-semibold">Policy Domain</th>
                  <th className="text-left p-4 font-semibold">Matched Patterns</th>
                  <th className="text-left p-4 font-semibold hidden sm:table-cell">Risk Level</th>
                  <th className="text-left p-4 font-semibold">Mitigation Strategy</th>
                </tr>
              </thead>
              <tbody>
                {POLICY_PACKS.map(p => (
                  <tr key={p.name} className="border-b border-zinc-800/50 hover:bg-zinc-800/30 transition-colors">
                    <td className="p-4 font-semibold text-white text-xs">{p.name}</td>
                    <td className="p-4 font-mono text-zinc-300 text-xs">{p.examples}</td>
                    <td className="p-4 text-xs hidden sm:table-cell">
                      <span className="px-2 py-0.5 rounded-full bg-red-950/60 text-red-400 border border-red-800/40 font-mono">
                        {p.risk}
                      </span>
                    </td>
                    <td className="p-4 text-zinc-400 text-xs">{p.mitigation}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* ── MCP Tools Reference ── */}
        <div className="mb-16">
          <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
            <Terminal className="w-5 h-5 text-purple-400" />
            MCP Tools Reference
          </h3>
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-zinc-800 text-zinc-400 text-xs uppercase tracking-wider">
                  <th className="text-left p-4 font-semibold">Tool</th>
                  <th className="text-left p-4 font-semibold hidden sm:table-cell">Arguments</th>
                  <th className="text-left p-4 font-semibold">Description</th>
                </tr>
              </thead>
              <tbody>
                {TOOLS_REF.map(t => (
                  <tr key={t.name} className="border-b border-zinc-800/50 hover:bg-zinc-800/30 transition-colors">
                    <td className="p-4 font-mono text-blue-300 text-xs whitespace-nowrap">{t.name}</td>
                    <td className="p-4 font-mono text-zinc-500 text-xs hidden sm:table-cell whitespace-nowrap">{t.args}</td>
                    <td className="p-4 text-zinc-300">{t.desc}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* ── CLI Quick Reference ── */}
        <div>
          <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
            <Terminal className="w-5 h-5 text-emerald-400" />
            CLI Quick Reference
          </h3>
          <div className="bg-zinc-900 border border-zinc-800 rounded-xl p-5 font-mono text-sm space-y-3 overflow-x-auto">
            {CLI_COMMANDS.map(c => (
              <div key={c.cmd} className="flex flex-col sm:flex-row sm:items-center gap-1 sm:gap-4">
                <div className="text-zinc-200 whitespace-nowrap">
                  <span className="text-emerald-400">$</span> {c.cmd}
                </div>
                <span className="text-zinc-500 text-xs">{'# ' + c.desc}</span>
              </div>
            ))}
          </div>
        </div>

      </div>
    </section>
  );
};
