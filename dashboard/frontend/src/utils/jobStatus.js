export function getDisplayStatus(job) {
    const text = `${job.label || ''} ${job.result || ''} ${job.error || ''}`.toLowerCase()

    const isTechnicalError = job.status === 'error'

    const isFunctionalFailure =
        text.includes('policy creation failed') ||
        text.includes('| **status** | failed') ||
        text.includes('| **outcome** | error')

    if (job.status === 'canceled') return 'canceled'
    if (job.status === 'running') return 'running'

    if (isTechnicalError) return 'error'
    if (isFunctionalFailure) return 'failed'

    if (job.status === 'done') return 'done'

    return 'failed'
}