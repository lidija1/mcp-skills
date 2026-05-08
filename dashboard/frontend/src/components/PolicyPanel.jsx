import { useState } from 'react'
import { api } from '../utils/api'
import {
  Check,
  ChevronsUpDown,
  Play,
  Plus,
  Route,
  UserPlus,
  X,
  Zap,
  UsersRound,
} from 'lucide-react'

const LOBS = [
  { id: 'auto', label: 'Personal Auto' },
  { id: 'cyber', label: 'Cyber' },
  { id: 'homeowner', label: 'Homeowner' },
]

const QUICK_PLACEHOLDERS = {
  auto: 'e.g. "A 23-year-old driver with an SR-22 on a leased BMW, two at-fault accidents in the past 3 years"',
  cyber: 'e.g. "A fintech startup with 80 employees handling card data, no prior cyber coverage, remote workforce"',
  homeowner: 'e.g. "A homeowner with a 22-year-old roof in a flood zone, prior water damage claim two years ago"',
}

const BUILD_PLACEHOLDERS = {
  auto: 'e.g. "Young male driver, multiple violations, SR-22 filing required..."',
  cyber: 'e.g. "Healthcare company, 200 employees, stores PHI, no MFA in place..."',
  homeowner: 'e.g. "Older home in wildfire zone, prior loss history, wood-shake roof..."',
}

export default function PolicyPanel({ submitJob }) {
  const [lob, setLob] = useState('auto')
  const [loading, setLoading] = useState('')

  const run = async (label, apiFn) => {
    setLoading(label)
    try {
      await submitJob(apiFn, label)
    } finally {
      setLoading('')
    }
  }

  return (
    <div className="panel-stack animate-fade-in">
      <section className="page-heading">
        <h1>Policy Flow Generator</h1>
        <p>Generate realistic customer profiles and run end-to-end insurance policy workflows</p>
      </section>

      <LobSelector lobs={LOBS} selected={lob} onSelect={setLob} />

      <QuickTestCard lob={lob} run={run} loading={loading} />

      <div className="two-column-grid">
        <BuildProfileCard lob={lob} run={run} loading={loading} />
        <RunJourneyCard lob={lob} run={run} loading={loading} />
      </div>

      <BatchTestCard lob={lob} run={run} loading={loading} />
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
      {loading ? <span className="spinner" /> : <Icon size={17} fill="none" />}
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

function QuickTestCard({ lob, run, loading }) {
  const [description, setDescription] = useState('')
  const key = `Quick Policy Test - ${lob.toUpperCase()}`

  const handleRun = () => {
    if (!description.trim()) return
    run(key, () => api.quickRun(lob, description))
  }

  return (
    <ToolCard icon={Zap} tone="blue" featured>
      <div className="card-copy">
        <h2>Quick Policy Test</h2>
        <p>Describe a customer in plain English. We will build their profile and run the full policy journey automatically.</p>
      </div>
      <div className="field-wrap large">
        <textarea
          className="field"
          placeholder={QUICK_PLACEHOLDERS[lob]}
          value={description}
          onChange={e => setDescription(e.target.value)}
        />
        {description && <ClearButton onClick={() => setDescription('')} />}
      </div>
      <ActionBtn
        tone="blue"
        loading={loading === key}
        onClick={handleRun}
        disabled={!description.trim()}
      >
        Run Policy Test
      </ActionBtn>
    </ToolCard>
  )
}

function BuildProfileCard({ lob, run, loading }) {
  const [description, setDescription] = useState('')
  const key = `Build Profile - ${lob.toUpperCase()}`

  const handleRun = () => {
    if (!description.trim()) return
    run(key, () => api.createPersona(lob, description))
  }

  return (
    <ToolCard icon={UserPlus} tone="purple">
      <div className="card-copy">
        <h2>Build Customer Profile</h2>
        <p>Generate structured test data from a description.</p>
      </div>
      <div className="field-wrap">
        <textarea
          className="field"
          placeholder={BUILD_PLACEHOLDERS[lob]}
          value={description}
          onChange={e => setDescription(e.target.value)}
        />
        {description && <ClearButton onClick={() => setDescription('')} />}
      </div>
      <ActionBtn
        tone="purple"
        icon={UserPlus}
        loading={loading === key}
        onClick={handleRun}
        disabled={!description.trim()}
      >
        Build Profile
      </ActionBtn>
    </ToolCard>
  )
}

function RunJourneyCard({ lob, run, loading }) {
  const [personaJson, setPersonaJson] = useState('')
  const key = `Policy Journey - ${lob.toUpperCase()}`

  const handleRun = () => {
    if (!personaJson.trim()) return
    run(key, () => api.runFlow(lob, personaJson))
  }

  return (
    <ToolCard icon={Route} tone="green">
      <div className="card-copy">
        <h2>Run Policy Journey</h2>
        <p>Paste profile JSON from Build Customer Profile</p>
      </div>
      <div className="field-wrap">
        <textarea
          className="field mono"
          placeholder='Paste JSON from "Build Customer Profile"...'
          value={personaJson}
          onChange={e => setPersonaJson(e.target.value)}
        />
        {personaJson && <ClearButton onClick={() => setPersonaJson('')} />}
      </div>
      <ActionBtn
        tone="green"
        loading={loading === key}
        onClick={handleRun}
        disabled={!personaJson.trim()}
      >
        Run Journey
      </ActionBtn>
    </ToolCard>
  )
}

function BatchTestCard({ lob, run, loading }) {
  const [scenarios, setScenarios] = useState([
    { lob: 'auto', description: '' },
    { lob: 'auto', description: '' },
  ])

  const LOBS_SIMPLE = ['auto', 'cyber', 'homeowner']
  const addScenario = () => setScenarios(s => s.length >= 25 ? s : [...s, { lob, description: '' }])
  const removeScenario = i => setScenarios(s => s.filter((_, idx) => idx !== i))
  const updateScenario = (i, field, val) =>
    setScenarios(s => s.map((sc, idx) => idx === i ? { ...sc, [field]: val } : sc))

  const handleRun = () => {
    const valid = scenarios.filter(s => s.description.trim())
    if (!valid.length) return
    run(`Batch Test - ${valid.length} customers`, () => api.batchRun(valid))
  }

  return (
    <ToolCard icon={UsersRound} tone="blue">
      <div className="batch-header">
        <div className="card-copy">
          <h2>Test Multiple Customers</h2>
          <p>Run several policy scenarios back-to-back (max 25)</p>
        </div>
        <button onClick={addScenario} className="text-button" type="button">
          <Plus size={17} />
          Add Customer
        </button>
      </div>

      <div className="scenario-list">
        {scenarios.map((sc, i) => (
          <div key={i} className="scenario-row">
            <div className="select-wrap">
              <select
                className="field select-field"
                value={sc.lob}
                onChange={e => updateScenario(i, 'lob', e.target.value)}
              >
                {LOBS_SIMPLE.map(l => <option key={l} value={l}>{l}</option>)}
              </select>
              <ChevronsUpDown size={16} />
            </div>
            <input
              className="field"
              placeholder={`Customer ${i + 1} description...`}
              value={sc.description}
              onChange={e => updateScenario(i, 'description', e.target.value)}
            />
            {scenarios.length > 1 && (
              <button onClick={() => removeScenario(i)} className="row-remove" title="Remove" type="button">
                <X size={17} />
              </button>
            )}
          </div>
        ))}
      </div>

      <ActionBtn
        tone="blue"
        icon={UsersRound}
        loading={loading.startsWith('Batch Test')}
        onClick={handleRun}
        disabled={!scenarios.some(s => s.description.trim())}
      >
        Test All Customers
      </ActionBtn>
    </ToolCard>
  )
}
