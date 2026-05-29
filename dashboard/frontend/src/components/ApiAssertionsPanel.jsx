import {useEffect, useMemo, useState} from 'react'
import {api} from '../utils/api'
import {
  AlertTriangle,
  Bookmark,
  BookmarkCheck,
  Check,
  ClipboardCheck,
  Layers,
  Play,
  Plus,
  ShieldCheck,
  SlidersHorizontal,
  Sparkles,
  Trash2,
  WandSparkles,
  X,
  Zap,
} from 'lucide-react'

const SINGLE_EXAMPLES = [
  'Generate a young driver with Gold coverage and assert premium is around 1000 USD',
  'Generate a 22 year old driver with SR-22 and assert underwriting referral contains "All drivers under 25 years of age"',
  'Generate a clean adult driver with Gold coverage and assert premium is less than 2500 USD',
  'Generate a driver under 25 with Bronze coverage and assert flow is not blocked',
]

const DRIVER_PROFILES = [
  {value: 'young', label: 'Young driver', text: 'young driver under 25'},
  {value: 'middle', label: 'Middle-aged driver', text: 'middle-aged adult driver'},
  {value: 'senior', label: 'Senior driver', text: 'senior driver'},
  {value: 'teen', label: 'Teen driver', text: 'teen driver'},
  {value: 'custom', label: 'Custom age', text: 'driver'},
]

const COVERAGES = ['Bronze', 'Silver', 'Gold', 'Platinum']
const EMPLOYMENT = ['Employed', 'Unemployed', 'Retired', 'Student']
const OCCUPATIONS = ['Day Care', 'Office worker', 'Healthcare worker', 'Teacher', 'Retail worker', 'Contractor']
const LICENSE_STATUSES = ['Active License', 'Suspended', 'Revoked']
const VEHICLE_USES = ['Pleasure', 'Commute', 'Business']
const OWNERSHIPS = ['Owned', 'Leased', 'Financed']
const MARITAL_STATUSES = ['Single', 'Married', 'Divorced', 'Widowed']
const GENDERS = ['Male', 'Female']
const DAMAGE_OPTIONS = ['No prior damage', 'Prior damage']

const ASSERTION_TYPES = [
  {value: 'total_premium', label: 'Total premium'},
  {value: 'total_cost', label: 'Total cost'},
  {value: 'policy_status', label: 'Policy status'},
  {value: 'uw_condition_text', label: 'UW condition text'},
  {value: 'coverage', label: 'Coverage'},
  {value: 'base_rate_coverage', label: 'Base rate for a coverage'},
  {value: 'premium_summary_tab', label: 'Total premium (from Summary tab)'},
]

const PREMIUM_OPERATORS = [
  {value: 'lt', label: 'less than'},
  {value: 'gt', label: 'greater than'},
  {value: 'between', label: 'between'},
  {value: 'approx', label: 'around'},
  {value: 'equals', label: 'equals'},
]

const BASE_RATE_COVERAGES = [
  'Bodily Injury',
  'Collision',
  'Comprehensive',
  'Medical Payments',
  'Personal Injury Protection',
  'Property Damage',
  'Uninsured Motorist Bodily Injury',
  'Uninsured Motorist Property Damage',
]

const POLICY_STATUSES = ['Rated', 'Referral', 'Issued', 'Bound', 'Cancelled']

const VARIATION_STRATEGIES = [
  {
    title: 'Clean baseline',
    apply: base => ({
      ...base,
      sr22: 'No',
      licenseStatus: 'Active License',
      damageInfo: 'No prior damage',
      vehicleUse: base.vehicleUse || 'Pleasure',
      ownership: base.ownership || 'Owned',
    }),
  },
  {
    title: 'Coverage sensitivity',
    apply: base => ({
      ...base,
      coverage: nextFrom(COVERAGES, base.coverage),
      sr22: 'No',
      licenseStatus: 'Active License',
    }),
  },
  {
    title: 'Business use',
    apply: base => ({
      ...base,
      vehicleUse: 'Business',
      employment: 'Employed',
      sr22: 'No',
      licenseStatus: 'Active License',
    }),
  },
  {
    title: 'SR-22 trigger',
    apply: base => ({
      ...base,
      sr22: 'Yes',
      licenseStatus: 'Active License',
    }),
  },
  {
    title: 'License trigger',
    apply: base => ({
      ...base,
      licenseStatus: base.licenseStatus === 'Revoked' ? 'Suspended' : 'Revoked',
      sr22: 'No',
    }),
  },
  {
    title: 'Leased high coverage',
    apply: base => ({
      ...base,
      ownership: 'Leased',
      coverage: 'Platinum',
      vehicleUse: base.vehicleUse === 'Business' ? 'Business' : 'Commute',
    }),
  },
]

const SUITE_PRESETS = [
  {
    name: 'SR-22 Regression',
    prompts: [
      'Generate a 22-year-old driver with SR-22 and Gold coverage and assert UW condition contains sr-22',
      'Generate a clean 35-year-old driver with Gold coverage and assert flow is not blocked',
      'Generate a 19-year-old driver with Gold coverage and assert premium is less than 2000',
    ],
  },
  {
    name: 'Premium Range Check',
    prompts: [
      'Generate a young driver with Bronze coverage and assert premium is greater than 500',
      'Generate a clean middle-aged driver with Silver coverage and assert premium is between 600 and 1800',
      'Generate a clean senior driver with Gold coverage and assert premium is less than 2500',
    ],
  },
]

const DEFAULT_BUILDER = {
  driverProfile: 'middle',
  customAge: '35',
  gender: 'Male',
  maritalStatus: 'Married',
  employment: 'Employed',
  occupation: 'Day Care',
  licenseStatus: 'Active License',
  sr22: 'No',
  damageInfo: 'No prior damage',
  coverage: 'Gold',
  vehicleUse: 'Pleasure',
  ownership: 'Owned',
  assertionType: 'total_premium',
  premiumOperator: 'lt',
  premiumTarget: '1500',
  premiumMin: '600',
  premiumMax: '2200',
  baseCoverage: 'Bodily Injury',
  baseCoverageExpected: '281',
  totalCostTarget: '2500',
  policyStatusExpected: 'Rated',
  uwConditionText: 'SR-22',
  variationCount: 3,
}

export default function ApiAssertionsPanel({submitJob}) {
  const [activeTab, setActiveTab] = useState('single')

  const [prompt, setPrompt] = useState('')
  const [loadingSingle, setLoadingSingle] = useState(false)
  const [submittedSingle, setSubmittedSingle] = useState(false)

  const [suiteName, setSuiteName] = useState('')
  const [suitePrompts, setSuitePrompts] = useState(['', ''])
  const [loadingSuite, setLoadingSuite] = useState(false)
  const [submittedSuite, setSubmittedSuite] = useState(false)
  const [builder, setBuilder] = useState(DEFAULT_BUILDER)
  const [sharedPersona, setSharedPersona] = useState(true)
  const [loadingSmartVariations, setLoadingSmartVariations] = useState(false)
  const [smartVariationsError, setSmartVariationsError] = useState('')
  const [savedSuites, setSavedSuites] = useState([])
  const [savingSuite, setSavingSuite] = useState(false)
  const [savedConfirm, setSavedConfirm] = useState(false)

  const generatedPrompt = useMemo(() => buildPrompt(builder), [builder])
  const filledCount = suitePrompts.filter(p => p.trim()).length

  useEffect(() => {
    api.getSuites().then(data => setSavedSuites(data.suites || [])).catch(() => {})
  }, [])

  const handleSaveSuite = async () => {
    const filled = suitePrompts.filter(p => p.trim())
    if (filled.length === 0) return
    const name = suiteName.trim() || `Auto Suite (${filled.length} assertions)`
    setSavingSuite(true)
    try {
      const saved = await api.saveSuite(name, filled, builder, sharedPersona)
      setSavedSuites(prev => [saved, ...prev])
      setSavedConfirm(true)
      setTimeout(() => setSavedConfirm(false), 2500)
    } catch (_) {
      // silently ignore — network error doesn't block workflow
    } finally {
      setSavingSuite(false)
    }
  }

  const handleDeleteSaved = async id => {
    try {
      await api.deleteSuite(id)
      setSavedSuites(prev => prev.filter(s => s.id !== id))
    } catch (_) {}
  }

  const handleRunSingle = async () => {
    if (!prompt.trim()) return
    setLoadingSingle(true)
    setSubmittedSingle(false)
    try {
      await submitJob(
        () => api.runApiPlainAssertion(prompt),
        `API Assertion - ${prompt.slice(0, 54)}`,
        {metadata: {lob: 'auto', lob_display: 'Personal Auto'}},
      )
      setSubmittedSingle(true)
      setTimeout(() => setSubmittedSingle(false), 3000)
    } finally {
      setLoadingSingle(false)
    }
  }

  const handleRunSuite = async () => {
    const filled = suitePrompts.filter(p => p.trim())
    if (filled.length === 0) return
    setLoadingSuite(true)
    setSubmittedSuite(false)
    const name = suiteName.trim() || `Auto Suite (${filled.length} assertions)`
    const personaDescription = sharedPersona ? buildPersonaDescription(builder) : null
    try {
      await submitJob(
        () => api.runApiSuite(filled, name, personaDescription),
        `API Suite - ${name}`,
        {metadata: {lob: 'auto', lob_display: 'Personal Auto'}},
      )
      setSubmittedSuite(true)
      setTimeout(() => setSubmittedSuite(false), 3000)
    } finally {
      setLoadingSuite(false)
    }
  }

  const updateBuilder = (key, value) => setBuilder(prev => ({...prev, [key]: value}))
  const addPromptRow = () => setSuitePrompts(prev => (prev.length >= 20 ? prev : [...prev, generatedPrompt]))
  const removePromptRow = i => setSuitePrompts(prev => prev.filter((_, idx) => idx !== i))
  const updatePromptRow = (i, val) =>
    setSuitePrompts(prev => prev.map((p, idx) => (idx === i ? val : p)))

  const loadPreset = preset => {
    setSuiteName(preset.name)
    setSuitePrompts(preset.prompts.slice(0, 20))
  }

  const loadSaved = saved => {
    setSuiteName(saved.name)
    setSuitePrompts(saved.prompts.slice(0, 20))
    if (saved.builder && Object.keys(saved.builder).length > 0) {
      setBuilder(prev => ({...prev, ...saved.builder}))
    }
    setSharedPersona(saved.shared_persona)
    setActiveTab('suite')
  }

  const useCurrentPrompt = () => {
    setSuitePrompts([generatedPrompt])
    setSuiteName(suiteName || promptSuiteName(builder))
  }

  const generateVariations = () => {
    const count = Number(builder.variationCount) || 1
    const variations = Array.from({length: Math.min(20, Math.max(1, count))}, (_, index) => {
      const strategy = VARIATION_STRATEGIES[index % VARIATION_STRATEGIES.length]
      const variant = strategy.apply(builder)
      return buildPrompt(variant, {
        note: strategy.title,
        index: index + 1,
        count,
      })
    })
    setSuitePrompts(variations)
    setSuiteName(suiteName || promptSuiteName(builder))
  }

  const generateSmartVariations = async () => {
    setLoadingSmartVariations(true)
    setSmartVariationsError('')
    try {
      const count = Number(builder.variationCount) || 3
      const {variations} = await api.smartVariations(builder, count)
      if (!variations || variations.length === 0) {
        setSmartVariationsError('No variations returned.')
        return
      }
      setSuitePrompts(variations.map(v => v.prompt))
      setSuiteName(suiteName || promptSuiteName(builder))
      setSharedPersona(false)
    } catch (err) {
      setSmartVariationsError(err.message || 'Smart variations failed.')
    } finally {
      setLoadingSmartVariations(false)
    }
  }

  return (
    <div className="panel-stack animate-fade-in">
      <section className="panel-hero-card no-icon">
        <div className="panel-hero-copy">
          <span className="overview-eyebrow">
            <ShieldCheck size={14}/>
            API Evidence
          </span>
          <h1>Plain-English API Assertions</h1>
          <p>Generate Auto customers, run OneShield API replay, and validate results from business language - no browser required.</p>
        </div>
      </section>

      <section className="tool-card featured">
        <div className="card-content">
          <div className="api-tab-row" role="group" aria-label="Assertion mode">
            <button
              className={`api-tab-btn ${activeTab === 'single' ? 'active' : ''}`}
              type="button"
              onClick={() => setActiveTab('single')}
            >
              <Zap size={13}/>
              Single Assertion
            </button>
            <button
              className={`api-tab-btn ${activeTab === 'suite' ? 'active' : ''}`}
              type="button"
              onClick={() => setActiveTab('suite')}
            >
              <Layers size={13}/>
              Auto Batch Builder
            </button>
          </div>

          {activeTab === 'single' && (
            <>
              <div className="card-copy">
                <h2>Ask for an API test in plain English</h2>
                <p>The system converts the request into a generated Auto persona, runs the API flow, then checks assertions against API evidence.</p>
              </div>

              <div className="field-wrap large">
                <textarea
                  className="field"
                  value={prompt}
                  onChange={e => setPrompt(e.target.value)}
                  placeholder="e.g. Generate a young driver with Gold coverage and assert premium is around 1000 USD"
                />
                {prompt && (
                  <button
                    onClick={() => setPrompt('')}
                    className="clear-button"
                    title="Clear"
                    aria-label="Clear"
                    type="button"
                  >
                    <X size={16}/>
                  </button>
                )}
              </div>

              <div className="card-action-row">
                <button
                  onClick={handleRunSingle}
                  disabled={!prompt.trim() || loadingSingle}
                  className={`action-button blue ${submittedSingle ? 'completed' : ''}`}
                  type="button"
                >
                  {loadingSingle
                    ? <span className="spinner"/>
                    : submittedSingle
                      ? <Check size={17}/>
                      : <Play size={17}/>}
                  <span>
                    {loadingSingle ? 'Submitting...' : submittedSingle ? 'Submitted' : 'Run API Assertion'}
                  </span>
                </button>
              </div>
            </>
          )}

          {activeTab === 'suite' && (
            <AutoBatchBuilder
              builder={builder}
              generatedPrompt={generatedPrompt}
              suiteName={suiteName}
              suitePrompts={suitePrompts}
              filledCount={filledCount}
              loadingSuite={loadingSuite}
              submittedSuite={submittedSuite}
              loadingSmartVariations={loadingSmartVariations}
              smartVariationsError={smartVariationsError}
              sharedPersona={sharedPersona}
              savingSuite={savingSuite}
              savedConfirm={savedConfirm}
              onBuilderChange={updateBuilder}
              onSuiteNameChange={setSuiteName}
              onSharedPersonaChange={setSharedPersona}
              onUseCurrentPrompt={useCurrentPrompt}
              onGenerateVariations={generateVariations}
              onSmartVariations={generateSmartVariations}
              onAddPrompt={addPromptRow}
              onRemovePrompt={removePromptRow}
              onPromptChange={updatePromptRow}
              onRunSuite={handleRunSuite}
              onSaveSuite={handleSaveSuite}
            />
          )}
        </div>
      </section>

      {activeTab === 'single' && (
        <section className="tool-card">
          <div className="card-content">
            <div className="batch-header">
              <div className="card-copy">
                <h2>Business examples</h2>
                <p>Click to load into the assertion field. Runs live API replay - no policy is bound.</p>
              </div>
              <ClipboardCheck size={24}/>
            </div>
            <div className="scenario-list">
              {SINGLE_EXAMPLES.map(example => (
                <button
                  key={example}
                  className="text-button"
                  type="button"
                  onClick={() => setPrompt(example)}
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        </section>
      )}

      {activeTab === 'suite' && (
        <section className="tool-card">
          <div className="card-content">
            <div className="batch-header">
              <div className="card-copy">
                <h2>Preset suites</h2>
                <p>Load a ready-made regression suite, then edit any generated prompt before running.</p>
              </div>
              <ClipboardCheck size={24}/>
            </div>
            <div className="scenario-list">
              {SUITE_PRESETS.map(preset => (
                <button
                  key={preset.name}
                  className="text-button"
                  type="button"
                  onClick={() => loadPreset(preset)}
                >
                  <Layers size={14}/>
                  {preset.name} - {preset.prompts.length} assertions
                </button>
              ))}
            </div>

            {savedSuites.length > 0 && (
              <>
                <div className="batch-header" style={{marginTop: '1.25rem'}}>
                  <div className="card-copy">
                    <h2>Saved suites</h2>
                    <p>Your saved suite definitions — click to restore the full builder state.</p>
                  </div>
                  <Bookmark size={24}/>
                </div>
                <div className="scenario-list">
                  {savedSuites.map(suite => (
                    <div key={suite.id} className="saved-suite-row">
                      <button
                        className="text-button"
                        type="button"
                        onClick={() => loadSaved(suite)}
                      >
                        <BookmarkCheck size={14}/>
                        {suite.name} - {suite.prompts.length} assertion{suite.prompts.length !== 1 ? 's' : ''}
                      </button>
                      <button
                        className="icon-button danger"
                        type="button"
                        title="Delete saved suite"
                        onClick={() => handleDeleteSaved(suite.id)}
                      >
                        <Trash2 size={13}/>
                      </button>
                    </div>
                  ))}
                </div>
              </>
            )}
          </div>
        </section>
      )}
    </div>
  )
}

function AutoBatchBuilder({
  builder,
  generatedPrompt,
  suiteName,
  suitePrompts,
  filledCount,
  loadingSuite,
  submittedSuite,
  loadingSmartVariations,
  smartVariationsError,
  sharedPersona,
  savingSuite,
  savedConfirm,
  onBuilderChange,
  onSuiteNameChange,
  onSharedPersonaChange,
  onUseCurrentPrompt,
  onGenerateVariations,
  onSmartVariations,
  onAddPrompt,
  onRemovePrompt,
  onPromptChange,
  onRunSuite,
  onSaveSuite,
}) {
  const suggestion = useMemo(() => getAssertionSuggestion(builder), [builder])
  const triggerKey = `${builder.sr22}|${builder.licenseStatus}|${builder.driverProfile}|${builder.customAge}`
  const [dismissedForKey, setDismissedForKey] = useState(null)
  const showSuggestion = suggestion && builder.assertionType !== suggestion.type && dismissedForKey !== triggerKey

  return (
    <>
      <div className="batch-builder-header">
        <div className="card-copy">
          <h2>Create Auto assertions from controlled inputs</h2>
          <p>Choose driver, coverage, risk, vehicle, and assertion criteria. The generated prompts remain editable and are saved into the job report.</p>
        </div>
        <span className="suite-pill">
          <Sparkles size={14}/>
          6 parallel · 20 max
        </span>
      </div>

      <div className="suite-form-grid">
        <FieldSelect
          label="Driver profile"
          value={builder.driverProfile}
          onChange={value => onBuilderChange('driverProfile', value)}
          options={DRIVER_PROFILES.map(item => ({value: item.value, label: item.label}))}
        />
        <FieldInput
          label="Exact age"
          value={builder.customAge}
          disabled={builder.driverProfile !== 'custom'}
          onChange={value => onBuilderChange('customAge', value)}
          type="number"
          min="16"
          max="90"
        />
        <FieldSelect
          label="Coverage"
          value={builder.coverage}
          onChange={value => onBuilderChange('coverage', value)}
          options={COVERAGES}
        />
        <FieldSelect
          label="Assertion"
          value={builder.assertionType}
          onChange={value => onBuilderChange('assertionType', value)}
          options={ASSERTION_TYPES}
        />
      </div>

      {showSuggestion && (
        <div className="assertion-suggestion">
          <AlertTriangle size={14} className="assertion-suggestion-icon"/>
          <span>
            <strong>{suggestion.label}</strong> is the meaningful assertion here — {suggestion.reason}.
          </span>
          <button
            type="button"
            className="assertion-suggestion-apply"
            onClick={() => onBuilderChange('assertionType', suggestion.type)}
          >
            Apply
          </button>
          <button
            type="button"
            className="assertion-suggestion-dismiss"
            aria-label="Dismiss suggestion"
            onClick={() => setDismissedForKey(triggerKey)}
          >
            <X size={13}/>
          </button>
        </div>
      )}

      <div className="suite-section-title">
        <SlidersHorizontal size={15}/>
        Driver and risk details
      </div>
      <div className="suite-form-grid dense">
        <FieldSelect label="Gender" value={builder.gender} onChange={value => onBuilderChange('gender', value)} options={GENDERS}/>
        <FieldSelect label="Marital status" value={builder.maritalStatus} onChange={value => onBuilderChange('maritalStatus', value)} options={MARITAL_STATUSES}/>
        <FieldSelect label="Employment" value={builder.employment} onChange={value => onBuilderChange('employment', value)} options={EMPLOYMENT}/>
        <FieldSelect label="Occupation" value={builder.occupation} onChange={value => onBuilderChange('occupation', value)} options={OCCUPATIONS}/>
        <FieldSelect label="License" value={builder.licenseStatus} onChange={value => onBuilderChange('licenseStatus', value)} options={LICENSE_STATUSES}/>
        <FieldSelect label="SR-22" value={builder.sr22} onChange={value => onBuilderChange('sr22', value)} options={['No', 'Yes']}/>
      </div>

      <div className="suite-section-title">
        <Layers size={15}/>
        Vehicle and rating inputs
      </div>
      <div className="suite-form-grid dense">
        <FieldSelect label="Vehicle use" value={builder.vehicleUse} onChange={value => onBuilderChange('vehicleUse', value)} options={VEHICLE_USES}/>
        <FieldSelect label="Ownership" value={builder.ownership} onChange={value => onBuilderChange('ownership', value)} options={OWNERSHIPS}/>
        <FieldSelect label="Prior damage" value={builder.damageInfo} onChange={value => onBuilderChange('damageInfo', value)} options={DAMAGE_OPTIONS}/>
        <FieldSelect
          label="Variations"
          value={String(builder.variationCount)}
          onChange={value => onBuilderChange('variationCount', Number(value))}
          options={['1', '2', '3', '4', '5', '6', '8', '10', '12', '15', '20']}
        />
      </div>

      {(builder.assertionType === 'total_premium' || builder.assertionType === 'premium_summary_tab') && (
        <div className="suite-form-grid dense">
          <FieldSelect
            label="Operator"
            value={builder.premiumOperator}
            onChange={value => onBuilderChange('premiumOperator', value)}
            options={PREMIUM_OPERATORS}
          />
          {builder.premiumOperator === 'between' ? (
            <>
              <FieldInput label="Min premium" value={builder.premiumMin} onChange={value => onBuilderChange('premiumMin', value)} type="number"/>
              <FieldInput label="Max premium" value={builder.premiumMax} onChange={value => onBuilderChange('premiumMax', value)} type="number"/>
            </>
          ) : (
            <FieldInput label="Premium target" value={builder.premiumTarget} onChange={value => onBuilderChange('premiumTarget', value)} type="number"/>
          )}
        </div>
      )}

      {builder.assertionType === 'base_rate_coverage' && (
        <div className="suite-form-grid dense">
          <FieldSelect
            label="Coverage"
            value={builder.baseCoverage}
            onChange={value => onBuilderChange('baseCoverage', value)}
            options={BASE_RATE_COVERAGES}
          />
          <FieldInput
            label="Expected base rate"
            value={builder.baseCoverageExpected}
            onChange={value => onBuilderChange('baseCoverageExpected', value)}
            type="number"
          />
        </div>
      )}

      {builder.assertionType === 'total_cost' && (
        <div className="suite-form-grid dense">
          <FieldInput label="Total cost target" value={builder.totalCostTarget} onChange={value => onBuilderChange('totalCostTarget', value)} type="number"/>
        </div>
      )}

      {builder.assertionType === 'policy_status' && (
        <div className="suite-form-grid dense">
          <FieldSelect
            label="Expected status"
            value={builder.policyStatusExpected}
            onChange={value => onBuilderChange('policyStatusExpected', value)}
            options={POLICY_STATUSES}
          />
        </div>
      )}

      {builder.assertionType === 'uw_condition_text' && (
        <div className="suite-form-grid dense">
          <FieldInput label="Condition text" value={builder.uwConditionText} onChange={value => onBuilderChange('uwConditionText', value)}/>
        </div>
      )}

      <div className="suite-preview">
        <div className="suite-preview-heading">
          <div>
            <strong>Prompt preview</strong>
            <span>This exact text will be sent unless you edit it below.</span>
          </div>
          <button className="text-button" type="button" onClick={onUseCurrentPrompt}>
            <Plus size={14}/>
            Use this prompt
          </button>
        </div>
        <p>{generatedPrompt}</p>
      </div>

      <div className="suite-toolbar">
        <div className="field-wrap suite-name-wrap">
          <input
            type="text"
            className="field"
            value={suiteName}
            onChange={e => onSuiteNameChange(e.target.value)}
            placeholder="Suite name, e.g. Auto Premium Sensitivity"
          />
        </div>
        <label
          className="shared-persona-toggle"
          title={sharedPersona
            ? 'One persona generated and reused across all assertions — coverage is the isolated variable'
            : 'Each assertion generates its own persona — use for intentional risk-profile variation'}
        >
          <input
            type="checkbox"
            checked={sharedPersona}
            onChange={e => onSharedPersonaChange(e.target.checked)}
          />
          Shared persona
        </label>
        <button
          className="action-button purple"
          type="button"
          onClick={onSmartVariations}
          disabled={loadingSmartVariations}
          title="Ask local AI to suggest UW boundary variations targeting distinct rules"
        >
          {loadingSmartVariations ? <span className="spinner"/> : <Sparkles size={17}/>}
          <span>{loadingSmartVariations ? 'Thinking...' : `Smart Variations`}</span>
        </button>
        <button className="action-button ghost" type="button" onClick={onGenerateVariations}>
          <WandSparkles size={17}/>
          <span>Generate {builder.variationCount}</span>
        </button>
        <button
          className={`action-button ghost ${savedConfirm ? 'completed' : ''}`}
          type="button"
          onClick={onSaveSuite}
          disabled={savingSuite || filledCount === 0}
          title="Save this suite definition for later"
        >
          {savingSuite
            ? <span className="spinner"/>
            : savedConfirm
              ? <BookmarkCheck size={17}/>
              : <Bookmark size={17}/>}
          <span>{savedConfirm ? 'Saved' : 'Save Suite'}</span>
        </button>
      </div>
      {smartVariationsError && (
        <p className="suite-error">{smartVariationsError}</p>
      )}

      <div className="suite-prompt-editor">
        <div className="suite-prompt-editor-header">
          <strong>Generated prompts</strong>
          <span>{filledCount} / 6 ready</span>
        </div>
        {suitePrompts.map((p, i) => (
          <div key={i} className="prompt-row structured">
            <label>Assertion {i + 1}</label>
            <textarea
              className="field"
              value={p}
              onChange={e => onPromptChange(i, e.target.value)}
              placeholder={`Prompt for assertion ${i + 1}`}
            />
            {suitePrompts.length > 1 && (
              <button
                className="row-remove"
                type="button"
                aria-label={`Remove assertion ${i + 1}`}
                onClick={() => onRemovePrompt(i)}
              >
                <X size={14}/>
              </button>
            )}
          </div>
        ))}
      </div>

      <div className="suite-add-row">
        <button
          className="text-button"
          type="button"
          onClick={onAddPrompt}
          disabled={suitePrompts.length >= 20}
        >
          <Plus size={14}/>
          Add prompt
        </button>
        <span className="suite-count">{filledCount} filled · {20 - suitePrompts.length} slots left · 6 run in parallel</span>
      </div>

      <div className="card-action-row">
        <button
          onClick={onRunSuite}
          disabled={filledCount === 0 || loadingSuite}
          className={`action-button blue ${submittedSuite ? 'completed' : ''}`}
          type="button"
        >
          {loadingSuite
            ? <span className="spinner"/>
            : submittedSuite
              ? <Check size={17}/>
              : <Layers size={17}/>}
          <span>
            {loadingSuite
              ? 'Submitting...'
              : submittedSuite
                ? 'Submitted'
                : `Run Suite (${filledCount})`}
          </span>
        </button>
      </div>
    </>
  )
}

function FieldSelect({label, value, onChange, options}) {
  const normalized = options.map(option =>
    typeof option === 'string' ? {value: option, label: option} : option
  )
  return (
    <label className="builder-field">
      <span>{label}</span>
      <select className="field select-field" value={value} onChange={e => onChange(e.target.value)}>
        {normalized.map(option => (
          <option key={option.value} value={option.value}>{option.label}</option>
        ))}
      </select>
    </label>
  )
}

function FieldInput({label, value, onChange, disabled = false, type = 'text', min, max}) {
  return (
    <label className="builder-field">
      <span>{label}</span>
      <input
        className="field"
        value={value}
        disabled={disabled}
        type={type}
        min={min}
        max={max}
        onChange={e => onChange(e.target.value)}
      />
    </label>
  )
}

function personaDetails(config) {
  return [
    driverText(config),
    `${config.gender.toLowerCase()} driver`,
    `${config.maritalStatus.toLowerCase()} marital status`,
    `${config.employment.toLowerCase()} employment category`,
    `occupation ${config.occupation}`,
    `${config.licenseStatus} license status`,
    config.sr22 === 'Yes' ? 'with SR-22 filing in Massachusetts' : 'without SR-22',
    config.damageInfo === 'Prior damage' ? 'with prior vehicle damage' : 'with no prior damage',
    `${config.vehicleUse.toLowerCase()} vehicle use`,
    `${config.ownership.toLowerCase()} vehicle`,
    `${config.coverage} coverage`,
  ]
}

function buildPersonaDescription(config) {
  return personaDetails(config).join(', ')
}

function buildPrompt(config, variation = null) {
  const details = personaDetails(config)
  const variationPrefix = variation
    ? `Generate Auto variation ${variation.index} of ${variation.count} (${variation.note}) for `
    : 'Generate Auto persona for '
  return `${variationPrefix}${details.join(', ')} and ${assertionText(config)}.`
}

function driverText(config) {
  if (config.driverProfile === 'custom') {
    return `${config.customAge || 35}-year-old driver`
  }
  const profile = DRIVER_PROFILES.find(item => item.value === config.driverProfile)
  return profile?.text || 'driver'
}

function assertionText(config) {
  switch (config.assertionType) {
    case 'total_premium':
    case 'premium_summary_tab': {
      const op = config.premiumOperator || 'lt'
      if (op === 'between') return `assert premium is between ${config.premiumMin || 600} and ${config.premiumMax || 2200}`
      if (op === 'approx') return `assert premium is around ${config.premiumTarget || 1500} USD`
      if (op === 'gt') return `assert premium is greater than ${config.premiumTarget || 1500}`
      if (op === 'equals') return `assert premium equals ${config.premiumTarget || 1500}`
      return `assert premium is less than ${config.premiumTarget || 1500}`
    }
    case 'total_cost':
      return `assert total cost is less than ${config.totalCostTarget || 2500}`
    case 'policy_status':
      return `assert policy status equals ${config.policyStatusExpected || 'Rated'}`
    case 'uw_condition_text':
      return `assert UW condition contains "${config.uwConditionText || 'SR-22'}"`
    case 'coverage':
      return `assert coverage equals ${config.coverage}`
    case 'base_rate_coverage':
      return `base rate for ${config.baseCoverage || 'Bodily Injury'} is ${config.baseCoverageExpected || 281}`
    default:
      return 'assert premium exists'
  }
}

const ASSERTION_SUGGESTION_MAP = [
  {
    test: b => b.sr22 === 'Yes',
    type: 'uw_condition_text',
    reason: 'SR-22 filing almost always triggers a UW referral — assert the condition text directly',
  },
  {
    test: b => b.licenseStatus === 'Suspended' || b.licenseStatus === 'Revoked',
    type: 'uw_condition_text',
    reason: 'Suspended/Revoked license is a UW rule trigger — assert the condition text directly',
  },
  {
    test: b =>
      b.driverProfile === 'young' ||
      b.driverProfile === 'teen' ||
      (b.driverProfile === 'custom' && Number(b.customAge) < 25),
    type: 'uw_condition_text',
    reason: 'Driver under 25 triggers the age-based UW referral rule',
  },
]

function getAssertionSuggestion(builder) {
  for (const rule of ASSERTION_SUGGESTION_MAP) {
    if (rule.test(builder)) {
      return {type: rule.type, label: ASSERTION_TYPES.find(a => a.value === rule.type)?.label, reason: rule.reason}
    }
  }
  return null
}

function nextFrom(values, current) {
  const index = values.indexOf(current)
  return values[(index + 1 + values.length) % values.length]
}

function promptSuiteName(config) {
  const profile = DRIVER_PROFILES.find(item => item.value === config.driverProfile)?.label || 'Auto'
  return `${profile} ${config.coverage} ${ASSERTION_TYPES.find(item => item.value === config.assertionType)?.label || 'Assertions'}`
}
