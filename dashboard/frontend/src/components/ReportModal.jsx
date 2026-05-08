import { useEffect, useRef, useState } from 'react'
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'
import { BarChart2, Clipboard, Clock3, Copy, FileJson, ShieldAlert, X } from 'lucide-react'

export default function ReportModal({ job, onClose }) {
  const ref = useRef(null)
  const [allureState, setAllureState] = useState('idle') // idle | generating | ready | error
  const [allureError, setAllureError] = useState('')

  useEffect(() => {
    const handler = e => { if (e.key === 'Escape') onClose() }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [onClose])

  const handleBackdrop = e => { if (e.target === ref.current) onClose() }

  const copyReport = () => {
    const text = job.status === 'done' ? job.result : job.error
    navigator.clipboard.writeText(text || '')
  }

  const openAllure = async () => {
    setAllureState('generating')
    setAllureError('')
    try {
      const res = await fetch('http://localhost:8000/api/allure/generate', { method: 'POST' })
      const data = await res.json()
      if (data.ok) {
        setAllureState('ready')
        window.open('http://localhost:8000/allure/', '_blank')
      } else {
        setAllureState('error')
        setAllureError(data.error || 'Allure report generation failed')
        console.error('Allure generate failed:', data.error)
      }
    } catch (error) {
      setAllureState('error')
      setAllureError(error?.message || 'Unable to contact dashboard backend')
    }
  }

  const isJson = job.status === 'done' && job.result?.trimStart().startsWith('{')
  const isError = job.status === 'error'
  const isMarkdown = !isError && !isJson && job.status === 'done'
  const duration = job.finished ? `${Math.round(job.finished - job.started)}s` : 'Running'
  const HeaderIcon = isError ? ShieldAlert : isJson ? FileJson : Clipboard

  const allureLabel = {
    idle:       'Allure Report',
    generating: 'Generating…',
    ready:      'Open Again',
    error:      'Report Error',
  }[allureState]

  return (
    <div ref={ref} onClick={handleBackdrop} className="report-backdrop">
      <section className="report-dialog" role="dialog" aria-modal="true" aria-label="Job report">
        <header className="report-header">
          <div className="report-title-block">
            <div className={`report-icon ${isError ? 'error' : 'blue'}`}>
              <HeaderIcon size={24} />
            </div>
            <div>
              <h2>{job.label}</h2>
              <p>
                <Clock3 size={15} />
                {job.finished ? `Completed in ${duration}` : 'Still running'}
              </p>
            </div>
          </div>

          <div className="report-actions">
            {isMarkdown && (
              <button
                onClick={openAllure}
                className="text-button compact"
                type="button"
                disabled={allureState === 'generating'}
                title={allureState === 'error' ? allureError : 'Generate and open Allure report'}
              >
                <BarChart2 size={16} />
                {allureLabel}
              </button>
            )}
            <button onClick={copyReport} className="text-button compact" type="button">
              <Copy size={16} />
              Copy
            </button>
            <button onClick={onClose} className="modal-close-button" title="Close" aria-label="Close report" type="button">
              <X size={20} />
            </button>
          </div>
        </header>

        <div className="report-body">
          {isError ? (
            <div className="report-state error">
              <div className="report-state-heading">
                <ShieldAlert size={21} />
                Error
              </div>
              <pre>{job.error}</pre>
            </div>
          ) : isJson ? (
            <div className="report-state json">
              <div className="report-state-heading">
                <FileJson size={21} />
                Generated Profile JSON
              </div>
              <pre>{JSON.stringify(JSON.parse(job.result), null, 2)}</pre>
            </div>
          ) : (
            <div className="markdown-report report-markdown">
              <Markdown remarkPlugins={[remarkGfm]} components={mdComponents}>
                {job.result || ''}
              </Markdown>
            </div>
          )}
        </div>
        {!isError && job.result && <ViolationSummary content={job.result} />}
      </section>
    </div>
  )
}

const VIOLATION_TYPES = {
  FALSE_APPROVE:     { label: 'False Approve',      title: 'Rule engine missed a risk — risky profile was approved without referral' },
  FALSE_REFER:       { label: 'False Refer',         title: 'Rule engine over-triggered — clean profile was incorrectly flagged for review' },
  MISSING_CONDITION: { label: 'Missing Condition',   title: 'Wrong or incomplete rule displayed on the UW referral page' },
  WRONG_COUNT:       { label: 'Wrong Count',         title: 'Fewer UW conditions appeared than expected' },
  EXTRA_CONDITIONS:  { label: 'Extra Conditions',    title: 'Unexpected additional rules fired that should not have triggered' },
  FLOW_ERROR:        { label: 'Flow Error',          title: 'Browser automation failed before a UW decision could be reached' },
}

function parseViolationTypes(content) {
  const results = []
  for (const line of content.split('\n')) {
    if (!line.startsWith('- ')) continue
    // split on backtick: ["- 🔴 ", "FLOW_ERROR", ": 1"]
    const parts = line.split('`')
    if (parts.length < 3) continue
    const type = parts[1]
    if (!/^[A-Z_]+$/.test(type) || type === 'PASS') continue
    const countMatch = parts[2].match(/:\s*(\d+)/)
    if (!countMatch) continue
    const count = parseInt(countMatch[1], 10)
    if (count > 0) results.push({ type, count })
  }
  return results
}

function ViolationSummary({ content }) {
  const violations = parseViolationTypes(content)
  if (!violations.length) return null
  return (
    <div className="violation-summary">
      <p className="violation-summary-title">Validation errors found:</p>
      <ul className="violation-summary-list">
        {violations.map(v => {
          const meta = VIOLATION_TYPES[v.type]
          return (
            <li key={v.type}>
              <strong>{meta?.label || v.type} &middot; {v.count}</strong>
              {meta?.title && <span> — {meta.title}</span>}
            </li>
          )
        })}
      </ul>
    </div>
  )
}

const mdComponents = {
  h1: ({ children }) => <h1>{children}</h1>,
  h2: ({ children }) => <h2>{children}</h2>,
  h3: ({ children }) => <h3>{children}</h3>,
  p: ({ children }) => <p>{children}</p>,
  strong: ({ children }) => <strong>{children}</strong>,
  em: ({ children }) => <em>{children}</em>,
  table: ({ children }) => (
    <div className="report-table-wrap">
      <table>{children}</table>
    </div>
  ),
  thead: ({ children }) => <thead>{children}</thead>,
  tbody: ({ children }) => <tbody>{children}</tbody>,
  tr: ({ children }) => <tr>{children}</tr>,
  th: ({ children }) => <th>{children}</th>,
  td: ({ children }) => <td>{children}</td>,
  code: ({ children, className }) => {
    if (className) return <code className="code-block">{children}</code>
    return <code>{children}</code>
  },
  pre: ({ children }) => <pre>{children}</pre>,
  blockquote: ({ children }) => <blockquote>{children}</blockquote>,
  ul: ({ children }) => <ul>{children}</ul>,
  ol: ({ children }) => <ol>{children}</ol>,
  li: ({ children }) => <li>{children}</li>,
  hr: () => <hr />,
}
