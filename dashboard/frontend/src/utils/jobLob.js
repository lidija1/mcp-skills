/** Canonical dashboard LOB keys → Jobs page group labels */
export const JOB_LOB_DISPLAY = {
  'personal-auto': 'Personal Auto',
  auto: 'Personal Auto',
  cyber: 'Cyber',
  homeowner: 'Homeowner',
  multi: 'Multi-LOB',
  all: 'All LOBs',
}

export const JOB_LOB_GROUP_ORDER = [
  'Personal Auto',
  'Homeowner',
  'Cyber',
  'Multi-LOB',
  'All LOBs',
  'General',
]

/**
 * Resolve the LOB group label for a job. Prefer server metadata; never scan result bodies.
 */
export function resolveJobLobDisplay(job) {
  const meta = job?.metadata || {}

  if (meta.lob_display && typeof meta.lob_display === 'string') {
    return meta.lob_display.trim()
  }

  if (meta.lob) {
    const key = String(meta.lob).toLowerCase().trim()
    if (JOB_LOB_DISPLAY[key]) return JOB_LOB_DISPLAY[key]
  }

  const paramLob = meta.params?.lob
  if (paramLob) {
    const key = String(paramLob).toLowerCase().trim()
    const normalized = key === 'auto' ? 'personal-auto' : key
    if (JOB_LOB_DISPLAY[normalized]) return JOB_LOB_DISPLAY[normalized]
  }

  return inferLobFromLabel(job?.label)
}

function inferLobFromLabel(label) {
  const text = String(label || '').toLowerCase()
  if (text.includes('all lob')) return 'All LOBs'
  if (text.includes('batch test')) return 'Multi-LOB'
  if (text.includes('homeowner')) return 'Homeowner'
  if (text.includes('cyber')) return 'Cyber'
  if (
    text.includes('personal auto') ||
    text.includes('personal-auto') ||
    /\bauto\b/.test(text)
  ) {
    return 'Personal Auto'
  }
  return 'General'
}

export function sortLobGroupKeys(lobKeys) {
  return [...lobKeys].sort((a, b) => {
    const ia = JOB_LOB_GROUP_ORDER.indexOf(a)
    const ib = JOB_LOB_GROUP_ORDER.indexOf(b)
    const rankA = ia === -1 ? JOB_LOB_GROUP_ORDER.length : ia
    const rankB = ib === -1 ? JOB_LOB_GROUP_ORDER.length : ib
    if (rankA !== rankB) return rankA - rankB
    return a.localeCompare(b)
  })
}

/** Build metadata for optimistic job placeholders from a policy-flow LOB id */
export function metadataForPolicyLob(lobId) {
  const key = lobId === 'auto' ? 'personal-auto' : lobId
  return {
    lob: key,
    lob_display: JOB_LOB_DISPLAY[key] || 'General',
  }
}

/** Build metadata for UW panel (engine id "auto" → personal-auto) */
export function metadataForUwLob(lobId) {
  const key = lobId === 'auto' ? 'personal-auto' : lobId
  return {
    lob: key,
    lob_display: JOB_LOB_DISPLAY[key] || JOB_LOB_DISPLAY[lobId] || 'General',
  }
}
