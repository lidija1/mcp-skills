import { useState, useEffect, useRef, useCallback } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { api } from '../utils/api'
import { Bot, SendHorizonal, User, CheckCircle2, XCircle } from 'lucide-react'

const SUGGESTIONS = [
  'Run a quick auto test for a young driver',
  'Generate a homeowner profile',
  'List all UW rules',
  'Audit cyber underwriting rules',
]

const GUIDANCE_SUGGESTIONS = [
  'Explain how Tools mode is restricted',
  'How do I add a new policy workflow?',
  'Help me improve auto test data',
  'Why would a UW audit fail?',
]

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

function JobBadge({ jobId, label }) {
  return (
    <div className="chat-job-badge">
      <CheckCircle2 size={14} />
      <span>Job <code>{jobId}</code> started — <em>{label}</em></span>
    </div>
  )
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

export default function ChatPanel({ onJobDispatched }) {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [pendingConfirm, setPendingConfirm] = useState(null)
  const [mode, setMode] = useState('tools')
  const threadRef = useRef(null)

  useEffect(() => {
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

  useEffect(() => {
    if (threadRef.current) {
      threadRef.current.scrollTop = threadRef.current.scrollHeight
    }
  }, [messages, loading])

  const appendBot = useCallback((text, extra = {}) => {
    setMessages(prev => [...prev, { role: 'bot', text, ...extra }])
  }, [])

  const send = useCallback(async (userText, confirmedTool = null, confirmedParams = null) => {
    if (loading) return

    const trimmed = (userText || '').trim()
    if (!trimmed && !confirmedTool) return

    if (!confirmedTool) {
      setMessages(prev => [...prev, { role: 'user', text: trimmed }])
      setInput('')
    }
    setPendingConfirm(null)
    setLoading(true)

    try {
      const resp = mode === 'guidance' && !confirmedTool
        ? await api.chatAsk(trimmed)
        : await api.chat(confirmedTool ? '' : trimmed, confirmedTool, confirmedParams)

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
    } catch (err) {
      appendBot(`Error: ${err.message}`)
    } finally {
      setLoading(false)
    }
  }, [loading, mode, appendBot, onJobDispatched])

  const handleConfirm = useCallback(() => {
    if (!pendingConfirm) return
    send('', pendingConfirm.tool, pendingConfirm.params)
  }, [pendingConfirm, send])

  const handleCancel = useCallback(() => {
    setPendingConfirm(null)
    appendBot('Cancelled.')
  }, [appendBot])

  const handleKeyDown = useCallback(e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send(input)
    }
  }, [input, send])

  const suggestions = mode === 'guidance' ? GUIDANCE_SUGGESTIONS : SUGGESTIONS

  return (
    <div className="chat-panel-page">
      <div className="chat-thread" ref={threadRef}>
        {messages.map((msg, i) => (
          <div key={i}>
            {msg.role === 'user'
              ? <UserBubble text={msg.text} />
              : <BotBubble text={msg.text} />
            }
            {msg.jobId && <JobBadge jobId={msg.jobId} label={msg.jobLabel} />}
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
        {loading && <TypingIndicator />}
      </div>

      {messages.length <= 1 && !loading && (
        <div className="chat-suggestions">
          {suggestions.map(s => (
            <button key={s} className="chat-suggestion-chip" type="button" onClick={() => send(s)}>
              {s}
            </button>
          ))}
        </div>
      )}

      <div className="chat-mode-row" role="group" aria-label="Chat mode">
        <button
          className={`chat-mode-btn ${mode === 'tools' ? 'active' : ''}`}
          type="button"
          onClick={() => {
            setMode('tools')
            setPendingConfirm(null)
          }}
          disabled={loading}
        >
          Tools
        </button>
        <button
          className={`chat-mode-btn ${mode === 'guidance' ? 'active' : ''}`}
          type="button"
          onClick={() => {
            setMode('guidance')
            setPendingConfirm(null)
          }}
          disabled={loading}
        >
          Guidance
        </button>
      </div>

      <div className="chat-input-row">
        <textarea
          className="chat-input"
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={mode === 'guidance'
            ? 'Ask for explanations, troubleshooting, or implementation guidance...'
            : 'Ask me to run a policy test, generate a profile, audit UW rules...'}
          rows={1}
          disabled={loading}
        />
        <button
          className="chat-send-btn"
          type="button"
          onClick={() => send(input)}
          disabled={loading || !input.trim()}
          aria-label="Send"
        >
          <SendHorizonal size={18} />
        </button>
      </div>
    </div>
  )
}
