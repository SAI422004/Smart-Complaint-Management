import React from 'react';
import { useSelector } from 'react-redux';
import ComplaintForm from './ComplaintForm';
import RiskAssessment from './RiskAssessment';

export default function LeftPanel() {
  const complaint = useSelector((state) => state.complaint);
  const isProcessing = useSelector((state) => state.chat.isProcessing);

  return (
    <div className="left-panel">
      <div className="panel-header">
        <h2>
          Log Customer Complaint
          {isProcessing && <span className="loading-dots"><span /><span /><span /></span>}
        </h2>
      </div>
      <div className="panel-content">
        <ComplaintForm complaint={complaint} />
        <RiskAssessment risk={complaint.riskAssessment} />
      </div>
    </div>
  );
}
