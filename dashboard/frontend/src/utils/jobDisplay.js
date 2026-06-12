import {cleanDisplayText, summarizePersonaDescription, truncateDisplayText} from './text'

const DASH_RE = /\s+-\s+/

function money(value) {
  const numeric = Number(value)
  if (!Number.isFinite(numeric)) return ''
  return `$${numeric.toLocaleString('en-US', {minimumFractionDigits: 2, maximumFractionDigits: 2})}`
}

function operatorText(metadata) {
  const tolerance = Number(metadata.tolerance_pct ?? 5)
  if (metadata.operator === 'approx') {
    return `approx ${Number.isFinite(tolerance) ? tolerance.toFixed(0) : 5}%`
  }
  return metadata.operator || ''
}

function splitDashLabel(label) {
  const normalized = cleanDisplayText(label || '')
  if (!DASH_RE.test(normalized)) return {prefix: normalized, description: ''}
  const [prefix, ...rest] = normalized.split(DASH_RE)
  return {
    prefix: prefix.trim(),
    description: rest.join(' - ').trim(),
  }
}

function parseRegressionBaseline(label) {
  const {description} = splitDashLabel(label)
  return description || ''
}

export function fullJobTitle(job) {
  const metadata = job?.metadata || {}
  const label = cleanDisplayText(job?.label || '')
  const split = splitDashLabel(label)

  if (job?.execution_type === 'regression_sweep' || /^Regression Sweep/i.test(label)) {
    const focusLabel = metadata.focus ? ` [${metadata.focus}]` : ''
    const baseline = metadata.baseline_description || parseRegressionBaseline(label)
    return baseline ? `Regression Sweep${focusLabel} - ${baseline}` : label
  }

  if (metadata.persona_description) {
    const prefix = /^(AI Assert|Assert)\b/i.test(split.prefix) ? split.prefix : ''
    return prefix ? `${prefix} - ${metadata.persona_description}` : metadata.persona_description
  }

  return label
}

export function jobDisplayLabel(job, maxLength = 92) {
  const metadata = job?.metadata || {}
  const label = cleanDisplayText(job?.label || '')

  if (job?.execution_type === 'regression_sweep' || /^Regression Sweep/i.test(label)) {
    const focusLabel = metadata.focus ? ` [${metadata.focus}]` : ''
    const baseline = metadata.baseline_description || parseRegressionBaseline(label)
    const available = Math.max(34, maxLength - `Regression Sweep${focusLabel} - `.length)
    const summary = summarizePersonaDescription(baseline || label, available)
    return truncateDisplayText(`Regression Sweep${focusLabel} - ${summary}`, maxLength)
  }

  if (job?.execution_type === 'api_assert_flow' && metadata.persona_description) {
    const split = splitDashLabel(label)
    const prefix = /^Assert\b/i.test(split.prefix)
      ? split.prefix
      : `Assert ${metadata.assertion_type || 'assertion'} ${operatorText(metadata)} ${money(metadata.expected_value)}`.replace(/\s+/g, ' ').trim()
    return truncateDisplayText(
      `${prefix} - ${summarizePersonaDescription(metadata.persona_description, 56)}`,
      maxLength
    )
  }

  if (job?.execution_type === 'api_ai_assert' && metadata.persona_description) {
    return truncateDisplayText(
      `AI Assert - ${summarizePersonaDescription(metadata.persona_description, maxLength - 12)}`,
      maxLength
    )
  }

  if (DASH_RE.test(label)) {
    const {prefix, description} = splitDashLabel(label)
    if (/^(Assert|AI Assert)\b/i.test(prefix) && description) {
      return truncateDisplayText(`${prefix} - ${summarizePersonaDescription(description, maxLength - prefix.length - 3)}`, maxLength)
    }
  }

  return truncateDisplayText(label, maxLength)
}
