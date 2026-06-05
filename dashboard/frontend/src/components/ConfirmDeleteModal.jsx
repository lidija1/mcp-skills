import {Trash2, X} from 'lucide-react'

export default function ConfirmDeleteModal({job, deleting = false, error = '', onCancel, onConfirm}) {
    if (!job) return null

    return (
        <div className="confirm-delete-backdrop" role="presentation" onClick={onCancel}>
            <section
                className="confirm-delete-dialog"
                role="dialog"
                aria-modal="true"
                aria-labelledby="confirm-delete-title"
                onClick={e => e.stopPropagation()}
            >
                <header className="confirm-delete-header">
                    <div className="confirm-delete-icon">
                        <Trash2 size={22}/>
                    </div>
                    <div>
                        <h2 id="confirm-delete-title">Delete job?</h2>
                        <p>This removes the job from your dashboard history.</p>
                    </div>
                    <button
                        className="modal-close-button"
                        type="button"
                        aria-label="Cancel delete"
                        title="Cancel"
                        onClick={onCancel}
                        disabled={deleting}
                    >
                        <X size={18}/>
                    </button>
                </header>

                <div className="confirm-delete-body">
                    <strong>{job.label || job.id}</strong>
                    <span>ID {job.id}</span>
                    {error && <p className="confirm-delete-error">{error}</p>}
                </div>

                <footer className="confirm-delete-actions">
                    <button className="text-button compact" type="button" onClick={onCancel} disabled={deleting}>
                        Cancel
                    </button>
                    <button
                        className="text-button compact danger confirm-delete-button"
                        type="button"
                        onClick={onConfirm}
                        disabled={deleting}
                    >
                        <Trash2 size={16}/>
                        {deleting ? 'Deleting...' : 'Delete'}
                    </button>
                </footer>
            </section>
        </div>
    )
}
