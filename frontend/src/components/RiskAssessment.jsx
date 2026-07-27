import React from 'react';

export default function RiskAssessment({ risk }) {
  if (!risk) {
    return (
      <div className="risk-card">
        <div style={{ fontSize: 13, color: '#999', textAlign: 'center', padding: 16 }}>
          Risk assessment will appear here after a complaint is logged.
        </div>
      </div>
    );
  }

  const severity = risk.severity || 'Unclassified';
  const confidence = risk.confidence != null ? (risk.confidence * 100).toFixed(0) : null;

  return (
    <div className="risk-card">
      <h4 style={{ fontSize: 12, textTransform: 'uppercase', color: '#666', marginBottom: 12, letterSpacing: 0.5 }}>
        AI Risk Assessment
      </h4>

      <div style={{ display: 'flex', gap: 12, marginBottom: 10 }}>
        <div>
          <div style={{ fontSize: 10, color: '#999', marginBottom: 2, textTransform: 'uppercase' }}>Severity</div>
          <span className={`risk-severity ${severity}`}>{severity}</span>
        </div>
        {confidence && (
          <div>
            <div style={{ fontSize: 10, color: '#999', marginBottom: 2, textTransform: 'uppercase' }}>Confidence</div>
            <span style={{ fontSize: 14, fontWeight: 600, color: '#555' }}>{confidence}%</span>
          </div>
        )}
      </div>

      <div style={{ marginBottom: 8 }}>
        <div style={{ fontSize: 10, color: '#999', marginBottom: 2, textTransform: 'uppercase' }}>Suggested Next Action</div>
        <div style={{ fontSize: 13, lineHeight: 1.5 }}>{risk.next_action}</div>
      </div>

      <div>
        <div style={{ fontSize: 10, color: '#999', marginBottom: 2, textTransform: 'uppercase' }}>Rationale</div>
        <div style={{ fontSize: 12, lineHeight: 1.5, color: '#555' }}>{risk.rationale}</div>
      </div>
    </div>
  );
}
