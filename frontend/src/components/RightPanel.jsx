import React from 'react';
import { useSelector } from 'react-redux';
import CopilotChat from './CopilotChat';

export default function RightPanel() {
  const messages = useSelector((state) => state.chat.messages);
  const isProcessing = useSelector((state) => state.chat.isProcessing);

  return (
    <div className="right-panel">
      <div className="panel-header">
        <h2>
          AIVOA Copilot
          {isProcessing && <span className="loading-dots"><span /><span /><span /></span>}
        </h2>
      </div>
      <CopilotChat messages={messages} isProcessing={isProcessing} />
    </div>
  );
}
