import React, { useState, useRef, useEffect, useCallback } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { sendMessage, uploadDocument } from '../store/chatSlice';
import { setComplaint, setRiskAssessment, setUpdatedFields } from '../store/complaintSlice';
import MessageBubble from './MessageBubble';

export default function CopilotChat({ messages, isProcessing }) {
  const [input, setInput] = useState('');
  const dispatch = useDispatch();
  const complaintId = useSelector((state) => state.complaint.complaintId);
  const chatEndRef = useRef(null);
  const fileInputRef = useRef(null);

  const scrollToBottom = useCallback(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  const handleSend = async () => {
    const msg = input.trim();
    if (!msg || isProcessing) return;
    setInput('');

    const result = await dispatch(sendMessage({ message: msg, complaintId }));
    if (sendMessage.fulfilled.match(result)) {
      const payload = result.payload;
      if (payload.complaint) {
        dispatch(setComplaint(payload.complaint));
      }
      if (payload.risk_assessment) {
        dispatch(setRiskAssessment(payload.risk_assessment));
      }
      if (payload.updated_fields) {
        dispatch(setUpdatedFields(payload.updated_fields));
      }
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const result = await dispatch(uploadDocument(file));
    if (uploadDocument.fulfilled.match(result)) {
      const payload = result.payload;
      if (payload.complaint) {
        dispatch(setComplaint(payload.complaint));
      }
      if (payload.risk_assessment) {
        dispatch(setRiskAssessment(payload.risk_assessment));
      }
    }
    // Reset file input so the same file can be re-uploaded
    if (fileInputRef.current) fileInputRef.current.value = '';
  };

  const handleSummary = async () => {
    if (!complaintId) return;
    await dispatch(sendMessage({
      message: 'summarize this complaint',
      complaintId,
    }));
  };

  return (
    <div className="chat-container">
      <div className="chat-messages">
        {messages.length === 0 && (
          <div style={{ textAlign: 'center', padding: '40px 20px', color: '#999' }}>
            <p style={{ fontSize: 14, marginBottom: 8 }}>How can I help you?</p>
            <p style={{ fontSize: 12 }}>
              Describe a complaint, upload a document, or ask me to summarize an existing record.
            </p>
          </div>
        )}
        {messages.map((msg, i) => (
          <MessageBubble key={i} message={msg} />
        ))}
        <div ref={chatEndRef} />
      </div>

      <div className="chat-input-area">
        {complaintId && (
          <div style={{ marginBottom: 8 }}>
            <button
              className="btn btn-secondary"
              onClick={handleSummary}
              disabled={isProcessing}
              style={{ fontSize: 12 }}
            >
              Generate Summary
            </button>
            <span style={{ fontSize: 11, color: '#999', marginLeft: 8 }}>
              Active: {complaintId}
            </span>
          </div>
        )}

        <div className="chat-input-row">
          <textarea
            className="chat-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Describe the complaint or provide additional details..."
            rows={1}
            disabled={isProcessing}
          />
          <div className="upload-btn-wrapper">
            <button className="btn btn-secondary" disabled={isProcessing}>
              Upload
            </button>
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileUpload}
              accept=".pdf,.docx,.txt,.eml"
              disabled={isProcessing}
            />
          </div>
          <button
            className="btn btn-primary"
            onClick={handleSend}
            disabled={!input.trim() || isProcessing}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
