import { useState, useEffect } from 'react'
import './App.css'

const ORGAN_ICONS = {
  // Clinical
  epic: '🏥', imprivata: '🔐', hl7: '📋', fhir: '🔥', hospital: '🏨',
  // Security
  guardian: '🛡️', sentinel: '👁️', firewall: '🧱', quarantine: '🔒', vault: '🔐',
  auth: '🔑', mfa: '🔑', rbac: '👥', dlp: '🛡️', canary: '🐤', forensic: '🔬',
  // Core
  cortex: '🧠', bios: '⚡', init: '🚀', engine: '⚙️', daemon: '👻',
  // Data
  backup: '💾', ledger: '📒', journal: '📓', audit: '📝', logger: '📋',
  // Network
  gateway: '🌐', router: '🔀', bridge: '🌉', relay: '📡', socket: '🔌',
  // Recovery
  rollback: '⏪', restore: '♻️', snapshot: '📸',
  // Monitoring
  telemetry: '📊', metrics: '📈', monitor: '🖥️', watchdog: '🐕', health: '❤️',
  // Default
  default: '⚙️'
}

function getOrganIcon(name) {
  return ORGAN_ICONS[name] || ORGAN_ICONS.default
}

// Mock data - replace with real API calls
const mockOrgans = [
  { name: 'epic', status: 'active', tier: 'clinical' },
  { name: 'imprivata', status: 'active', tier: 'clinical' },
  { name: 'guardian', status: 'active', tier: 'security' },
  { name: 'cortex', status: 'active', tier: 'core' },
  { name: 'vault', status: 'active', tier: 'security' },
  { name: 'backup', status: 'active', tier: 'recovery' },
  { name: 'quarantine', status: 'active', tier: 'security' },
  { name: 'sentinel', status: 'active', tier: 'security' },
  { name: 'audit', status: 'active', tier: 'compliance' },
  { name: 'firewall', status: 'active', tier: 'network' },
  { name: 'gateway', status: 'active', tier: 'network' },
  { name: 'telemetry', status: 'active', tier: 'monitoring' },
]

const mockLedger = [
  { organ: 'epic', action: 'activated', tier: 'clinical', time: '04:23' },
  { organ: 'imprivata', action: 'activated', tier: 'clinical', time: '03:30' },
  { organ: 'guardian', action: 'activated', tier: 'security', time: '02:05' },
  { organ: 'backup', action: 'snapshot', tier: 'recovery', time: '01:10' },
  { organ: 'audit', action: 'verified', tier: 'compliance', time: '00:45' },
]

const mockEvents = [
  { time: '04:23', text: 'Epic connector initialized' },
  { time: '03:30', text: 'Imprivata SSO bridge active' },
  { time: '02:05', text: 'Guardian scan completed' },
  { time: '01:10', text: 'Backup snapshot created' },
  { time: '00:45', text: 'Ledger integrity verified' },
]

function OrganCard({ organ }) {
  return (
    <div className={`organ-card ${organ.status}`}>
      <div className="organ-icon">{getOrganIcon(organ.name)}</div>
      <div className="organ-name">{organ.name}</div>
      <div className="organ-meta">
        <span className={`organ-badge badge-${organ.status}`}>
          {organ.status}
        </span>
        <span className="organ-badge badge-tier">{organ.tier}</span>
      </div>
    </div>
  )
}

function LedgerItem({ entry }) {
  return (
    <div className="ledger-item">
      <div className="ledger-avatar">{getOrganIcon(entry.organ)}</div>
      <div className="ledger-info">
        <div className="ledger-name">{entry.organ}</div>
        <div className="ledger-meta">
          <span className={`organ-badge badge-active`}>{entry.action}</span>
          <span className="organ-badge badge-tier">{entry.tier}</span>
        </div>
      </div>
    </div>
  )
}

function EventItem({ event }) {
  return (
    <div className="event-item">
      <span className="event-time">{event.time}</span>
      <span className="event-text">{event.text}</span>
    </div>
  )
}

export default function App() {
  const [theme, setTheme] = useState(localStorage.getItem('theme') || 'light')
  const [filter, setFilter] = useState('all')
  const [search, setSearch] = useState('')
  const [organs, setOrgans] = useState(mockOrgans)
  const [ledger, setLedger] = useState(mockLedger)
  const [events, setEvents] = useState(mockEvents)

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem('theme', theme)
  }, [theme])

  // Fetch real data from API
  useEffect(() => {
    fetch('/api/organs')
      .then(res => res.json())
      .then(data => {
        if (data && data.length) setOrgans(data)
      })
      .catch(() => {})
    
    fetch('/api/ledger')
      .then(res => res.json())
      .then(data => {
        if (data && data.length) setLedger(data.slice(-10).reverse())
      })
      .catch(() => {})
  }, [])

  const filteredOrgans = organs.filter(o => {
    if (filter !== 'all' && o.tier !== filter) return false
    if (search && !o.name.toLowerCase().includes(search.toLowerCase())) return false
    return true
  })

  const tiers = [...new Set(organs.map(o => o.tier))]
  const activeCount = organs.filter(o => o.status === 'active').length

  return (
    <div className="app-shell">
      <header className="app-header">
        <div>
          <div className="app-title">Veil OS Cockpit</div>
          <div className="app-subtitle">Hospital Security Operations</div>
        </div>
        <div className="header-actions">
          <div className="theme-toggle">
            <button 
              className={theme === 'light' ? 'active' : ''} 
              onClick={() => setTheme('light')}
            >
              ☀️ Clinical
            </button>
            <button 
              className={theme === 'dark' ? 'active' : ''} 
              onClick={() => setTheme('dark')}
            >
              🌙 Cyber
            </button>
          </div>
        </div>
      </header>

      <main className="app-main">
        <section className="card card-ledger">
          <div className="card-header">
            <div className="card-title">Ledger</div>
          </div>
          <div className="card-body">
            <div className="ledger-list">
              {ledger.map((entry, i) => (
                <LedgerItem key={i} entry={entry} />
              ))}
            </div>
          </div>
        </section>

        <section className="card card-organs">
          <div className="card-header">
            <div className="card-title">Organs</div>
            <div className="card-actions">
              <input
                type="text"
                className="search-input"
                placeholder="Search organs..."
                value={search}
                onChange={e => setSearch(e.target.value)}
                style={{ width: '150px' }}
              />
            </div>
          </div>
          <div className="card-body">
            <div className="stats-bar">
              <div className="stat-item">
                <span className="stat-value">{organs.length}</span>
                <span className="stat-label">Total</span>
              </div>
              <div className="stat-item">
                <span className="stat-value" style={{ color: 'var(--status-active)' }}>{activeCount}</span>
                <span className="stat-label">Active</span>
              </div>
              <div className="stat-item">
                <span className="stat-value">{tiers.length}</span>
                <span className="stat-label">Tiers</span>
              </div>
            </div>
            
            <div className="filter-pills">
              <button 
                className={`filter-pill ${filter === 'all' ? 'active' : ''}`}
                onClick={() => setFilter('all')}
              >
                All
              </button>
              {tiers.map(tier => (
                <button
                  key={tier}
                  className={`filter-pill ${filter === tier ? 'active' : ''}`}
                  onClick={() => setFilter(tier)}
                >
                  {tier}
                </button>
              ))}
            </div>

            <div className="organ-grid">
              {filteredOrgans.map(organ => (
                <OrganCard key={organ.name} organ={organ} />
              ))}
            </div>
          </div>
        </section>

        <section className="card card-events">
          <div className="card-header">
            <div className="card-title">Events</div>
          </div>
          <div className="card-body">
            <div className="events-list" style={{ display: 'flex', flexDirection: 'row', gap: '2rem', flexWrap: 'wrap' }}>
              {events.map((event, i) => (
                <EventItem key={i} event={event} />
              ))}
            </div>
          </div>
        </section>
      </main>
    </div>
  )
}
