import React, { useEffect, useRef, useState, type FormEvent } from "react";
import { createRoot } from "react-dom/client";
import ReactMarkdown from "react-markdown";
import { useAgent } from "agents/react";
import { useAgentChat } from "@cloudflare/ai-chat/react";
import type { UIMessage } from "ai";
import { conversationIdSchema, safeEvidenceHref, type ConversationSummary, type PublicModelProfile, type WorkspaceState } from "../contracts";
import "./style.css";

const LIBRARY = "https://library.lupine.science/#/read/research-index";
type WorkspaceInfo = { id: string; state: WorkspaceState; catalog: { profiles: PublicModelProfile[] } };
type Room = { id: string; title?: string };

function startingRoom(): Room {
  const raw = new URL(location.href).searchParams.get("conversation") ?? "research";
  return { id: conversationIdSchema.safeParse(raw).success ? raw : "research" };
}

class ConversationBoundary extends React.Component<{ children: React.ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() {
    if (this.state.failed) return <main className="workspace-main"><section className="welcome history-failure" role="alert">
      <p className="eyebrow">CONVERSATION CONNECTION</p><h2>Your saved conversation<br />could not load.</h2>
      <p>Check your connection or sign in again, then retry. The saved conversation has not been cleared.</p>
      <button onClick={() => location.reload()}>Retry saved conversation</button> <a href={LIBRARY}>Open Research Library ↗</a>
    </section></main>;
    return this.props.children;
  }
}

function LoadingConversation() {
  return <main className="workspace-main"><section className="welcome history-failure" role="status"><p className="eyebrow">RESEARCH WORKSPACE</p><h2>Opening your<br />saved conversation…</h2><p>Restoring messages and reconnecting to Rhizo.</p></section></main>;
}

function ToolResult({ part }: { part: Record<string, unknown> }) {
  const state = String(part.state ?? "input-streaming");
  const done = state === "output-available";
  const failed = state === "output-error" || state === "output-denied";
  const labels: Record<string, string> = {
    "input-streaming": "Preparing evidence read", "input-available": "Reading saved evidence",
    "output-available": "Evidence read complete", "output-error": "Evidence could not be read",
    "output-denied": "Action unavailable", "approval-requested": "Waiting for approval",
  };
  return <details className={`tool-result ${failed ? "failed" : ""}`}>
    <summary><span aria-hidden="true">{done ? "✓" : failed ? "!" : "◌"}</span> {labels[state] ?? "Tool activity"}</summary>
    <pre>{JSON.stringify(done ? part.output : part.input ?? {}, null, 2).slice(0, 20000)}</pre>
  </details>;
}

function Message({ message }: { message: UIMessage }) {
  return <article className={`message ${message.role}`}>
    <div className="message-label">{message.role === "user" ? "You" : "Rhizo"}</div>
    <div className="message-content">{message.parts.map((part, i) => {
      if (part.type === "text") return <ReactMarkdown key={i}
        urlTransform={(url) => safeEvidenceHref(url) ?? ""}
        components={{ a: ({ children, href }) => href ? <a href={href} target="_blank" rel="noopener noreferrer">{children}</a> : <span>{children}</span>,
          img: ({ alt }) => <span>[Image: {alt ?? "attachment"}]</span> }}
      >{part.text}</ReactMarkdown>;
      if (part.type === "reasoning") return <details className="reasoning" key={i}><summary>Model notes</summary><p>{part.text}</p></details>;
      if (part.type === "dynamic-tool" || part.type.startsWith("tool-")) return <ToolResult key={i} part={part as unknown as Record<string, unknown>} />;
      if (part.type === "source-url") {
        const href = safeEvidenceHref(part.url);
        return href ? <a className="source" key={i} href={href} target="_blank" rel="noopener noreferrer">{part.title ?? "Source"} ↗</a> : null;
      }
      return null;
    })}</div>
  </article>;
}

function Chat({ room, onMetadata }: { room: Room; onMetadata: (entry: ConversationSummary) => void }) {
  const [connected, setConnected] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const [state, setState] = useState<WorkspaceState | null>(null);
  const [catalog, setCatalog] = useState<PublicModelProfile[]>([]);
  const [draft, setDraft] = useState("");
  const [title, setTitle] = useState(room.title ?? "Research conversation");
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const end = useRef<HTMLDivElement>(null);
  const initialTitle = useRef(room.title);
  const agent = useAgent<WorkspaceState>({
    agent: "research-workspace", name: room.id,
    onOpen: () => { setConnected(true); setError(""); setNotice((current) => current === "Reconnecting to your saved conversation…" ? "" : current); },
    onClose: () => setConnected(false),
    onError: () => { setConnected(false); setError("Connection unavailable. Reconnect, or sign in again if your session expired."); },
    onStateUpdate: (next) => { if (next && typeof next.profile === "string") { setState(next); setTitle(next.title); } },
  });
  const chat = useAgentChat({ agent, credentials: "same-origin", resume: true,
    onError: () => setError("This reply could not complete. Your conversation is saved. Check model access, choose another profile, or reconnect."),
  });
  const busy = chat.status === "submitted" || chat.isStreaming;
  const selectedUnavailable = loaded && state?.profile !== "auto" && !catalog.some((profile) => profile.id === state?.profile && profile.configured && profile.role !== "decision");

  useEffect(() => {
    if (!connected) return;
    let active = true;
    void (async () => {
      try {
        const info = await agent.call<WorkspaceInfo>("getWorkspace", []);
        let next = info.state;
        if (initialTitle.current) {
          next = await agent.call<WorkspaceState>("updateWorkspace", [{ title: initialTitle.current, profile: next.profile }]);
          initialTitle.current = undefined;
        }
        if (active) {
          setState(next); setTitle(next.title); setCatalog(info.catalog.profiles); setLoaded(true);
          onMetadata({ id: room.id, title: next.title, updatedAt: next.lastTurnAt ?? new Date().toISOString() });
        }
      } catch { if (active) setError("Workspace could not load. Your sign-in or model configuration may need attention."); }
    })();
    return () => { active = false; };
  }, [connected, room.id]);

  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth", block: "end" }); }, [chat.messages, busy]);

  async function saveSettings(profile: string, newTitle = state?.title ?? title) {
    if (!state || busy) return;
    setSaving(true); setError("");
    try {
      const next = await agent.call<WorkspaceState>("updateWorkspace", [{ title: newTitle, profile }]);
      setState(next); setTitle(next.title); setEditing(false);
      onMetadata({ id: room.id, title: next.title, updatedAt: new Date().toISOString() });
    } catch { setError("Settings were not saved. Choose a configured chat profile and a name up to 80 characters."); }
    finally { setSaving(false); }
  }

  async function send(event: FormEvent) {
    event.preventDefault();
    const text = draft.trim();
    if (!text || !connected || !loaded || busy || saving) return;
    setDraft(""); setError(""); setNotice("");
    try { await chat.sendMessage({ text }); }
    catch { setDraft(text); setError("The message could not be sent. Reconnect and try again."); }
  }

  async function copyLink() {
    try { await navigator.clipboard.writeText(location.href); setNotice("Conversation link copied. Open it on another signed-in device."); }
    catch { setNotice("Use this page’s address to reopen this conversation on another signed-in device."); }
  }

  return <main className="workspace-main">
    <header className="conversation-header">
      <div><p className="eyebrow">RESEARCH WORKSPACE</p>
        {editing ? <form onSubmit={(e) => { e.preventDefault(); void saveSettings(state?.profile ?? "workers-flash", title); }} className="rename-form">
          <input aria-label="Conversation name" maxLength={80} value={title} onChange={(e) => setTitle(e.target.value)} autoFocus />
          <button disabled={saving || !title.trim()}>Save</button><button type="button" onClick={() => { setTitle(state?.title ?? title); setEditing(false); }}>Cancel</button>
        </form> : <h1><button className="title-button" disabled={!loaded || busy} title="Rename conversation" onClick={() => setEditing(true)}>{state?.title ?? room.title ?? "Research conversation"} <span>↗</span></button></h1>}
        <span className={`connection ${connected ? "online" : ""}`}><i />{connected ? loaded ? "Connected · conversation saved" : "Loading conversation" : "Reconnecting"}</span>
      </div>
      <div className="header-actions"><button className="quiet" onClick={() => void copyLink()}>Copy link</button><button className="quiet" onClick={() => { setNotice("Reconnecting to your saved conversation…"); agent.reconnect(); }}>Reconnect</button></div>
    </header>

    <section className="model-bar" aria-label="Model selection">
      <label>Reply profile<select value={state?.profile ?? "workers-flash"} disabled={!loaded || saving || busy} onChange={(e) => void saveSettings(e.target.value)}>
        {catalog.length === 0 && <option value="workers-flash">Loading models…</option>}
        {catalog.length > 0 && <option value="auto">Auto · decision routing</option>}
        {state && catalog.length > 0 && state.profile !== "auto" && !catalog.some((profile) => profile.id === state.profile) && <option value={state.profile} disabled>{state.profile} · unavailable</option>}
        {catalog.filter((p) => p.role !== "decision").map((p) => <option key={p.id} value={p.id} disabled={!p.configured}>{p.label}{!p.configured ? " · not configured" : ""}</option>)}
      </select></label>
      <div className="model-identity"><span>{state?.provider ?? "Model provider"}</span><strong>{state?.modelId ?? "Waiting for configuration"}</strong></div>
      <span className="permission-pill">Evidence reads only</span>
    </section>
    <div className="routing-note">Model access is checked when you send.{state?.routing && <> Last selection: {state.routing.mode} · {state.routing.profileId}{state.routing.confidence !== undefined ? ` · ${Math.round(state.routing.confidence * 100)}% classifier confidence` : ""}. {state.routing.reason}
      {state.routing.suggestedProfileId && <> Suggested: {state.routing.suggestedProfileId}.</>}
      {state.routing.task && <> Task: {state.routing.task}.</>}
      {state.routing.margin !== undefined && <> Margin: {Math.round(state.routing.margin * 100)}%.</>}
      {state.routing.contextTruncated && <> Decision used the first 2,000 characters.</>}
    </>}</div>
    {notice && <div className="notice" role="status">{notice}</div>}
    {selectedUnavailable && <div className="notice" role="status">This conversation’s selected profile is unavailable. Choose a configured reply profile to continue.</div>}
    {error && <div className="error" role="alert">{error}</div>}

    <section className="conversation" aria-label="Conversation" aria-busy={busy}>
      {chat.messages.length === 0 && <div className="welcome">
        <div className="seed-mark" aria-hidden="true">✳</div><p className="eyebrow">A PLACE TO THINK TOGETHER</p>
        <h2>Follow the evidence.<br />Find the next good question.</h2>
        <p>Explore the research already in Rhizo, compare competing explanations, and turn open questions into a clear plan.</p>
        <div className="starter-grid">{[
          "What are our current hypotheses, and what evidence would distinguish them?",
          "Show me the latest recorded lab activity. Separate reported progress from verified outcomes.",
          "Which saved papers are most useful for our next research question?",
        ].map((prompt) => <button key={prompt} onClick={() => setDraft(prompt)}>{prompt}<span>↗</span></button>)}</div>
      </div>}
      {chat.messages.map((message) => <Message key={message.id} message={message} />)}
      {busy && <div className="working" role="status"><span />{chat.status === "submitted" ? "Preparing a reply…" : "Rhizo is working…"}</div>}
      <div ref={end} />
    </section>
    <footer className="composer-region">
      <form className="composer" onSubmit={send}>
        <textarea aria-label="Message Rhizo" placeholder="Ask a research question, challenge a claim, or explore an idea…" value={draft} maxLength={16000}
          onChange={(e) => setDraft(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); if (!busy) e.currentTarget.form?.requestSubmit(); } }} rows={3} />
        <div className="composer-actions"><span>Enter to send · Shift + Enter for a new line</span>{busy ? <button type="button" className="stop" onClick={() => void chat.stop()}>Stop reply</button> : <button disabled={!connected || !loaded || saving || !draft.trim()} type="submit">Send <span aria-hidden="true">↑</span></button>}</div>
      </form>
      <p className="composer-note">Uses the selected provider when you send. No experiments or compute jobs are started from this workspace.</p>
    </footer>
  </main>;
}

function App() {
  const [room, setRoom] = useState<Room>(startingRoom);
  const [conversations, setConversations] = useState<ConversationSummary[]>([]);
  const [newName, setNewName] = useState("");
  const [listError, setListError] = useState("");

  async function refresh() {
    try {
      const response = await fetch("/workspace/conversations", { credentials: "same-origin" });
      if (!response.ok) throw new Error("unavailable");
      const data = await response.json() as { conversations: ConversationSummary[]; truncated: boolean };
      setConversations(data.conversations); setListError(data.truncated ? "Showing the first 100 saved conversations. A copied link can still open another." : "");
    } catch { setListError("Saved conversations are unavailable. Sign in or refresh to try again."); }
  }
  useEffect(() => { void refresh(); }, []);
  useEffect(() => {
    const handler = () => setRoom(startingRoom());
    window.addEventListener("popstate", handler);
    return () => window.removeEventListener("popstate", handler);
  }, []);

  function openRoom(next: Room) {
    const url = new URL(location.href); url.searchParams.set("conversation", next.id);
    history.pushState(null, "", url); setRoom(next);
  }
  function remember(entry: ConversationSummary) {
    setConversations((items) => [entry, ...items.filter((item) => item.id !== entry.id)].slice(0, 100));
  }
  return <div className="app-shell">
    <aside className="sidebar">
      <a href="/workspace" className="brand"><span>✳</span><div>Lupine <em>Rhizo</em><small>RESEARCH, CONNECTED</small></div></a>
      <nav className="destinations" aria-label="Research navigation"><a className="selected" href="/workspace">Workspace <span>↗</span></a><a href={LIBRARY} target="_blank" rel="noopener noreferrer">Research Library <span>↗</span></a><a href="/live">Live evidence <span>↗</span></a></nav>
      <div className="sidebar-heading"><h2>Conversations</h2><button className="icon-button" title="Refresh saved conversations" aria-label="Refresh saved conversations" onClick={() => void refresh()}>↻</button></div>
      <form className="new-conversation" onSubmit={(e) => { e.preventDefault(); if (newName.trim()) { openRoom({ id: crypto.randomUUID(), title: newName.trim() }); setNewName(""); } }}>
        <input aria-label="New conversation name" placeholder="Name a new conversation" maxLength={80} value={newName} onChange={(e) => setNewName(e.target.value)} /><button disabled={!newName.trim()} aria-label="Create conversation">+</button>
      </form>
      {listError && <p className="sidebar-note" role="status">{listError}</p>}
      <nav className="conversation-list" aria-label="Saved conversations">{conversations.map((item) => <button key={item.id} className={room.id === item.id ? "active" : ""} onClick={() => openRoom({ id: item.id })}><span>{item.title}</span><small>{new Date(item.updatedAt).toLocaleDateString(undefined, { month: "short", day: "numeric" })}</small></button>)}</nav>
      <div className="sidebar-footer"><i /><span>A shared, durable notebook.<br />Pick up on any signed-in device.</span></div>
    </aside>
    <ConversationBoundary key={room.id}><React.Suspense fallback={<LoadingConversation />}><Chat room={room} onMetadata={remember} /></React.Suspense></ConversationBoundary>
  </div>;
}

createRoot(document.getElementById("root")!).render(<App />);
