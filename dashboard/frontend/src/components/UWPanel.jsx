import { useState, useEffect } from 'react'
import { api } from '../utils/api'
import {
  AlertTriangle,
  BookOpenText,
  Check,
  ChevronsUpDown,
  ClipboardCheck,
  Info,
  Play,
  Plus,
  SearchCheck,
  ShieldAlert,
  X,
} from 'lucide-react'
import { metadataForUwLob } from '../utils/jobLob'

const LOBS = [
  { id: 'auto', label: 'Personal Auto' },
  { id: 'homeowner', label: 'Homeowner' },
]

const EDGE_PLACEHOLDERS = {
  auto: 'e.g. "Triple risk: SR-22 + revoked license + age 22"',
  homeowner: 'e.g. "30-year-old roof in a wildfire zone with a prior total loss claim within 3 years"',
}

export default function UWPanel({ submitJob }) {
  const [lob, setLob] = useState('auto')
  const [rules, setRules] = useState([])
  const [loading, setLoading] = useState('')

  useEffect(() => {
    api.listRules(lob).then(d => {
      setRules(parseRuleRows(d.result || ''))
    })
  }, [lob])

  const run = async (label, apiFn) => {
    setLoading(label)
    try {
      await submitJob(apiFn, label, { metadata: metadataForUwLob(lob) })
    } finally {
      setLoading('')
    }
  }

  return (
    <div className="panel-stack animate-fade-in">
      <section className="page-heading">
        <h1>UW Rules Validator</h1>
        <p>Validate underwriting rules against live application workflows and edge-case outcomes</p>
      </section>

      <LobSelector lobs={LOBS} selected={lob} onSelect={setLob} />

      <ViewRulesCard lob={lob} />

      <div className="two-column-grid">
        <DepartmentAuditCard lob={lob} run={run} loading={loading} />
        <SingleRuleCard lob={lob} rules={rules} run={run} loading={loading} />
      </div>

      <EdgeCaseCard lob={lob} run={run} loading={loading} />
      <FullAuditCard run={run} loading={loading} />
    </div>
  )
}

function LobSelector({ lobs, selected, onSelect }) {
  return (
    <div className="lob-selector">
      <span>Line of Business:</span>
      {lobs.map(l => (
        <button
          key={l.id}
          onClick={() => onSelect(l.id)}
          className={`lob-pill ${selected === l.id ? 'active' : ''}`}
          type="button"
        >
          {selected === l.id && <Check size={17} />}
          {l.label}
        </button>
      ))}
    </div>
  )
}

function ToolCard({ icon: Icon, tone = 'blue', children, featured }) {
  return (
    <section className={`tool-card ${featured ? 'featured' : ''}`}>
      <div className={`card-icon ${tone}`}>
        <Icon size={27} strokeWidth={2.3} />
      </div>
      <div className="card-content">{children}</div>
    </section>
  )
}

function ActionBtn({ tone = 'blue', loading, onClick, children, disabled, icon: Icon = Play }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled || loading}
      className={`action-button ${tone}`}
      type="button"
    >
      {loading ? <span className="spinner" /> : <Icon size={17} />}
      <span>{children}</span>
    </button>
  )
}

function ClearButton({ onClick }) {
  return (
    <button onClick={onClick} className="clear-button" title="Clear" aria-label="Clear" type="button">
      <X size={16} />
    </button>
  )
}

function ViewRulesCard({ lob }) {
  const [open, setOpen] = useState(false)
  const [content, setContent] = useState('')
  const [fetching, setFetching] = useState(false)

  const handleClick = async () => {
    if (open) { setOpen(false); return }
    setFetching(true)
    const data = await api.listRules(lob)
    setContent(data.result || '')
    setFetching(false)
    setOpen(true)
  }

  useEffect(() => { setOpen(false) }, [lob])

  return (
    <ToolCard icon={BookOpenText} tone="blue" featured>
      <div className="browse-row">
        <div className="card-copy">
          <h2>View Rule Library</h2>
          <p>Browse all registered UW rules and test case counts for the selected line of business.</p>
        </div>
        <ActionBtn tone="blue" icon={BookOpenText} loading={fetching} onClick={handleClick}>
          {open ? 'Hide Rules' : 'View Rules'}
        </ActionBtn>
      </div>
      {open && content && (
        <div className="rule-table-wrap">
          <RulesTable raw={content} />
        </div>
      )}
    </ToolCard>
  )
}

function RulesTable({ raw }) {
  const lines = raw.split('\n')
  const tableLines = lines.filter(l => l.startsWith('|'))
  if (!tableLines.length) return <pre className="inline-result">{raw}</pre>

  const headers = tableLines[0].split('|').filter(Boolean).map(h => h.trim())
  const rows = tableLines.slice(2).map(l => l.split('|').filter(Boolean).map(c => c.trim()))

  return (
    <div className="overflow-x-auto">
      <table className="rules-table">
        <thead>
          <tr>
            {headers.map(h => <th key={h}>{h}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i}>
              {row.map((cell, j) => (
                <td key={j}>
                  <span dangerouslySetInnerHTML={{ __html: cell.replace(/`([^`]+)`/g, '<code>$1</code>') }} />
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function parseRuleRows(raw) {
  const rows = raw
    .split('\n')
    .filter(line => line.startsWith('| `'))
    .map(line => {
      const cells = line.split('|').filter(Boolean).map(cell => cell.trim())
      const id = cells[0]?.replace(/`/g, '')
      const name = cells[1] || id
      const severityText = cells[2] || ''
      const cases = cells[3] || ''
      const severity = severityText.replace(/[^\w\s-]/g, '').trim() || 'Unknown'

      return {
        id,
        name,
        severity,
        cases,
        explanation: explainRule(id, name),
      }
    })
    .filter(rule => rule.id)

  return rows
}

function explainRule(id, name) {
  const explanations = {
    AUTO_SR22: 'Checks that drivers requiring an SR-22 certificate are sent to underwriting review.',
    AUTO_LICENSE: 'Checks that suspended or revoked driver licenses trigger underwriting review.',
    AUTO_UNDER25: 'Checks youthful-driver referral behavior for drivers under 25 years old.',
    AUTO_COMBINED_SR22_UNDER25: 'Checks the combined risk of SR-22 filing and a driver under 25.',
    AUTO_COMBINED_SR22_LICENSE: 'Checks the combined risk of SR-22 filing and suspended or revoked license status.',
    AUTO_COMBINED_UNDER25_LEASED: 'Checks under-25 drivers with leased vehicles and loss payee requirements.',
    AUTO_COMBINED_UNDER25_LICENSE: 'Checks under-25 drivers with suspended or revoked license status.',
    AUTO_COMBINED_SR22_LEASED: 'Checks SR-22 drivers with leased vehicles and loss payee requirements.',
    AUTO_TRIPLE_RISK: 'Checks the highest-risk auto profile: SR-22, revoked license, and under-25 driver.',
    AUTO_CLEAN_BASELINE: 'Checks that a clean auto profile can proceed without active UW conditions.',
    HO_PRIOR_LOSSES: 'Checks homeowner profiles with losses in the last three years.',
    HO_REFUSED_DECLINED: 'Checks homeowner profiles with prior refused, declined, or non-renewed coverage.',
    HO_ALL_FLAGS: 'Checks the highest-risk homeowner profile with all major risk flags active.',
    HO_CLEAN_BASELINE: 'Checks that a clean homeowner profile can proceed without active UW conditions.',
  }

  return explanations[id] || `Runs the test cases registered for ${name}.`
}

function DepartmentAuditCard({ lob, run, loading }) {
  const key = `Department Audit - ${lob.toUpperCase()}`
  const est = { auto: '~15-30 min', homeowner: '~10-20 min' }[lob] || ''

  return (
    <ToolCard icon={ClipboardCheck} tone="green">
      <div className="card-copy">
        <h2>Run Department Audit</h2>
        <p>Run all pre-defined test cases for this line of business. Expected runtime: {est}</p>
      </div>
      <div className="card-action-row">
        <ActionBtn
          tone="green"
          icon={ClipboardCheck}
          loading={loading === key}
          onClick={() => run(key, () => api.runAudit(lob))}
        >
          Start Audit
        </ActionBtn>
      </div>
    </ToolCard>
  )
}

function SingleRuleCard({ lob, rules, run, loading }) {
  const [ruleId, setRuleId] = useState('')
  const key = `Rule Test - ${ruleId}`
  const selectedRule = rules.find(rule => rule.id === ruleId)

  return (
    <ToolCard icon={SearchCheck} tone="purple">
      <div className="card-copy">
        <h2>Test One Rule</h2>
        <p>Select a business rule in plain language and run only its related test cases.</p>
      </div>
      <div className="select-wrap uw-select">
        <select
          className="field select-field"
          value={ruleId}
          onChange={e => setRuleId(e.target.value)}
          title={selectedRule?.explanation || 'Choose one underwriting rule to test'}
        >
          <option value="">Select a rule</option>
          {rules.map(rule => (
            <option key={rule.id} value={rule.id} title={rule.explanation}>
              {rule.name}
            </option>
          ))}
        </select>
        <ChevronsUpDown size={16} />
      </div>
      {selectedRule && (
        <div className="rule-help" title={selectedRule.explanation}>
          <Info size={18} />
          <div>
            <strong>{selectedRule.name}</strong>
            <p>{selectedRule.explanation}</p>
            <span>{selectedRule.severity} severity · {selectedRule.cases}</span>
          </div>
        </div>
      )}
      <ActionBtn
        tone="purple"
        icon={SearchCheck}
        loading={loading === key}
        onClick={() => run(key, () => api.runRuleCases(lob, ruleId))}
        disabled={!ruleId}
      >
        Test Rule
      </ActionBtn>
    </ToolCard>
  )
}

function EdgeCaseCard({ lob, run, loading }) {
  const [description, setDescription] = useState('')
  const [expectedOutcome, setExpectedOutcome] = useState('uw_referral')
  const [conditions, setConditions] = useState([''])
  const key = `Edge Case - ${lob.toUpperCase()}`

  const addCondition = () => setConditions(c => [...c, ''])
  const updateCondition = (i, val) => setConditions(c => c.map((x, idx) => idx === i ? val : x))
  const removeCondition = i => setConditions(c => c.filter((_, idx) => idx !== i))

  const handleRun = () => {
    const validConditions = conditions.filter(c => c.trim())
    run(key, () => api.runCustomBoundary(lob, description, expectedOutcome, validConditions))
  }

  return (
    <ToolCard icon={ShieldAlert} tone="blue">
      <div className="card-copy">
        <h2>Test Edge Case</h2>
        <p>Describe a custom risk scenario, set your expectation, and validate the system behavior.</p>
      </div>

      <div className="field-wrap large">
        <textarea
          className="field"
          placeholder={EDGE_PLACEHOLDERS[lob]}
          value={description}
          onChange={e => setDescription(e.target.value)}
        />
        {description && <ClearButton onClick={() => setDescription('')} />}
      </div>

      <div className="outcome-row">
        <span>Expected outcome:</span>
        {['uw_referral', 'policy_bound'].map(o => (
          <button
            key={o}
            onClick={() => setExpectedOutcome(o)}
            className={`outcome-chip ${expectedOutcome === o ? 'active' : ''}`}
            type="button"
          >
            {o === 'uw_referral' ? 'UW Referral' : 'Policy Bound'}
          </button>
        ))}
      </div>

      <div className="conditions-block">
        <div className="conditions-header">
          <span>Expected condition text</span>
          <button onClick={addCondition} className="text-button compact" type="button">
            <Plus size={16} />
            Add
          </button>
        </div>
        {conditions.map((c, i) => (
          <div key={i} className="condition-row">
            <input
              className="field"
              placeholder="Condition substring to match..."
              value={c}
              onChange={e => updateCondition(i, e.target.value)}
            />
            {conditions.length > 1 && (
              <button onClick={() => removeCondition(i)} className="row-remove" title="Remove" type="button">
                <X size={17} />
              </button>
            )}
          </div>
        ))}
      </div>

      <ActionBtn
        tone="blue"
        icon={ShieldAlert}
        loading={loading === key}
        onClick={handleRun}
        disabled={!description.trim()}
      >
        Test Edge Case
      </ActionBtn>
    </ToolCard>
  )
}

function FullAuditCard({ run, loading }) {
  const key = 'Full System Audit - ALL LOBs'

  return (
    <ToolCard icon={AlertTriangle} tone="purple">
      <div className="batch-header">
        <div className="card-copy">
          <h2>Full System Audit</h2>
          <p>Runs every test case across Auto and Homeowner. Expected runtime: 25-40 minutes.</p>
        </div>
        <ActionBtn
          tone="purple"
          icon={AlertTriangle}
          loading={loading === key}
          onClick={() => run(key, () => api.runFullAudit())}
        >
          Launch Audit
        </ActionBtn>
      </div>
    </ToolCard>
  )
}
