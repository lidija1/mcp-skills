import { useState, useEffect, useRef, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { api } from '../utils/api'
import { cleanDisplayText } from '../utils/text'
import { Bot, ChevronDown, ExternalLink, SendHorizonal, User, CheckCircle2, XCircle, Loader, Plus, RotateCcw, MessageSquare, History, Trash2 } from 'lucide-react'

function BotBubble({ text }) {
  return (
    <div className="chat-bubble-row bot">
      <span className="chat-avatar bot"><Bot size={16} /></span>
      <div className="chat-bubble bot">
        <div className="chat-table-wrap">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
        </div>
      </div>
    </div>
  )
}

function UserBubble({ text }) {
  return (
    <div className="chat-bubble-row user">
      <div className="chat-bubble user">{text}</div>
      <span className="chat-avatar user"><User size={16} /></span>
    </div>
  )
}

function JobResultBubble({ jobId, label, job, onOpenReport }) {
  if (!job || job.status === 'running') {
    return (
      <div className="chat-job-badge">
        <Loader size={13} className="chat-job-spinner" />
        <span>Running — <em>{label}</em></span>
      </div>
    )
  }

  if (job.status === 'error') {
    return (
      <div className="chat-job-result chat-job-result--error">
        <div className="chat-job-result-header">
          <XCircle size={14} />
          <span className="chat-job-result-label">{label}</span>
          <span className="chat-job-result-badge error">Failed</span>
        </div>
        <pre className="chat-job-result-error">{job.error}</pre>
      </div>
    )
  }

  const result = cleanDisplayText(job.result || '')
  const assertFlowData = parseAssertFlowResult(result)

  return (
    <div className="chat-job-result">
      <div className="chat-job-result-header">
        <CheckCircle2 size={14} />
        <span className="chat-job-result-label">{label}</span>
        <span className="chat-job-result-badge success">Completed</span>
        {onOpenReport && (
          <button
            type="button"
            className="chat-job-open-btn"
            onClick={() => onOpenReport(job)}
          >
            <ExternalLink size={11} /> Full report
          </button>
        )}
      </div>
      {assertFlowData ? (
        <div className={`chat-inline-af ${assertFlowData.passed ? 'pass' : 'fail'}`}>
          <span className="chat-inline-af-verdict">{assertFlowData.passed ? 'PASS' : 'FAIL'}</span>
          <span className="chat-inline-af-type">
            {(assertFlowData.assertion_type || '').replace('_', ' ')} assertion
          </span>
          {assertFlowData.message && (
            <span className="chat-inline-af-msg">{assertFlowData.message}</span>
          )}
        </div>
      ) : (
        <div className="chat-job-result-body">
          <div className="chat-table-wrap">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{result}</ReactMarkdown>
          </div>
        </div>
      )}
    </div>
  )
}

function parseAssertFlowResult(text) {
  if (!text.trimStart().startsWith('{')) return null
  try {
    const p = JSON.parse(text)
    return p._type === 'assert_flow' ? p : null
  } catch {
    return null
  }
}

function ConfirmCard({ toolCall, reply, onConfirm, onCancel }) {
  return (
    <div className="chat-confirm-card">
      <p className="confirm-reply">{reply}</p>
      <pre className="confirm-preview">{JSON.stringify(toolCall.params, null, 2)}</pre>
      <div className="confirm-actions">
        <button className="action-button blue compact" onClick={onConfirm} type="button">
          <CheckCircle2 size={15} /> Confirm
        </button>
        <button className="text-button compact" onClick={onCancel} type="button">
          <XCircle size={15} /> Cancel
        </button>
      </div>
    </div>
  )
}

function TypingIndicator() {
  return (
    <div className="chat-bubble-row bot">
      <span className="chat-avatar bot"><Bot size={16} /></span>
      <div className="chat-typing">
        <span /><span /><span />
      </div>
    </div>
  )
}

const HELP_SUGGESTIONS = [
  '/help',
  '/help playwright',
  '/help bdd',
  '/help chat',
  '/help tools',
  '/help mcp',
  '/help api',
  '/help ladder',
  '/help regression',
  '/help persona',
  '/help lob',
  '/help uw',
  '/help testdata',
  '/help dashboard',
]

const TOOL_SUGGESTIONS = [
  'run a quick auto test for a young male driver',
  'run an auto policy flow for a married couple with two vehicles',
  'run a homeowner policy flow for a coastal property with prior losses',
  'create an auto persona for a driver with SR-22 and revoked license',
  'create a homeowner persona for a luxury coastal home',
  'generate 5 auto persona variations for high-risk young drivers',
  'generate 10 homeowner personas for coastal properties with prior losses',
  'assert that a young male driver with Gold coverage premium is around $1,200',
  'assert that a retired driver with clean record premium is less than $800',
  'assert that a married homeowner with no claims total cost is under $2,000',
  'run batch: young auto driver and retired homeowner',
  'list all underwriting rules',
  'audit auto underwriting rules',
  'audit homeowner underwriting rules',
  'run a full audit of all underwriting rules',
]

function formatChatDate(ts) {
  if (!ts) return ''
  const date = new Date(ts * 1000)
  const now = new Date()
  const sameDay = date.toDateString() === now.toDateString()
  if (sameDay) {
    return date.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
  }
  return date.toLocaleDateString([], { month: 'short', day: 'numeric' })
}

function sessionMessagesToChat(messages = []) {
  return messages.map(message => ({
    role: message.role === 'user' ? 'user' : 'bot',
    text: message.content || '',
  })).filter(message => message.text)
}

export default function ChatPanel({ onJobDispatched, jobs = [], onOpenReport, expanded = false }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [streaming, setStreaming] = useState(false)
  const [pendingConfirm, setPendingConfirm] = useState(null)
  const [mode, setMode] = useState(() => localStorage.getItem('chat_mode') || 'guidance')
  const [sessions, setSessions] = useState([])
  const [sessionsLoading, setSessionsLoading] = useState(false)
  const [activeSessionId, setActiveSessionId] = useState(null)
  const [sessionLoading, setSessionLoading] = useState(false)
  const [compactView, setCompactView] = useState('chat')
  const [acSuggestions, setAcSuggestions] = useState([])
  const [acIndex, setAcIndex] = useState(-1)
  const [inputFocused, setInputFocused] = useState(false)
  const threadRef = useRef(null)
  const historyVisible = expanded || compactView === 'history'
  const chatVisible = expanded || compactView !== 'history'

  const loadGreeting = useCallback(() => {
    api.chatGreeting()
      .then(data => {
        if (data.greeting) {
          setMessages([{ role: 'bot', text: data.greeting }])
        }
      })
      .catch(() => {
        setMessages([{ role: 'bot', text: 'Hi! I\'m your insurance testing assistant. How can I help?' }])
      })
  }, [])

  const loadSessions = useCallback(async () => {
    if (!historyVisible) return
    setSessionsLoading(true)
    try {
      const data = await api.listChatSessions()
      setSessions(Array.isArray(data.sessions) ? data.sessions : [])
    } catch {
      setSessions([])
    } finally {
      setSessionsLoading(false)
    }
  }, [historyVisible])

  useEffect(() => {
    loadGreeting()
  }, [loadGreeting])

  useEffect(() => {
    loadSessions()
  }, [loadSessions])

  const loadChatSession = useCallback(async (sessionId) => {
    if (!sessionId || loading) return
    setSessionLoading(true)
    setPendingConfirm(null)
    try {
      const session = await api.getChatSession(sessionId)
      setActiveSessionId(session.id)
      if (!expanded) setCompactView('chat')
      const savedMessages = sessionMessagesToChat(session.messages || [])
      if (savedMessages.length > 0) {
        setMessages(savedMessages)
      } else {
        loadGreeting()
      }
    } catch (err) {
      setMessages([{ role: 'bot', text: `Error: ${err.message}` }])
    } finally {
      setSessionLoading(false)
    }
  }, [expanded, loadGreeting, loading])

  const startNewChat = useCallback(async () => {
    setInput('')
    setPendingConfirm(null)
    setLoading(false)
    setActiveSessionId(null)
    setCompactView('chat')
    loadGreeting()
  }, [loadGreeting])

  const deleteChatSession = useCallback(async (sessionId) => {
    if (!sessionId || loading) return
    try {
      await api.deleteChatSession(sessionId)
      if (sessionId === activeSessionId) {
        setActiveSessionId(null)
        setPendingConfirm(null)
        loadGreeting()
      }
      await loadSessions()
    } catch (err) {
      setMessages(prev => [...prev, { role: 'bot', text: `Error: ${err.message}` }])
    }
  }, [activeSessionId, loadGreeting, loadSessions, loading])

  useEffect(() => {
    if (threadRef.current) {
      threadRef.current.scrollTop = threadRef.current.scrollHeight
    }
  }, [messages, loading])

  const appendBot = useCallback((text, extra = {}) => {
    setMessages(prev => [...prev, { role: 'bot', text, ...extra }])
  }, [])

  useEffect(() => {
    const trimmed = input.trim()
    if (!inputFocused || trimmed.length < 1) {
      setAcSuggestions([])
      return
    }
    // /help autocomplete in any mode
    if (trimmed.startsWith('/')) {
      setAcSuggestions(
        HELP_SUGGESTIONS.filter(s => s.startsWith(trimmed.toLowerCase())).slice(0, 8)
      )
      return
    }
    if (mode !== 'tools' || trimmed.length < 2) {
      setAcSuggestions([])
      return
    }
    const words = trimmed.toLowerCase().split(/\s+/)
    setAcSuggestions(
      TOOL_SUGGESTIONS.filter(s => words.every(w => s.includes(w))).slice(0, 6)
    )
  }, [input, mode, inputFocused])

  useEffect(() => { setAcIndex(-1) }, [acSuggestions])

  const selectSuggestion = useCallback((s) => {
    setInput(s)
    setAcSuggestions([])
    setInputFocused(false)
  }, [])

  const buildHistory = (msgs) =>
    msgs
      .filter(m => m.text && !m.confirm)
      .slice(-10)
      .map(m => ({ role: m.role === 'user' ? 'user' : 'assistant', content: m.text.slice(0, 800) }))

  // Expand /help [topic] into a structured Ask-mode query.
  // Returns { query, displayText } or null if not a /help command.
  const parseHelpCommand = useCallback((text) => {
    const m = text.trim().match(/^\/help\s*(.*)/i)
    if (!m) return null
    const topic = m[1].trim()
    if (!topic) {
      return {
        displayText: '/help',
        query: (
          'Give me a structured help overview of this insurance automation dashboard. ' +
          'Cover: (1) Chat modes — Ask vs Tools and what each can do, ' +
          '(2) available Tools-mode commands with short examples, ' +
          '(3) the Playwright/pytest-bdd test framework structure (features, steps, page objects), ' +
          '(4) MCP servers and their purpose, ' +
          '(5) how to add a new LOB or test scenario. ' +
          'Use markdown headings and bullet points.'
        ),
      }
    }
    const topicMap = {
      playwright: 'Playwright, pytest-bdd BDD framework, page objects, BasePage smart wrappers, ExtJS patterns, and how tests are structured in this project',
      bdd: 'BDD feature files, step definitions, pytest-bdd fixtures, conftest.py plugins, and how to write or extend scenarios',
      chat: 'the dashboard chat panel — Ask mode vs Tools mode, available tools, how to trigger jobs, confirmation flow, and streaming',
      tools: 'all available Tools-mode chat commands with usage examples and what each one does',
      mcp: 'the six MCP servers — policy-flow-generator, uw-rules-validator, lob-recorder, form-intelligence, accessibility, auto-scenario-generator — their purpose and how to use them',
      api: 'the API assertions panel — comparative, ladder, AI assert, and history tabs — and how to use each',
      ladder: 'the ladder runner — dimensions, how monotonic checks work, how to run a sweep, and what the results mean',
      persona: 'persona generation — AI providers, JSON fields, LOB differences, how to create variations, and how personas feed into flows',
      lob: 'how to add a new Line of Business — page objects, feature file, step definitions, test entry point, test data fields, and fixture registration',
      uw: 'the UW rules validator — rule registry, positive/negative/boundary cases, how to run audits, and how to write custom boundary tests',
      testdata: 'test data — JSON structure, TC_ID filtering, required fields per LOB, and the testdata RAG index',
      dashboard: 'the React dashboard — panels, job tracking, polling, report modal, and how the backend FastAPI connects to the frontend',
    }
    const key = Object.keys(topicMap).find(k => topic.toLowerCase().includes(k)) || null
    const subject = key ? topicMap[key] : `"${topic}" in the context of this insurance automation dashboard`
    return {
      displayText: `/help ${topic}`,
      query: (
        `Give me a structured explanation of ${subject}. ` +
        'Include: what it is, how it works in this project, key files or commands, and a practical usage example. ' +
        'Use markdown headings and bullet points.'
      ),
    }
  }, [])

  const send = useCallback(async (userText, confirmedTool = null, confirmedParams = null) => {
    if (loading) return

    const trimmed = (userText || '').trim()
    if (!trimmed && !confirmedTool) return
    const sessionIdForRequest = activeSessionId

    // /help [topic] — force Ask mode and rewrite to a structured query
    if (!confirmedTool) {
      const help = parseHelpCommand(trimmed)
      if (help) {
        setMode('guidance')
        localStorage.setItem('chat_mode', 'guidance')
        setInput('')
        setMessages(prev => [...prev, { role: 'user', text: help.displayText }])
        setPendingConfirm(null)
        setLoading(true)
        setStreaming(true)
        setMessages(prev => [...prev, { role: 'bot', text: '' }])
        try {
          const response = await api.chatAskStream(help.query, buildHistory(messages), 4000, sessionIdForRequest, help.displayText)
          if (!response.ok) {
            const data = await response.json().catch(() => ({}))
            throw new Error(data.detail || data.error || 'Help stream failed')
          }
          const reader = response.body.getReader()
          const decoder = new TextDecoder()
          let buf = '', acc = ''
          while (true) {
            const { done, value } = await reader.read()
            if (done) break
            buf += decoder.decode(value, { stream: true })
            const parts = buf.split('\n\n')
            buf = parts.pop() ?? ''
            for (const part of parts) {
              if (!part.startsWith('data: ')) continue
              let evt
              try { evt = JSON.parse(part.slice(6)) } catch { continue }
              if (evt.error) throw new Error(evt.error)
              if (evt.session_id) setActiveSessionId(evt.session_id)
              if (evt.done) return
              if (evt.t) {
                acc += evt.t
                setMessages(prev => {
                  const next = [...prev]
                  next[next.length - 1] = { role: 'bot', text: acc }
                  return next
                })
              }
            }
          }
        } catch (err) {
          setMessages(prev => {
            const next = [...prev]
            next[next.length - 1] = { role: 'bot', text: `Error: ${err.message}` }
            return next
          })
        } finally {
          setStreaming(false)
          setLoading(false)
          if (historyVisible) await loadSessions()
        }
        return
      }
    }

    // Snapshot history before the new user turn is appended
    const history = confirmedTool ? [] : buildHistory(messages)

    if (!confirmedTool) {
      setMessages(prev => [...prev, { role: 'user', text: trimmed }])
      setInput('')
    }
    setPendingConfirm(null)
    setLoading(true)

    try {
      if (mode === 'guidance' && !confirmedTool) {
        // ── Streaming path for Guidance mode ──────────────────────────────
        const response = await api.chatAskStream(trimmed, history, 1200, sessionIdForRequest)
        if (!response.ok) {
          const data = await response.json().catch(() => ({}))
          throw new Error(data.detail || data.error || 'Guidance stream failed')
        }

        setStreaming(true)
        setMessages(prev => [...prev, { role: 'bot', text: '' }])

        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buf = ''
        let acc = ''

        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          buf += decoder.decode(value, { stream: true })
          const parts = buf.split('\n\n')
          buf = parts.pop() ?? ''
          for (const part of parts) {
            if (!part.startsWith('data: ')) continue
            let evt
            try { evt = JSON.parse(part.slice(6)) } catch { continue }
              if (evt.error) throw new Error(evt.error)
              if (evt.session_id) setActiveSessionId(evt.session_id)
              if (evt.done) return
            if (evt.t) {
              acc += evt.t
              setMessages(prev => {
                const next = [...prev]
                next[next.length - 1] = { role: 'bot', text: acc }
                return next
              })
            }
          }
        }
      } else {
        // ── Standard path for Tools mode and confirmed dispatches ──────────
        const resp = await api.chat(confirmedTool ? '' : trimmed, confirmedTool, confirmedParams, history, sessionIdForRequest)
        if (resp.chat_session_id) setActiveSessionId(resp.chat_session_id)

        if (resp.status === 'job') {
          appendBot(resp.reply, { jobId: resp.job_id, jobLabel: resp.job_label })
          if (resp.job_id && onJobDispatched) {
            onJobDispatched(resp.job_id, resp.job_label || 'Chat job')
          }
        } else if (resp.status === 'confirm') {
          appendBot(resp.reply, { confirm: resp.tool_call })
          setPendingConfirm(resp.tool_call)
        } else {
          appendBot(resp.reply || '(no response)')
        }
      }
    } catch (err) {
      appendBot(`Error: ${err.message}`)
    } finally {
      setStreaming(false)
      setLoading(false)
      if (historyVisible) await loadSessions()
    }
  }, [activeSessionId, historyVisible, loadSessions, loading, mode, messages, appendBot, onJobDispatched])

  const handleConfirm = useCallback(() => {
    if (!pendingConfirm) return
    send('', pendingConfirm.tool, pendingConfirm.params)
  }, [pendingConfirm, send])

  const handleCancel = useCallback(() => {
    setPendingConfirm(null)
    appendBot('Cancelled.')
  }, [appendBot])

  const handleKeyDown = useCallback(e => {
    if (acSuggestions.length > 0) {
      if (e.key === 'ArrowDown') { e.preventDefault(); setAcIndex(i => Math.min(i + 1, acSuggestions.length - 1)); return }
      if (e.key === 'ArrowUp')   { e.preventDefault(); setAcIndex(i => Math.max(i - 1, -1)); return }
      if (e.key === 'Escape')    { setAcSuggestions([]); return }
      if (e.key === 'Enter' && acIndex >= 0) { e.preventDefault(); selectSuggestion(acSuggestions[acIndex]); return }
    }
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send(input)
    }
  }, [input, send, acSuggestions, acIndex, selectSuggestion])

  const isGreetingOnly = messages.length === 1 && messages[0]?.role === 'bot' && messages[0]?.text?.startsWith('Hi!')
  const isFreshChat = (messages.length === 0 || isGreetingOnly) && !loading
  const visibleMessages = expanded && isFreshChat ? [] : messages

  return (
    <div className={`chat-panel-shell${expanded ? ' chat-panel-shell--expanded' : ''}${compactView === 'history' ? ' chat-panel-shell--history' : ''}`}>
      {historyVisible && (
        <aside className={`chat-history-sidebar${!expanded ? ' chat-history-sidebar--compact' : ''}`} aria-label="Chat history">
          <div className="chat-history-header">
            <button
              className="chat-history-new-btn"
              type="button"
              onClick={startNewChat}
              disabled={loading}
            >
              <Plus size={15} />
              <span>New chat</span>
            </button>
            {!expanded && (
              <button
                className="chat-history-chat-btn"
                type="button"
                onClick={() => setCompactView('chat')}
              >
                Chat
              </button>
            )}
          </div>
          <div className="chat-history-list">
            {sessionsLoading && (
              <div className="chat-history-state">Loading chats...</div>
            )}
            {!sessionsLoading && sessions.length === 0 && (
              <div className="chat-history-state">No saved chats yet.</div>
            )}
            {!sessionsLoading && sessions.map(session => (
              <div
                key={session.id}
                className={`chat-history-item${session.id === activeSessionId ? ' active' : ''}`}
              >
                <button
                  type="button"
                  className="chat-history-item-main"
                  onClick={() => loadChatSession(session.id)}
                  disabled={loading || sessionLoading}
                  title={session.title}
                >
                  <MessageSquare size={14} />
                  <span className="chat-history-item-copy">
                    <span className="chat-history-item-title">{session.title || 'New chat'}</span>
                    <span className="chat-history-item-meta">{formatChatDate(session.updated_at)}</span>
                  </span>
                </button>
                <button
                  type="button"
                  className="chat-history-delete-btn"
                  onClick={() => deleteChatSession(session.id)}
                  disabled={loading || sessionLoading}
                  aria-label={`Delete ${session.title || 'chat'}`}
                  title="Delete chat"
                >
                  <Trash2 size={13} />
                </button>
              </div>
            ))}
          </div>
        </aside>
      )}
      {chatVisible && (
      <div className={`chat-panel-page${isFreshChat ? ' chat-panel-page--empty' : ''}`}>
      {!expanded && (
        <div className="chat-compact-topbar">
          <button
            className="chat-new-btn"
            type="button"
            onClick={startNewChat}
            disabled={loading}
          >
            <Plus size={14} />
            <span>New chat</span>
          </button>
          <button
            className="chat-history-toggle-btn"
            type="button"
            onClick={() => {
              setCompactView('history')
              loadSessions()
            }}
            disabled={loading}
          >
            <History size={14} />
            <span>History</span>
          </button>
          <button
            className="chat-refresh-btn"
            type="button"
            onClick={loadGreeting}
            disabled={loading}
            aria-label="Refresh greeting"
            title="Refresh greeting"
          >
            <RotateCcw size={14} />
          </button>
        </div>
      )}
      <div className="chat-thread" ref={threadRef}>
        {visibleMessages.map((msg, i) => (
          <div key={i}>
            {msg.role === 'user'
              ? <UserBubble text={msg.text} />
              : <BotBubble text={msg.text} />
            }
            {msg.jobId && (
              <JobResultBubble
                jobId={msg.jobId}
                label={msg.jobLabel}
                job={jobs.find(j => j.id === msg.jobId)}
                onOpenReport={onOpenReport}
              />
            )}
            {msg.confirm && (
              <div className="chat-bubble-row bot">
                <span className="chat-avatar bot" style={{ visibility: 'hidden' }}><Bot size={16} /></span>
                <ConfirmCard
                  toolCall={msg.confirm}
                  reply=""
                  onConfirm={handleConfirm}
                  onCancel={handleCancel}
                />
              </div>
            )}
          </div>
        ))}
        {(loading || sessionLoading) && !streaming && <TypingIndicator />}
      </div>

      <div className="chat-input-row">
        {acSuggestions.length > 0 && (
          <div className="chat-ac-dropdown">
            {acSuggestions.map((s, i) => (
              <button
                key={s}
                type="button"
                className={`chat-ac-item${i === acIndex ? ' chat-ac-item--active' : ''}`}
                onMouseDown={e => { e.preventDefault(); selectSuggestion(s) }}
              >
                {s}
              </button>
            ))}
          </div>
        )}
        <textarea
          className="chat-input"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          onFocus={() => setInputFocused(true)}
          onBlur={() => setInputFocused(false)}
          placeholder={mode === 'guidance'
            ? 'Ask a question, or type /help [topic] for structured guidance...'
            : 'Ask me to run a policy test, generate a profile, audit UW rules... (or /help)'}
          rows={1}
          disabled={loading}
        />
        <label className="chat-mode-select-wrap" aria-label="Chat response mode">
          <select
            className="chat-mode-select"
            value={mode}
            onChange={e => {
              const m = e.target.value
              setMode(m)
              localStorage.setItem('chat_mode', m)
              setPendingConfirm(null)
            }}
            disabled={loading}
          >
            <option value="tools">Tools</option>
            <option value="guidance">Ask</option>
          </select>
          <ChevronDown size={14} />
        </label>
        {!expanded && (
          <button
            className="chat-send-btn"
            type="button"
            onClick={() => send(input)}
            disabled={loading || !input.trim()}
            aria-label="Send"
          >
            <SendHorizonal size={18} />
          </button>
        )}
      </div>
      </div>
      )}
    </div>
  )
}
