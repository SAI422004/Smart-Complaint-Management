import React, { useEffect } from 'react';
import { useSelector, useDispatch } from 'react-redux';
import { clearError } from './store/chatSlice';
import LeftPanel from './components/LeftPanel';
import RightPanel from './components/RightPanel';
import './App.css';

export default function App() {
  const dispatch = useDispatch();
  const error = useSelector((state) => state.chat.error);

  useEffect(() => {
    if (error) {
      const timer = setTimeout(() => dispatch(clearError()), 5000);
      return () => clearTimeout(timer);
    }
  }, [error, dispatch]);

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="header-left">
          <h1>AIVOA Copilot</h1>
          <span className="header-subtitle">AI-Powered Complaint Management System</span>
        </div>
        <div className="header-right">
          <span className="badge badge-pharma">Pharma QMS</span>
        </div>
      </header>
      {error && <div className="error-banner">{error}</div>}
      <div className="app-main">
        <LeftPanel />
        <RightPanel />
      </div>
    </div>
  );
}
