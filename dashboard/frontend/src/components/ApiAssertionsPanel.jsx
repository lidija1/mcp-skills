import {useCallback, useEffect, useMemo, useState} from 'react'
import {api} from '../utils/api'
import {summarizePersonaDescription} from '../utils/text'
import {
  Check,
  ChevronDown,
  ChevronUp,
  Clock,
  Download,
  History,
  ShieldCheck,
  SlidersHorizontal,
  Target,
  Trash2,
  TrendingUp,
  X,
} from 'lucide-react'

const SWEEP_FOCUS_OPTIONS = [
  {value: '', label: 'All categories'},
  {value: 'risk_adding', label: 'Risk adding only'},
  {value: 'discount', label: 'Discounts only'},
  {value: 'hard_stop', label: 'Hard stops only'},
  {value: 'ladder', label: 'Ladder only'},
]

const SWEEP_EXAMPLES = [
  '35-year-old married driver, Gold coverage, clean record, pleasure use',
  '28-year-old single male driver, Silver coverage, clean record, commute use',
  '45-year-old married female driver, Platinum coverage, clean record, pleasure use',
  '22-year-old single driver, Bronze coverage, clean record, pleasure use',
]

const DRIVER_PROFILES = [
  {value: 'young', label: 'Young driver', text: 'young driver under 25'},
  {value: 'middle', label: 'Middle-aged driver', text: 'middle-aged adult driver'},
  {value: 'senior', label: 'Senior driver', text: 'senior driver'},
  {value: 'teen', label: 'Teen driver', text: 'teen driver'},
  {value: 'custom', label: 'Custom age', text: 'driver'},
]

const COVERAGES = ['Bronze', 'Silver', 'Gold', 'Platinum']
const LICENSE_STATUSES = ['Active License', 'Suspended', 'Revoked']
const VEHICLE_USES = ['Pleasure', 'Commute', 'Business']
const OWNERSHIPS = ['Owned', 'Leased', 'Financed']
const MARITAL_STATUSES = ['Single', 'Married', 'Divorced', 'Widowed']
const GENDERS = ['Male', 'Female']

const DIRECT_ASSERT_TYPES = [
  {value: 'premium', label: 'Total premium (Summary page)'},
  {value: 'total_cost', label: 'Total cost (Verify Billing)'},
]

const OPERATORS = [
  {value: 'approx', label: '≈ Approx (±%)'},
  {value: 'equals', label: '= Exact match'},
  {value: 'gt', label: '> Greater than'},
  {value: 'lt', label: '< Less than'},
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
}

export default function ApiAssertionsPanel({
  submitJob,
  activeTab = 'sweep',
  onActiveTabChange = () => {},
  historyFilter = 'all',
  onHistoryFilterChange = () => {},
  expandedId = null,
  onExpandedIdChange = () => {},
}) {

  // Regression Sweep tab
  const [sweepBaseline, setSweepBaseline] = useState('')
  const [sweepFocus, setSweepFocus] = useState('')
  const [loadingSweep, setLoadingSweep] = useState(false)
  const [submittedSweep, setSubmittedSweep] = useState(false)

  // History tab
  const [historyRows, setHistoryRows] = useState([])
  const [historyLoading, setHistoryLoading] = useState(false)

  const fetchHistory = useCallback(async () => {
    setHistoryLoading(true)
    try {
      const data = await api.getAssertionHistory()
      setHistoryRows(data.results || [])
    } catch {
      setHistoryRows([])
    } finally {
      setHistoryLoading(false)
    }
  }, [])

  useEffect(() => {
    if (activeTab !== 'history') return
    fetchHistory()
  }, [activeTab, fetchHistory])

  const handleDeleteResult = async id => {
    try {
      await api.deleteAssertionResult(id)
      setHistoryRows(prev => prev.filter(r => r.id !== id))
      if (expandedId === id) onExpandedIdChange(null)
    } catch { /* ignore */ }
  }

  // Direct Assert tab
  const [assertBuilder, setAssertBuilder] = useState(DEFAULT_BUILDER)
  const [assertType, setAssertType] = useState('premium')
  const [assertExpected, setAssertExpected] = useState('')
  const [assertOperator, setAssertOperator] = useState('approx')
  const [assertTolerance, setAssertTolerance] = useState('5')
  const [loadingAssert, setLoadingAssert] = useState(false)
  const [submittedAssert, setSubmittedAssert] = useState(false)

  const handleRunSweep = async () => {
    if (!sweepBaseline.trim()) return
    setLoadingSweep(true)
    setSubmittedSweep(false)
    try {
      await submitJob(
        () => api.runRegressionSweep(sweepBaseline, 'auto', sweepFocus || null),
        `Regression Sweep — ${sweepBaseline.slice(0, 50)}`,
        {
          executionType: 'regression_sweep',
          metadata: {
            lob: 'auto',
            lob_display: 'Personal Auto',
            baseline_description: sweepBaseline,
            focus: sweepFocus || null,
            rerun_payload: {baseline_description: sweepBaseline, lob: 'auto', focus: sweepFocus || null},
          },
        },
      )
      setSubmittedSweep(true)
      setTimeout(() => setSubmittedSweep(false), 3000)
    } finally {
      setLoadingSweep(false)
    }
  }

  const handleRunAssertFlow = async () => {
    const expected = parseFloat(assertExpected)
    if (!assertExpected.trim() || isNaN(expected)) return
    const personaDesc = buildPersonaDescription(assertBuilder)
    setLoadingAssert(true)
    setSubmittedAssert(false)
    try {
      await submitJob(
        () => api.runAssertFlow(personaDesc, assertType, expected, assertOperator, parseFloat(assertTolerance) || 5),
        `Assert ${assertType} — ${summarizeAssertPersona(personaDesc)}`,
        {
          executionType: 'api_assert_flow',
          metadata: {
            lob: 'auto',
            lob_display: 'Personal Auto',
            persona_description: personaDesc,
            assertion_type: assertType,
            expected_value: expected,
            operator: assertOperator,
            tolerance_pct: parseFloat(assertTolerance) || 5,
            rerun_payload: {
              persona_description: personaDesc,
              assertion_type: assertType,
              expected_value: expected,
              operator: assertOperator,
              tolerance_pct: parseFloat(assertTolerance) || 5,
              lob: 'auto',
            },
          },
        },
      )
      setSubmittedAssert(true)
      setTimeout(() => setSubmittedAssert(false), 3000)
    } finally {
      setLoadingAssert(false)
    }
  }

  const updateAssertBuilder = (key, value) => setAssertBuilder(prev => ({...prev, [key]: value}))

  return (
    <div className="panel-stack animate-fade-in">
      <section className="panel-hero-card no-icon">
        <div className="panel-hero-copy">
          <span className="overview-eyebrow">
            <ShieldCheck size={14}/>
            UW Evidence
          </span>
          <h1>Assertion Tests</h1>
          <p>Run premium regression sweeps and direct assertions against the OneShield rating flow — no policy is bound.</p>
        </div>
      </section>

      <section className="tool-card featured">
        <div className="card-content">
          <div className="api-tab-row" role="group" aria-label="Assertion mode">
            <button
              className={`api-tab-btn ${activeTab === 'sweep' ? 'active' : ''}`}
              type="button"
              onClick={() => onActiveTabChange('sweep')}
            >
              <TrendingUp size={13}/>
              Regression Sweep
            </button>
            <button
              className={`api-tab-btn ${activeTab === 'assert' ? 'active' : ''}`}
              type="button"
              onClick={() => onActiveTabChange('assert')}
            >
              <Target size={13}/>
              Direct Assert
            </button>
            <button
              className={`api-tab-btn api-tab-btn--history ${activeTab === 'history' ? 'active' : ''}`}
              type="button"
              onClick={() => onActiveTabChange('history')}
            >
              <History size={13}/>
              History
            </button>
          </div>

          {activeTab === 'sweep' && (
            <>
              <div className="card-copy">
                <h2>AI-driven premium regression sweep</h2>
                <p>Describe a clean baseline driver. The system generates variants (risk-adding, discounts, hard stops, ladders), runs them in parallel, and asserts that each mutation moves the premium in the expected direction.</p>
              </div>

              <div className="field-wrap large">
                <textarea
                  className="field"
                  value={sweepBaseline}
                  onChange={e => setSweepBaseline(e.target.value)}
                  placeholder="e.g. 35-year-old married driver, Gold coverage, clean record, pleasure use"
                />
                {sweepBaseline && (
                  <button
                    onClick={() => setSweepBaseline('')}
                    className="clear-button"
                    title="Clear"
                    aria-label="Clear"
                    type="button"
                  >
                    <X size={16}/>
                  </button>
                )}
              </div>

              <div className="suite-form-grid dense">
                <FieldSelect
                  label="Focus category"
                  value={sweepFocus}
                  onChange={setSweepFocus}
                  options={SWEEP_FOCUS_OPTIONS}
                />
              </div>

              <div className="card-action-row">
                <button
                  onClick={handleRunSweep}
                  disabled={!sweepBaseline.trim() || loadingSweep}
                  className={`action-button blue ${submittedSweep ? 'completed' : ''}`}
                  type="button"
                >
                  {loadingSweep
                    ? <span className="spinner"/>
                    : submittedSweep
                      ? <Check size={17}/>
                      : <TrendingUp size={17}/>}
                  <span>
                    {loadingSweep ? 'Submitting...' : submittedSweep ? 'Submitted' : 'Run Regression Sweep'}
                  </span>
                </button>
              </div>
            </>
          )}

          {activeTab === 'history' && (
            <AssertionHistory
              rows={historyRows}
              loading={historyLoading}
              filter={historyFilter}
              onFilterChange={onHistoryFilterChange}
              expandedId={expandedId}
              onExpand={id => onExpandedIdChange(prev => prev === id ? null : id)}
              onDelete={handleDeleteResult}
              onRefresh={fetchHistory}
            />
          )}

          {activeTab === 'assert' && (
            <>
              <div className="card-copy">
                <h2>Assert a specific value against the test result</h2>
                <p>Configure a driver profile, set your expected value and operator, then run — you get a clear PASS or FAIL with per-coverage breakdown.</p>
              </div>

              <div className="suite-form-grid">
                <FieldSelect
                  label="Driver profile"
                  value={assertBuilder.driverProfile}
                  onChange={v => updateAssertBuilder('driverProfile', v)}
                  options={DRIVER_PROFILES.map(i => ({value: i.value, label: i.label}))}
                />
                <FieldInput
                  label="Exact age"
                  value={assertBuilder.customAge}
                  disabled={assertBuilder.driverProfile !== 'custom'}
                  onChange={v => updateAssertBuilder('customAge', v)}
                  type="number"
                  min="16"
                  max="90"
                />
                <FieldSelect
                  label="Coverage"
                  value={assertBuilder.coverage}
                  onChange={v => updateAssertBuilder('coverage', v)}
                  options={COVERAGES}
                />
                <FieldSelect
                  label="Vehicle use"
                  value={assertBuilder.vehicleUse}
                  onChange={v => updateAssertBuilder('vehicleUse', v)}
                  options={VEHICLE_USES}
                />
              </div>

              <div className="suite-section-title">
                <SlidersHorizontal size={15}/>
                Driver details
              </div>
              <div className="suite-form-grid dense">
                <FieldSelect label="Gender" value={assertBuilder.gender} onChange={v => updateAssertBuilder('gender', v)} options={GENDERS}/>
                <FieldSelect label="Marital status" value={assertBuilder.maritalStatus} onChange={v => updateAssertBuilder('maritalStatus', v)} options={MARITAL_STATUSES}/>
                <FieldSelect label="License" value={assertBuilder.licenseStatus} onChange={v => updateAssertBuilder('licenseStatus', v)} options={LICENSE_STATUSES}/>
                <FieldSelect label="SR-22" value={assertBuilder.sr22} onChange={v => updateAssertBuilder('sr22', v)} options={['No', 'Yes']}/>
                <FieldSelect label="Ownership" value={assertBuilder.ownership} onChange={v => updateAssertBuilder('ownership', v)} options={OWNERSHIPS}/>
              </div>

              <div className="suite-section-title">
                <Target size={15}/>
                Assertion
              </div>
              <div className="suite-form-grid">
                <FieldSelect
                  label="Assertion type"
                  value={assertType}
                  onChange={setAssertType}
                  options={DIRECT_ASSERT_TYPES}
                />
                <FieldSelect
                  label="Operator"
                  value={assertOperator}
                  onChange={setAssertOperator}
                  options={OPERATORS}
                />
                <label className="builder-field">
                  <span>Expected value ($)</span>
                  <input
                    className="field"
                    type="number"
                    min="0"
                    step="0.01"
                    value={assertExpected}
                    onChange={e => setAssertExpected(e.target.value)}
                    placeholder="e.g. 2030"
                  />
                </label>
                {assertOperator === 'approx' && (
                  <FieldInput
                    label="Tolerance (%)"
                    value={assertTolerance}
                    onChange={setAssertTolerance}
                    type="number"
                    min="0"
                    max="50"
                  />
                )}
              </div>

              <div className="card-action-row">
                <button
                  onClick={handleRunAssertFlow}
                  disabled={!assertExpected.trim() || isNaN(parseFloat(assertExpected)) || loadingAssert}
                  className={`action-button blue ${submittedAssert ? 'completed' : ''}`}
                  type="button"
                >
                  {loadingAssert
                    ? <span className="spinner"/>
                    : submittedAssert
                      ? <Check size={17}/>
                      : <Target size={17}/>}
                  <span>
                    {loadingAssert ? 'Submitting...' : submittedAssert ? 'Submitted' : 'Run Assertion'}
                  </span>
                </button>
              </div>
            </>
          )}
        </div>
      </section>

      {activeTab === 'sweep' && (
        <section className="tool-card">
          <div className="card-content">
            <div className="batch-header">
              <div className="card-copy">
                <h2>Baseline examples</h2>
                <p>Click to load a clean baseline. The sweep generates all variants automatically.</p>
              </div>
              <TrendingUp size={24}/>
            </div>
            <div className="scenario-list">
              {SWEEP_EXAMPLES.map(example => (
                <button
                  key={example}
                  className="text-button"
                  type="button"
                  onClick={() => setSweepBaseline(example)}
                >
                  {example}
                </button>
              ))}
            </div>
          </div>
        </section>
      )}
    </div>
  )
}

/* ─── Assertion History ───────────────────────────────────────── */

const OP_LABEL = {
  approx:       (tol) => `approx ±${Number(tol).toFixed(0)}%`,
  equals:       () => 'exact',
  eq:           () => 'exact',
  gt:           () => 'greater than',
  greater_than: () => 'greater than',
  lt:           () => 'less than',
  less_than:    () => 'less than',
}

function fmtMoney(v) {
  if (v === null || v === undefined) return 'N/A'
  return `$${Number(v).toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`
}

function fmtDate(ts) {
  if (!ts) return '—'
  return new Date(ts * 1000).toLocaleString('en-US', {
    month: 'short', day: 'numeric', year: 'numeric',
    hour: 'numeric', minute: '2-digit',
  })
}

function fmtPercent(v) {
  if (v === null || v === undefined || Number.isNaN(Number(v))) return 'N/A'
  return `${Number(v).toFixed(1)}%`
}

function isRegressionSweepRow(row) {
  return row.assertion_type === 'regression_sweep' || row.operator === 'sweep'
}

function sweepVariants(row) {
  const variants = row.coverage_premiums?.variants
  return Array.isArray(variants) ? variants : []
}

function historyExpected(row) {
  return isRegressionSweepRow(row) ? 'Sweep' : fmtMoney(row.expected_value)
}

function historyActual(row) {
  return fmtMoney(row.actual_value)
}

function historyType(row) {
  return isRegressionSweepRow(row)
    ? 'regression sweep'
    : (row.assertion_type || '').replace('_', ' ')
}

function downloadPersonaJson(row) {
  const blob = new Blob([JSON.stringify(row.persona || {}, null, 2)], {type: 'application/json'})
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `persona-${row.id || 'export'}.json`
  a.click()
  URL.revokeObjectURL(url)
}

function summarizeAssertPersona(description = '') {
  const parts = String(description).split(',').map(part => part.trim()).filter(Boolean)
  const lowerParts = parts.map(part => [part, part.toLowerCase()])
  const driver = (lowerParts.find(([, low]) => low.includes('driver'))?.[0] || '')
    .replace(/\b(adult\s+)?driver\b/gi, '')
    .trim()
  const genderPart = lowerParts.find(([, low]) => low.includes('female driver') || low.includes('male driver'))?.[1] || ''
  const gender = genderPart.includes('female driver') ? 'female' : genderPart.includes('male driver') ? 'male' : ''
  const driverBits = [driver, gender].filter(bit => bit && !driver.toLowerCase().includes(bit)).join(' ')
  const coverage = (lowerParts.find(([, low]) => low.endsWith('coverage'))?.[0] || '').replace(/\s+coverage$/i, '').trim()
  const license = (lowerParts.find(([, low]) => low.endsWith('license status'))?.[0] || '').replace(/\s+license status$/i, '').trim()
  const vehicleUse = (lowerParts.find(([, low]) => low.endsWith('vehicle use'))?.[0] || '').replace(/\s+vehicle use$/i, '').trim()
  const sr22Part = lowerParts.find(([, low]) => low.includes('sr-22'))?.[1] || ''
  const sr22 = sr22Part.includes('without sr-22') ? 'no SR-22' : sr22Part ? 'SR-22' : ''
  const summary = [driverBits, coverage, license, vehicleUse, sr22].filter(Boolean).join(', ')

  return summary || String(description).slice(0, 80)
}

function AssertionHistory({rows, loading, filter, onFilterChange, expandedId, onExpand, onDelete, onRefresh}) {
  const filtered = useMemo(() => {
    if (filter === 'pass') return rows.filter(r => r.passed)
    if (filter === 'fail') return rows.filter(r => !r.passed)
    return rows
  }, [rows, filter])

  return (
    <div className="ah-root">
      <div className="ah-toolbar">
        <div className="ah-filter-group">
          {['all', 'pass', 'fail'].map(f => (
            <button
              key={f}
              type="button"
              className={`ah-filter-btn ${filter === f ? 'active' : ''}`}
              onClick={() => onFilterChange(f)}
            >
              {f === 'all' ? 'All' : f.toUpperCase()}
            </button>
          ))}
        </div>
        <button type="button" className="ah-refresh-btn" onClick={onRefresh} title="Refresh">
          <Clock size={14}/>
          Refresh
        </button>
      </div>

      {loading ? (
        <div className="ah-empty"><span className="spinner"/></div>
      ) : filtered.length === 0 ? (
        <div className="ah-empty">
          <History size={36} strokeWidth={1.4}/>
          <p>{rows.length === 0 ? 'No assertion results saved yet.' : 'No results match this filter.'}</p>
        </div>
      ) : (
        <div className="ah-table-wrap">
          <table className="ah-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Persona</th>
                <th>Type</th>
                <th>Expected</th>
                <th>Actual</th>
                <th>Result</th>
                <th/>
              </tr>
            </thead>
            <tbody>
              {filtered.map(row => (
                <AssertionHistoryRow
                  key={row.id}
                  row={row}
                  expanded={expandedId === row.id}
                  onExpand={() => onExpand(row.id)}
                  onDelete={() => onDelete(row.id)}
                />
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

function AssertionHistoryRow({row, expanded, onExpand, onDelete}) {
  const [confirmingDelete, setConfirmingDelete] = useState(false)
  const isSweep = isRegressionSweepRow(row)
  const opFn = OP_LABEL[row.operator]
  const opText = opFn ? opFn(row.tolerance_pct) : row.operator
  const coverageEntries = isSweep ? [] : Object.entries(row.coverage_premiums || {})
  const variants = sweepVariants(row)
  const personaDescription = row.persona_description || ''
  const personaSummary = summarizePersonaDescription(personaDescription, 84)
  const confirmDelete = async e => {
    e.stopPropagation()
    setConfirmingDelete(false)
    await onDelete()
  }

  return (
    <>
      <tr className={`ah-row ${expanded ? 'ah-row-expanded' : ''}`} onClick={onExpand}>
        <td className="ah-col-date">{fmtDate(row.created_at)}</td>
        <td className="ah-col-persona" title={personaDescription}>
          <span className="ah-persona-summary">{personaSummary}</span>
        </td>
        <td className="ah-col-type">{historyType(row)}</td>
        <td className="ah-col-money">{historyExpected(row)}</td>
        <td className="ah-col-money">{historyActual(row)}</td>
        <td className="ah-col-result">
          <span className={`ah-verdict ${row.passed ? 'pass' : 'fail'}`}>{row.passed ? 'PASS' : 'FAIL'}</span>
        </td>
        <td className="ah-col-chevron">
          {expanded ? <ChevronUp size={15}/> : <ChevronDown size={15}/>}
        </td>
      </tr>

      {expanded && (
        <tr className="ah-detail-row">
          <td colSpan={7}>
            <div className="ah-detail">
              <div className="ah-detail-prompt">
                <span className="ah-detail-label">Tested persona</span>
                <p>{row.persona_description}</p>
              </div>

              <div className="ah-detail-grid">
                {!isSweep && <div className="ah-detail-kv"><span>Expected</span><strong>{historyExpected(row)}</strong></div>}
                <div className="ah-detail-kv"><span>{isSweep ? 'Baseline Premium' : 'Actual'}</span><strong>{historyActual(row)}</strong></div>
                <div className="ah-detail-kv"><span>{isSweep ? 'Mode' : 'Operator'}</span><strong>{isSweep ? 'Regression sweep' : opText}</strong></div>
                {row.message && <div className="ah-detail-kv ah-detail-kv-wide"><span>Detail</span><strong>{row.message}</strong></div>}
              </div>

              {isSweep && variants.length > 0 && (
                <div className="ah-detail-section">
                  <span className="ah-detail-label">Regression variants</span>
                  <table className="ah-sweep-table">
                    <thead>
                      <tr>
                        <th>Variant</th>
                        <th>Category</th>
                        <th>Expected</th>
                        <th>Premium</th>
                        <th>Delta</th>
                        <th>Result</th>
                        <th>Message</th>
                      </tr>
                    </thead>
                    <tbody>
                      {variants.map((variant, i) => (
                        <tr key={`${variant.variant_id || variant.name || 'variant'}-${i}`}>
                          <td>{variant.name || variant.variant_id || `Variant ${i + 1}`}</td>
                          <td>{variant.category || 'N/A'}</td>
                          <td>{variant.expected_behavior || 'N/A'}</td>
                          <td className="ah-col-money">{fmtMoney(variant.actual_premium)}</td>
                          <td className="ah-col-money">{fmtPercent(variant.delta_pct)}</td>
                          <td><span className={`ah-verdict ${variant.passed ? 'pass' : 'fail'}`}>{variant.passed ? 'PASS' : 'FAIL'}</span></td>
                          <td>{variant.message || 'N/A'}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {isSweep && variants.length === 0 && (
                <div className="ah-detail-section">
                  <span className="ah-detail-label">Regression variants</span>
                  <p className="ah-detail-empty">No variant details were returned for this sweep.</p>
                </div>
              )}

              {coverageEntries.length > 0 && (
                <div className="ah-detail-section">
                  <span className="ah-detail-label">Coverage premiums</span>
                  <table className="ah-coverage-table">
                    <tbody>
                      {coverageEntries.map(([cov, prem]) => (
                        <tr key={cov}><td>{cov}</td><td>{fmtMoney(prem)}</td></tr>
                      ))}
                      <tr className="ah-coverage-total"><td>Total</td><td>{fmtMoney(row.actual_value)}</td></tr>
                    </tbody>
                  </table>
                </div>
              )}

              {row.uw_conditions?.length > 0 && (
                <div className="ah-detail-section">
                  <span className="ah-detail-label">UW conditions</span>
                  <ul className="ah-uw-list">
                    {row.uw_conditions.map((c, i) => <li key={i}>{c}</li>)}
                  </ul>
                </div>
              )}

              <div className="ah-detail-actions">
                {row.persona && Object.keys(row.persona).length > 0 && (
                  <button
                    type="button"
                    className="ah-action-btn"
                    onClick={e => { e.stopPropagation(); downloadPersonaJson(row) }}
                  >
                    <Download size={14}/>
                    Download JSON
                  </button>
                )}
                {confirmingDelete ? (
                  <div className="ah-delete-confirm" onClick={e => e.stopPropagation()}>
                    <span>Are you sure you want to delete?</span>
                    <button
                      type="button"
                      className="ah-confirm-btn"
                      onClick={e => { e.stopPropagation(); setConfirmingDelete(false) }}
                    >
                      Cancel
                    </button>
                    <button
                      type="button"
                      className="ah-action-btn danger ah-confirm-delete"
                      onClick={confirmDelete}
                    >
                      <Trash2 size={14}/>
                      Delete
                    </button>
                  </div>
                ) : (
                  <button
                    type="button"
                    className="ah-action-btn danger"
                    onClick={e => { e.stopPropagation(); setConfirmingDelete(true) }}
                  >
                    <Trash2 size={14}/>
                    Delete
                  </button>
                )}
              </div>
            </div>
          </td>
        </tr>
      )}
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
  const profile = DRIVER_PROFILES.find(i => i.value === config.driverProfile)
  const driverText = config.driverProfile === 'custom'
    ? `${config.customAge || 35}-year-old driver`
    : profile?.text || 'driver'
  return [
    driverText,
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
