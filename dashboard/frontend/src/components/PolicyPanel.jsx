import {useState, useEffect} from 'react'
import {api} from '../utils/api'
import {
    Check,
    ChevronDown,
    Play,
    Sparkles,
    UserPlus,
    X,
} from 'lucide-react'
import {useNavigate, useParams} from 'react-router-dom'

const LOBS = [
    {id: 'personal-auto', label: 'Personal Auto'},
    {id: 'homeowner', label: 'Homeowner'},
]

const QUICK_PLACEHOLDERS = {
    'personal-auto': 'e.g. "A 23-year-old driver with an SR-22 on a leased BMW, two at-fault accidents in the past 3 years"',
    homeowner: 'e.g. "A homeowner with a 22-year-old roof in a flood zone, prior water damage claim two years ago"',
}

const BUILD_PLACEHOLDERS = {
    'personal-auto': 'e.g. "Young male driver, multiple violations, SR-22 filing required..."',
    homeowner: 'e.g. "Older home in wildfire zone, prior loss history, wood-shake roof..."',
}

export default function PolicyPanel({submitJob}) {
    const navigate = useNavigate()
    const {lob: lobFromUrl} = useParams()

    const validLobs = LOBS.map(l => l.id)

    const initialLob = validLobs.includes(lobFromUrl)
        ? lobFromUrl
        : 'personal-auto'

    const [lob, setLob] = useState(initialLob)
    const [loading, setLoading] = useState('')

    useEffect(() => {
        if (lobFromUrl && lobFromUrl !== lob) {
            setLob(lobFromUrl)
        }
    }, [lobFromUrl])

    useEffect(() => {
        navigate(`/policy-flow/${lob}`)
    }, [lob])

    const run = async (label, apiFn) => {
        setLoading(label)
        try {
            await submitJob(apiFn, label)
        } finally {
            setLoading('')
        }
    }

    return (
        <div className="panel-stack policy-panel animate-fade-in">
            <section className="panel-hero-card no-icon">
                <div className="panel-hero-copy">
          <span className="overview-eyebrow">
            <Sparkles size={14}/>
            Insurance Automation
          </span>
                    <h1>Policy Flow Generator</h1>
                    <p>Generate realistic customer profiles and run end-to-end insurance policy workflows</p>
                </div>
            </section>

            <LobSelector
                lobs={LOBS}
                selected={lob}
                onSelect={value => {
                    setLob(value)
                }}
            />

            <QuickTestCard lob={lob} run={run} loading={loading}/>

            <div className="two-column-grid">
                <BuildProfileCard lob={lob} run={run} loading={loading}/>
                <RunJourneyCard lob={lob} run={run} loading={loading}/>
            </div>
        </div>
    )
}

function LobSelector({lobs, selected, onSelect}) {
    return (
        <div className="lob-selector-row">
            <label className="lob-selector-label" htmlFor="lob-select">Line of Business</label>
            <div className="lob-dropdown-wrap">
                <select
                    id="lob-select"
                    className="lob-dropdown"
                    value={selected}
                    onChange={e => onSelect(e.target.value)}
                >
                    {lobs.map(l => (
                        <option key={l.id} value={l.id}>{l.label}</option>
                    ))}
                </select>
                <ChevronDown size={15}/>
            </div>
        </div>
    )
}

function ToolCard({featured, children}) {
    return (
        <section className={`tool-card ${featured ? 'featured' : ''}`}>
            <div className="card-content">{children}</div>
        </section>
    )
}

function ActionBtn({tone = 'blue', loading, completed, onClick, children, disabled, icon: Icon = Play}) {
    return (
        <button
            onClick={onClick}
            disabled={disabled || loading}
            className={`action-button ${tone} ${completed ? 'completed' : ''}`}
            type="button"
        >
            {loading ? <span className="spinner"/> : completed ? <Check size={17}/> : <Icon size={17} fill="none"/>}
            <span>{loading ? 'Submitting…' : completed ? 'Submitted' : children}</span>
        </button>
    )
}

function ClearButton({onClick}) {
    return (
        <button onClick={onClick} className="clear-button" title="Clear" aria-label="Clear" type="button">
            <X size={16}/>
        </button>
    )
}

function QuickTestCard({lob, run, loading}) {
    const [description, setDescription] = useState('')
    const [submitted, setSubmitted] = useState(false)
    const key = `Quick Policy Test - ${lob.toUpperCase()}`

    const handleRun = async () => {
        if (!description.trim()) return
        setSubmitted(false)
        await run(key, () => api.quickRun(lob, description))
        setSubmitted(true)
        setTimeout(() => setSubmitted(false), 3000)
    }

    return (
        <ToolCard featured>
            <div className="card-copy">
                <h2>Quick Policy Test</h2>
                <p>Describe a customer in plain English. We will build their profile and run the full policy journey
                    automatically.</p>
            </div>
            <div className="field-wrap large">
        <textarea
            className="field"
            placeholder={QUICK_PLACEHOLDERS[lob]}
            value={description}
            onChange={e => setDescription(e.target.value)}
        />
                {description && <ClearButton onClick={() => setDescription('')}/>}
            </div>
            <ActionBtn
                tone="blue"
                loading={loading === key}
                completed={submitted}
                onClick={handleRun}
                disabled={!description.trim()}
            >
                Run Policy Test
            </ActionBtn>
        </ToolCard>
    )
}

function BuildProfileCard({lob, run, loading}) {
    const [description, setDescription] = useState('')
    const [submitted, setSubmitted] = useState(false)
    const key = `Build Profile - ${lob.toUpperCase()}`

    const handleRun = async () => {
        if (!description.trim()) return
        setSubmitted(false)
        await run(key, () => api.createPersona(lob, description))
        setSubmitted(true)
        setTimeout(() => setSubmitted(false), 3000)
    }

    return (
        <ToolCard>
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
                {description && <ClearButton onClick={() => setDescription('')}/>}
            </div>
            <ActionBtn
                tone="purple"
                icon={UserPlus}
                loading={loading === key}
                completed={submitted}
                onClick={handleRun}
                disabled={!description.trim()}
            >
                Build Profile
            </ActionBtn>
        </ToolCard>
    )
}

function RunJourneyCard({lob, run, loading}) {
    const [personaJson, setPersonaJson] = useState('')
    const [submitted, setSubmitted] = useState(false)
    const key = `Policy Journey - ${lob.toUpperCase()}`

    const handleRun = async () => {
        if (!personaJson.trim()) return
        setSubmitted(false)
        await run(key, () => api.runFlow(lob, personaJson))
        setSubmitted(true)
        setTimeout(() => setSubmitted(false), 3000)
    }

    return (
        <ToolCard>
            <div className="card-copy">
                <h2>Run Policy Journey</h2>
                <p>Paste profile JSON from Build Customer Profile or enter a TC_ID</p>
            </div>
            <div className="field-wrap">
        <textarea
            className="field mono"
            placeholder='Paste JSON from "Build Customer Profile" or enter TC_ID_0001...'
            value={personaJson}
            onChange={e => setPersonaJson(e.target.value)}
        />
                {personaJson && <ClearButton onClick={() => setPersonaJson('')}/>}
            </div>
            <ActionBtn
                tone="green"
                loading={loading === key}
                completed={submitted}
                onClick={handleRun}
                disabled={!personaJson.trim()}
            >
                Run Journey
            </ActionBtn>
        </ToolCard>
    )
}
