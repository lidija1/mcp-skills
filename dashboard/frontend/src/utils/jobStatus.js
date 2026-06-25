export function getDisplayStatus(job) {
    const text = `${job.label || ''} ${job.result || ''} ${job.error || ''}`.toLowerCase()
    const rawStatus = String(job.status || '').toLowerCase()
    const policyFlowType = getPolicyFlowType(job)

    const isCanceledStatus =
        rawStatus === 'canceled' ||
        rawStatus === 'cancelled'

    const isCanceledText =
        text.includes('canceled by user') ||
        text.includes('cancelled by user')

    const isFunctionalFailure =
        text.includes('policy creation failed') ||
        /\|\s*\*\*status\*\*\s*\|[^|\n]*\bfailed\b/i.test(text) ||
        /\|\s*\*\*outcome\*\*\s*\|[^|\n]*\berror\b/i.test(text)

    if (isCanceledStatus || isCanceledText) return 'canceled'
    if (rawStatus === 'running') return 'running'
    if (rawStatus === 'done' && policyFlowType && isFunctionalFailure) return 'failed'
    if (rawStatus === 'done') return 'done'

    if (rawStatus === 'error') return 'error'
    if (rawStatus === 'failed') return 'failed'
    if (isFunctionalFailure) return 'failed'

    return 'failed'
}

export function getJobStatusCounts(jobs = []) {
    return jobs.reduce(
        (counts, job) => {
            const displayStatus = getDisplayStatus(job)

            if (displayStatus === 'done') counts.completed += 1
            if (displayStatus === 'failed' || displayStatus === 'error') counts.failed += 1
            if (displayStatus === 'canceled') counts.canceled += 1
            if (displayStatus === 'running') counts.running += 1

            return counts
        },
        {
            completed: 0,
            failed: 0,
            canceled: 0,
            running: 0,
        }
    )
}

function getPolicyFlowType(job) {
    const executionType = String(job?.execution_type || '').toLowerCase()

    if (
        executionType === 'quick_run' ||
        executionType === 'policy_flow' ||
        executionType === 'create_persona'
    ) {
        return executionType
    }

    if (executionType === 'chat_execution') {
        const tool = String(job?.metadata?.tool || '').toLowerCase()
        if (tool === 'run_quick_policy') return 'quick_run'
        if (tool === 'create_persona') return 'create_persona'
    }

    const label = String(job?.label || '').toLowerCase()
    if (label.includes('quick policy')) return 'quick_run'
    if (label.includes('policy journey')) return 'policy_flow'
    if (label.includes('build profile')) return 'create_persona'

    return ''
}
