import { useState, useEffect, useRef } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { api } from '../utils/api'
import { CheckCircle2, Compass, Loader2, Play, XCircle } from 'lucide-react'

function parseLogLine(msg) {
  return msg
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/_(.+?)_/g, '<em>$1</em>')
}

function StatusChip({ status }) {
  const map = { running: 'Running', done: 'Done', error: 'Failed' }
  return <span className={`explorer-status-chip ${status}`}>{map[status] ?? status}</span>
}

function LogLines({ logs, done }) {
  return logs.map((l, i) => (
    <div key={i} className="log-line">
      <CheckCircle2 size={13} className={`log-check ${done ? 'done' : ''}`} />
      <span dangerouslySetInnerHTML={{ __html: parseLogLine(l.msg) }} />
    </div>
  ))
}

export default function ExplorerPanel({ submitJob, openJob }) {
  const [prompt, setPrompt] = useState('')
  const [loading, setLoading] = useState(false)
  const [jobId, setJobId] = useState(null)
  const [logs, setLogs] = useState([])
  const [status, setStatus] = useState(null)
  const [result, setResult] = useState(null)
  const [error, setError] = useState(null)
  const [currentJob, setCurrentJob] = useState(null)
  const logsEndRef = useRef(null)

  useEffect(() => {
    if (logs.length > 0) logsEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  useEffect(() => {
    if (!jobId || status === 'done' || status === 'error') return
    const timer = setInterval(async () => {
      try {
        const job = await api.getJob(jobId)
        if (Array.isArray(job.logs)) setLogs(job.logs)
        setCurrentJob(job)
        if (job.status === 'done') {
          setStatus('done')
          setResult(job.result)
          setLoading(false)
        } else if (job.status === 'error') {
          setStatus('error')
          setError(job.error)
          setLoading(false)
        }
      } catch {}
    }, 1000)
    return () => clearInterval(timer)
  }, [jobId, status])

  const run = async () => {
    if (!prompt.trim() || loading) return
    setLoading(true)
    setLogs([])
    setResult(null)
    setError(null)
    setStatus('running')
    setJobId(null)
    setCurrentJob(null)
    try {
      const id = await submitJob(() => api.explorerRun(prompt), `Explorer - ${prompt.slice(0, 50)}`)
      if (id) {
        setJobId(id)
      } else {
        setStatus('error')
        setError('Failed to start job - backend did not return a job_id.')
        setLoading(false)
      }
    } catch (e) {
      setStatus('error')
      setError(String(e))
      setLoading(false)
    }
  }

  return (
    <div className="panel-stack animate-fade-in">
      <section className="page-heading">
        <h1>Explorer</h1>
        <p>Local Codex runner for this framework only. Requests are validated before Codex can run.</p>
      </section>

      <section className="tool-card featured">
        <div className="card-icon blue">
          <Compass size={27} strokeWidth={2.3} />
        </div>
        <div className="card-content">
          <div className="card-copy">
            <h2>Safe Codex Runner</h2>
            <p>
              Codex runs inside the project folder with the OneShield Explorer skill and workspace sandboxing.
              Destructive requests and credential access are blocked by the backend.
            </p>
          </div>

          <div className="field-wrap large">
            <label className="field-label" htmlFor="explorer-prompt">
              What do you want Codex to do?
            </label>
            <textarea
              id="explorer-prompt"
              className="field explorer-field"
              placeholder='Example: "use oneshield explorer to add a safe GL smoke test and run targeted validation"'
              value={prompt}
              onChange={e => setPrompt(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) run() }}
              disabled={loading}
              rows={3}
            />
          </div>

          <button
            onClick={run}
            disabled={!prompt.trim() || loading}
            className="action-button blue explorer-run"
            type="button"
          >
            {loading
              ? <Loader2 size={17} className="explorer-spinner" />
              : <Play size={17} />}
            <span>{loading ? 'Running...' : 'Run'}</span>
          </button>

          <div className="safety-note">
            <strong>Safety:</strong> allowed inside this repo only. Blocked: recursive delete, git reset/clean,
            credential reads, drive/registry/system commands, and absolute paths outside the project.
          </div>
        </div>
      </section>

      {status === 'running' && (
        <section className="explorer-live-card">
          <div className="explorer-live-header">
            <StatusChip status="running" />
            <span className="live-label">Live output</span>
          </div>
          <div className="explorer-log">
            <LogLines logs={logs} done={false} />
            <div className="log-line muted">
              <Loader2 size={13} className="explorer-spinner log-dot" />
              <span>Working...</span>
            </div>
            <div ref={logsEndRef} />
          </div>
        </section>
      )}

      {status === 'done' && (
        <>
          {logs.length > 0 && (
            <section className="explorer-live-card done">
              <div className="explorer-live-header">
                <StatusChip status="done" />
                <span className="live-label">Completed steps</span>
              </div>
              <div className="explorer-log">
                <LogLines logs={logs} done />
                <div ref={logsEndRef} />
              </div>
            </section>
          )}

          {result && (
            <section className="explorer-report">
              <div className="explorer-live-header">
                <StatusChip status="done" />
                <span className="live-label">Report</span>
                {currentJob && openJob && (
                  <button
                    className="text-button compact"
                    onClick={() => openJob(currentJob)}
                    type="button"
                    style={{ marginLeft: 'auto' }}
                  >
                    Open full report
                  </button>
                )}
              </div>
              <div className="report-markdown explorer-report-body">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{result}</ReactMarkdown>
              </div>
            </section>
          )}
        </>
      )}

      {status === 'error' && (
        <section className="explorer-error-card">
          <div className="explorer-live-header">
            <StatusChip status="error" />
            <span className="live-label">Error</span>
          </div>
          {logs.length > 0 && (
            <div className="explorer-log" style={{ marginBottom: 12 }}>
              <LogLines logs={logs} done={false} />
            </div>
          )}
          <div className="explorer-error-body">
            <XCircle size={16} style={{ flexShrink: 0, marginTop: 2 }} />
            <pre>{error}</pre>
          </div>
        </section>
      )}
    </div>
  )
}
