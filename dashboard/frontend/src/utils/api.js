const getAuthHeaders = () => {
  const token = localStorage.getItem('access_token')

  return token
    ? {
        Authorization: `Bearer ${token}`,
      }
    : {}
}

const post = async (url, body) => {
  const response = await fetch(url, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...getAuthHeaders(),
    },
    body: JSON.stringify(body),
  })

  const data = await response.json()

  if (!response.ok) {
    throw new Error(data.detail || data.error || 'Request failed')
  }

  return data
}

const get = async url => {
  const response = await fetch(url, {
    credentials: 'include',
    headers: getAuthHeaders(),
  })

  const data = await response.json()

  if (!response.ok) {
    throw new Error(data.detail || data.error || 'Request failed')
  }

  return data
}

const del = async url => {
  const response = await fetch(url, {
    method: 'DELETE',
    credentials: 'include',
    headers: getAuthHeaders(),
  })

  const data = await response.json()

  if (!response.ok) {
    throw new Error(data.detail || data.error || 'Request failed')
  }

  return data
}

const policyLobForApi = lob => {
  const value = String(lob || '').toLowerCase().trim()
  if (value === 'personal-auto' || value === 'personal_auto' || value === 'personal auto') {
    return 'auto'
  }
  return value
}

export const api = {
  // ── Health ────────────────────────────────────────────────────────────
  health: () => get('/api/health'),

  // ── Jobs ──────────────────────────────────────────────────────────────
  listJobs: () => get('/api/jobs'),
  getJob: id => get(`/api/jobs/${id}`),
  cancelJob: id => post(`/api/jobs/${id}/cancel`, {}),
  rerunJob: id => post(`/api/jobs/${id}/rerun`, {}),
  deleteJob: id => del(`/api/jobs/${id}`),
  explorerPrompt: prompt => post('/api/explorer/prompt', { prompt }),
  explorerRun: prompt => post('/api/explorer/run', { prompt }),

  // ── Policy ────────────────────────────────────────────────────────────
  getArchetypes: (lob = '') => get(`/api/policy/archetypes?lob=${policyLobForApi(lob)}`),
  createPersona: (lob, description) => post('/api/policy/create-persona', { lob: policyLobForApi(lob), description }),
  runFlow: (lob, persona_json) => post('/api/policy/run-flow', { lob: policyLobForApi(lob), persona_json }),
  quickRun: (lob, description) => post('/api/policy/quick-run', { lob: policyLobForApi(lob), description }),
  batchRun: scenarios => post('/api/policy/batch-run', { scenarios }),
  runApiPlainAssertion: prompt => post('/api/api-tests/plain-assert', { prompt }),
runCompare: (description_a, description_b, relations, label_a = '', label_b = '') =>
    post('/api/api-tests/compare', { description_a, description_b, relations, label_a, label_b }),
  runLadder: (base_description, dimension, assert_monotonic = true) =>
    post('/api/api-tests/ladder', { base_description, dimension, assert_monotonic }),
  runAiAssert: persona_description => post('/api/api-tests/ai-assert', { persona_description }),
  runAssertFlow: (persona_description, assertion_type, expected_value, operator, tolerance_pct) =>
    post('/api/api-tests/assert-flow', { persona_description, assertion_type, expected_value, operator, tolerance_pct }),
  runRegressionSweep: (baseline_description, lob = 'auto', focus = null) =>
    post('/api/api-tests/regression-sweep', { baseline_description, lob, focus }),
  getSnapshot: run_id => get(`/api/api-tests/snapshot/${run_id}`),
  getAssertionHistory: () => get('/api/api-tests/results'),
  deleteAssertionResult: id => del(`/api/api-tests/results/${id}`),
  explainAssertFlow: data => post('/api/api-tests/explain', {
    persona_description: data.persona_description,
    lob: data.lob,
    coverage_premiums: data.coverage_premiums,
    uw_conditions: data.uw_conditions,
    actual_value: data.actual_value,
    expected_value: data.expected_value,
    assertion_type: data.assertion_type,
    operator: data.operator,
    tolerance_pct: data.tolerance_pct,
    passed: data.passed,
  }),

  // ── UW ────────────────────────────────────────────────────────────────
  listRules: (lob = '') => get(`/api/uw/rules?lob=${lob}`),
  runAudit: lob => post('/api/uw/audit', { lob }),
  runRuleCases: (lob, rule_id) => post('/api/uw/rule-cases', { lob, rule_id }),
  runCustomBoundary: (lob, description, expected_outcome, expected_conditions) =>
    post('/api/uw/custom-boundary', { lob, description, expected_outcome, expected_conditions }),
  runFullAudit: () => post('/api/uw/full-audit', {}),

  // ── Chat ──────────────────────────────────────────────────────────────
  chatGreeting: () => get('/api/chat/greeting'),
  chat: (message, confirmedTool = null, confirmedParams = null, history = []) =>
    post('/api/chat/message', {
      message,
      confirmed_tool: confirmedTool,
      confirmed_params: confirmedParams,
      history,
    }),
  chatAsk: (message, history = []) => post('/api/chat/ask', { message, history }),
  chatAskStream: (message, history = [], maxTokens = 1200) =>
    fetch('/api/chat/ask/stream', {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json', ...getAuthHeaders() },
      body: JSON.stringify({ message, history, max_tokens: maxTokens }),
    }),

  // ── Auth ──────────────────────────────────────────────────────────────
login: (username, password) =>
  post('/api/login', {
    username,
    password,
  }),

register: (first_name, last_name, username, password) =>
  post('/api/register', {
    first_name,
    last_name,
    username,
    password,
  }),

me: () => get('/api/auth/me'),

logout: () => post('/api/auth/logout', {}),
}
