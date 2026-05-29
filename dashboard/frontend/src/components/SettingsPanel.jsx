import {Moon, Sun} from 'lucide-react'

const THEME_OPTIONS = [
    {
        value: 'light',
        label: 'Light',
        icon: Sun,
    },
    {
        value: 'dark',
        label: 'Dark',
        icon: Moon,
    },
]

export default function SettingsPanel({theme, onThemeChange}) {
    return (
        <section className="panel-stack settings-panel">
            <div className="page-heading">
                <h1>Settings</h1>
                <p>Control how the dashboard looks and behaves on this device.</p>
            </div>

            <div className="tool-card settings-card">
                <div className="settings-row">
                    <div className="settings-copy">
                        <h2>Appearance</h2>
                        <p>Choose the dashboard theme used across navigation, forms, reports, and modals.</p>
                    </div>

                    <div className="theme-toggle" role="radiogroup" aria-label="Dashboard theme">
                        {THEME_OPTIONS.map(option => {
                            const Icon = option.icon
                            const active = theme === option.value
                            return (
                                <button
                                    className={`theme-toggle-option ${active ? 'active' : ''}`}
                                    type="button"
                                    role="radio"
                                    aria-checked={active}
                                    key={option.value}
                                    onClick={() => onThemeChange(option.value)}
                                >
                                    <Icon size={17}/>
                                    <span>{option.label}</span>
                                </button>
                            )
                        })}
                    </div>
                </div>
            </div>
        </section>
    )
}
