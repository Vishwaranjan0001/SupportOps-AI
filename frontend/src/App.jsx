import { useEffect, useRef, useState } from 'react';
import { api, post } from './api';

const suggestions = [
  ['📦', 'Track my order', 'Where is my order ORD-1001?'],
  ['↩', 'Request a refund', 'Please request a refund for ORD-1003. I changed my mind.'],
  ['📚', 'Ask a policy question', 'Can I return a damaged item after 5 days?'],
];

export default function App() {
  const [chatId, setChatId] = useState('');
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [orders, setOrders] = useState([]);
  const [refunds, setRefunds] = useState([]);
  const [managerOpen, setManagerOpen] = useState(false);
  const [activePanel, setActivePanel] = useState('orders');
  const [tools, setTools] = useState([]);
  const [online, setOnline] = useState(false);
  const bottom = useRef(null);

  async function refresh() {
    const [a, b] = await Promise.all([api('/api/orders'), api('/api/refunds')]);
    setOrders(a.orders); setRefunds(b.refunds);
  }

  async function openChat(id) {
    setChatId(id);
    localStorage.setItem('supportops_chat', id);
    const history = await api(`/api/conversations/${id}/messages`);
    setMessages(history.messages);
  }

  async function newChat() {
    const chat = await post('/api/conversations');
    await openChat(chat.conversation_id);
    setTools([]);
  }

  useEffect(() => {
    async function start() {
      try {
        await api('/health');
        setOnline(true);
        await refresh();
        const previous = localStorage.getItem('supportops_chat');
        if (previous) {
          try { await openChat(previous); return; } catch { /* Old chat ID? Start fresh. */ }
        }
        await newChat();
      } catch (err) {
        setError('Backend unavailable. Start FastAPI first. ' + err.message);
      }
    }
    start();
  }, []);

  useEffect(() => { bottom.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, busy]);

  async function send(question) {
    const text = (question ?? draft).trim();
    if (!text || busy || !chatId) return;
    setDraft(''); setError(''); setBusy(true); setTools([]);
    setMessages(current => [...current, { role: 'user', text }]);
    try {
      const result = await post('/api/chat', { conversation_id: chatId, message: text });
      setMessages(current => [...current, { role: 'assistant', text: result.reply }]);
      setTools(result.tools_used || []);
      await refresh();
    } catch (err) {
      setError(err.message);
      setMessages(current => [...current, { role: 'assistant', text: 'Sorry, I could not connect to the agent. Please check the backend terminal.' }]);
    } finally {
      setBusy(false);
    }
  }

  async function decide(id, approve) {
    try {
      await post(`/api/manager/refunds/${id}`, { approve });
      await refresh();
    } catch (err) { setError(err.message); }
  }

  return (
    <div className="page">
      <aside className="sidebar">
        <div className="brand"><span className="logo">◈</span><div><strong>SupportOps <span>AI</span></strong><small>Agent engineering project</small></div></div>
        <button className="new-chat" onClick={() => newChat().catch(err => setError(err.message))}>＋ &nbsp; New conversation</button>
        <p className="overline">WORKSPACE</p>
        <div className="nav-selected">◉ &nbsp; Support assistant</div>
        <div className="nav-dim">◷ &nbsp; Persistent chat memory</div>
        <div className="nav-dim">✳ &nbsp; MCP connected tools</div>
        <div className="sidebar-bottom"><div className="dotline"><span className={online ? 'online-dot' : 'offline-dot'}/>{online ? 'Local backend connected' : 'Backend disconnected'}</div><small>Fictional store • demo customer</small></div>
      </aside>

      <main className="center">
        <header className="topbar"><div><div className="overline">CUSTOMER SUPPORT</div><h1>AI Support Assistant</h1></div><span className="badge">✦ Powered by Groq</span></header>
        <section className="chat-scroll">
          {messages.length === 0 && <div className="welcome"><div className="welcome-logo">✦</div><h2>How can I help you today?</h2><p>Ask about orders, returns, shipping, warranty, or support tickets. I can look up real demo data and use company documents.</p>
            <div className="suggestions">{suggestions.map(([icon, label, prompt]) => <button key={label} onClick={() => send(prompt)}><span>{icon}</span><div><strong>{label}</strong><small>{prompt}</small></div><b>↗</b></button>)}</div>
          </div>}
          {messages.map((msg, i) => <div className={'bubble-row ' + (msg.role === 'user' ? 'user' : 'assistant')} key={i}>
            {msg.role !== 'user' && <div className="avatar">✦</div>}<div className="bubble"><span className="sender">{msg.role === 'user' ? 'You' : 'SupportOps AI'}</span><div className="bubble-text">{msg.text}</div></div>
          </div>)}
          {busy && <div className="bubble-row assistant"><div className="avatar">✦</div><div className="bubble"><span className="sender">SupportOps AI</span><div className="typing">● ● ● <span>Checking tools and generating answer...</span></div></div></div>}
          <div ref={bottom}/>
        </section>
        {tools.length > 0 && <div className="tool-trace">⚙ Tools executed: {tools.join(' → ')}</div>}
        {error && <div className="error" onClick={() => setError('')}>{error} <span>×</span></div>}
        <form className="composer" onSubmit={e => { e.preventDefault(); send(); }}><input value={draft} onChange={e => setDraft(e.target.value)} placeholder="Ask anything about your order or company policy..." maxLength={1500} disabled={busy || !chatId}/><button disabled={busy || !draft.trim()} type="submit">➤</button></form>
        <div className="footer-note">SupportOps AI is an interview demonstration with fictional customer data. Refunds never move money.</div>
      </main>

      <aside className="rightbar">
        <div className="right-title"><strong>Live data</strong><span className="live-pill">● DEMO</span></div>
        <div className="tabs">{['orders', 'refunds'].map(tab => <button key={tab} className={activePanel === tab ? 'active' : ''} onClick={() => setActivePanel(tab)}>{tab}</button>)}</div>
        <div className="record-list">
          {activePanel === 'orders' && orders.map(order => <div className="record" key={order.id}><div className="record-row"><strong>{order.id}</strong><span className={'status ' + order.status.toLowerCase()}>{order.status}</span></div><p>{order.product}</p><small>Refund eligible: {order.refund_eligible ? 'Yes' : 'No'}</small></div>)}
          {activePanel === 'refunds' && (refunds.length ? refunds.map(r => <div className="record" key={r.id}><div className="record-row"><strong>Refund #{r.id}</strong><span className={'status ' + r.status.toLowerCase()}>{r.status}</span></div><p>{r.order_id} — {r.reason}</p><small>Human approval is required.</small></div>) : <div className="empty-note">No refund requests yet. Try asking for a refund for ORD-1003.</div>)}
        </div>
        <div className="manager-panel"><div className="manager-title"><strong>Manager approval</strong><button onClick={() => setManagerOpen(open => !open)}>{managerOpen ? 'Hide' : 'Open'}</button></div>
          {managerOpen && <div className="manager-queue">{refunds.filter(r => r.status === 'PENDING').length === 0 ? <p>No pending refunds.</p> : refunds.filter(r => r.status === 'PENDING').map(r => <div className="approval" key={r.id}><small>REQUEST #{r.id}</small><strong>{r.order_id}</strong><p>{r.reason}</p><div><button className="approve" onClick={() => decide(r.id, true)}>Approve</button><button className="reject" onClick={() => decide(r.id, false)}>Reject</button></div></div>)}<small className="demo-warning">Demo-only human gate. Not an authenticated manager portal.</small></div>}
        </div>
        <div className="stack"><p className="overline">THE STACK</p><div>React <span>→</span> FastAPI</div><div>LangGraph <span>→</span> Groq</div><div>MCP <span>→</span> SQLite</div><div>RAG <span>+</span> Agent Skills</div></div>
      </aside>
    </div>
  );
}
