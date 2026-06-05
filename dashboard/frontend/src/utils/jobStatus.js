export function getDisplayStatus(job) {
    const text = `${job.label || ''} ${job.result || ''} ${job.error || ''}`.toLowerCase()
    const rawStatus = String(job.status || '').toLowerCase()

    const isCanceled =
        rawStatus === 'canceled' ||
        rawStatus === 'cancelled' ||
        text.includes('canceled by user') ||
        text.includes('cancelled by user')

    const isTechnicalError = rawStatus === 'error'

    const isFunctionalFailure =
        text.includes('policy creation failed') ||
        text.includes('| **status** | failed') ||
        text.includes('| **outcome** | error')

    if (isCanceled) return 'canceled'
    if (rawStatus === 'running') return 'running'

    if (isTechnicalError) return 'error'
    if (isFunctionalFailure) return 'failed'

    if (rawStatus === 'done') return 'done'

    return 'failed'
}
