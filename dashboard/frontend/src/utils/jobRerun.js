/** Infer policy execution kind from type, tool name, or job label. */
export function inferExecutionType(job) {
  const explicit = job?.execution_type
  if (explicit === 'quick_run' || explicit === 'policy_flow' || explicit === 'create_persona') return explicit
  if (isAssertExecutionType(explicit)) return explicit

  if (explicit === 'chat_execution') {
    const tool = job?.metadata?.tool
    if (tool === 'run_quick_policy') return 'quick_run'
    if (tool === 'create_persona') return 'create_persona'
  }

  const label = (job?.label || '').toLowerCase()
  if (label.includes('quick policy')) return 'quick_run'
  if (label.includes('policy journey')) return 'policy_flow'
  if (label.includes('build profile')) return 'create_persona'

  return explicit || ''
}

const ASSERT_EXECUTION_TYPES = new Set([
  'api_assertion',
  'api_compare',
  'api_ladder',
  'api_ai_assert',
  'api_assert_flow',
])

function isAssertExecutionType(type) {
  return ASSERT_EXECUTION_TYPES.has(type)
}

function extractSourceDescription(result) {
  if (!result || typeof result !== 'string') return ''
  const match = result.match(/\*\*Source Description:\*\*\s*(.+?)(?:\n\n|\n```|$)/is)
  return match?.[1]?.trim() || ''
}

function quickRunDescription(job) {
  const metadata = job?.metadata || {}
  const payload = metadata.rerun_payload || {}
  const params = metadata.params || {}

  return (
    payload.description ||
    metadata.description ||
    params.description ||
    extractSourceDescription(job?.result)
  )
}

function policyFlowPersona(job) {
  const metadata = job?.metadata || {}
  const payload = metadata.rerun_payload || {}
  const params = metadata.params || {}

  const persona = payload.persona_json ?? metadata.persona_json ?? params.persona_json
  if (persona == null || persona === '') return null
  return persona
}

function personaDescription(job) {
  const metadata = job?.metadata || {}
  const params = metadata.params || {}

  return (
    metadata.description ||
    params.description ||
    extractSourceDescription(job?.result)
  )
}

function markdownField(content, label) {
  if (!content || typeof content !== 'string') return ''
  const match = content.match(new RegExp(`\\*\\*${label}:\\*\\*\\s*(.+)`))
  return match?.[1]?.trim() || ''
}

function ladderBaseDescription(result) {
  if (!result || typeof result !== 'string') return ''
  const match = result.match(/^Base:\s*_(.+?)_\s*$/m)
  return match?.[1]?.trim() || ''
}

function assertFlowPayloadFromResult(result) {
  if (!result || typeof result !== 'string' || !result.trimStart().startsWith('{')) return null
  try {
    const data = JSON.parse(result)
    if (data?._type !== 'assert_flow') return null
    return data
  } catch {
    return null
  }
}

function canRerunAssertJob(job) {
  const metadata = job?.metadata || {}
  const payload = metadata.rerun_payload || {}
  const type = inferExecutionType(job)

  if (Object.keys(payload).length > 0) return true
  if (type === 'api_assertion') return Boolean(metadata.prompt)
  if (type === 'api_ai_assert') return Boolean(metadata.persona_description || markdownField(job?.result, 'Persona'))
  if (type === 'api_ladder') return Boolean((metadata.base_description || ladderBaseDescription(job?.result)) && metadata.dimension)
  if (type === 'api_assert_flow') return Boolean(assertFlowPayloadFromResult(job?.result))

  return false
}

/** Whether the backend /api/jobs/:id/rerun endpoint can handle this job. */
export function canRerunJob(job) {
  if (!job) return false

  const type = inferExecutionType(job)
  if (type === 'quick_run') return Boolean(quickRunDescription(job))
  if (type === 'policy_flow') return policyFlowPersona(job) != null
  if (type === 'create_persona') return Boolean(personaDescription(job))
  if (isAssertExecutionType(type)) return canRerunAssertJob(job)

  return false
}

function isPolicyAutomationLabel(job) {
  const label = (job?.label || '').toLowerCase()
  return (
    label.includes('quick policy') ||
    label.includes('policy journey') ||
    label.includes('policy test') ||
    label.includes('personal auto') ||
    label.includes('personal-auto')
  )
}

function hasPolicyLob(job) {
  const metadata = job?.metadata || {}
  const candidates = [
    metadata.lob,
    metadata.requested_lob,
    metadata.params?.lob,
    metadata.rerun_payload?.lob,
  ]

  return candidates.some(value => {
    const lob = String(value || '').toLowerCase().trim()
    return (
      lob === 'homeowner' ||
      lob === 'personal-auto' ||
      lob === 'personal auto' ||
      lob === 'auto'
    )
  })
}

/** Show Run again in the UI for canceled policy automation jobs. */
export function shouldShowRerunAction(job) {
  if (!job || job.status !== 'canceled') return false
  if (canRerunJob(job)) return true
  return isPolicyAutomationLabel(job) || hasPolicyLob(job)
}
