import React from 'react';

export default function MessageBubble({ message }) {
  const { role, text, isError, isUpload, risk_assessment, timestamp } = message;

  const roleClass = role === 'user' ? 'user' : 'assistant';
  const errorClass = isError ? 'is-error' : '';
  const uploadClass = isUpload ? 'message-upload' : '';

  const avatar = role === 'user' ? 'U' : 'AI';

  const formatTime = (ts) => {
    if (!ts) return '';
    try {
      return new Date(ts).toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return '';
    }
  };

  return (
    <div className={`message ${roleClass} ${errorClass} ${uploadClass}`}>
      <div className="message-avatar">{avatar}</div>
      <div>
        <div className="message-content">{text}</div>

        {risk_assessment && (
          <div className="risk-card" style={{ marginTop: 8 }}>
            <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 6 }}>
              <span className={`risk-severity ${risk_assessment.severity || 'Unclassified'}`}>
                {risk_assessment.severity || 'Unclassified'}
              </span>
              {risk_assessment.confidence != null && (
                <span style={{ fontSize: 11, color: '#666' }}>
                  {(risk_assessment.confidence * 100).toFixed(0)}% confidence
                </span>
              )}
            </div>
            <div style={{ fontSize: 12, lineHeight: 1.5 }}>
              <strong>Action:</strong> {risk_assessment.next_action}
            </div>
          </div>
        )}

        <div className="message-timestamp">{formatTime(timestamp)}</div>
      </div>
    </div>
  );
}
