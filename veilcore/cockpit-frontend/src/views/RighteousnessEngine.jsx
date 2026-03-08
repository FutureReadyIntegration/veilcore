export default function RighteousnessEngine({ stats, decisions }) {
  return (
    <div className="righteousness-engine">
      <h2>Righteousness Engine – Ethical Evaluation</h2>

      <div className="score-grid">
        <div className="score-item">❤️ DIVINE — {stats.divine}</div>
        <div className="score-item">🛡️ RIGHTEOUS — {stats.righteous}</div>
        <div className="score-item">🔑 NEUTRAL — {stats.neutral}</div>
        <div className="score-item">⚠️ QUESTIONABLE — {stats.questionable}</div>
        <div className="score-item">💀 BLOCKED — {stats.blocked}</div>
      </div>

      <h3>Recent Ethical Decisions</h3>

      <div className="decision-list">
        {decisions.map((d, i) => (
          <div key={i} className="decision-item">
            <div className="decision-icon">
              {d.icon === "divine" && "❤️"}
              {d.icon === "righteous" && "🛡️"}
              {d.icon === "neutral" && "🔑"}
              {d.icon === "questionable" && "⚠️"}
              {d.icon === "blocked" && "💀"}
              {d.icon === "scale" && "⚖️"}
            </div>

            <div className="decision-body">
              <div className="decision-title">“{d.message}”</div>
              <div className="decision-meta">
                {d.actor} → {d.target}
              </div>
            </div>

            <div className={`decision-status status-${d.status.toLowerCase()}`}>
              {d.status}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
