import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';

const API_BASE = '/api/complaint';

export const sendMessage = createAsyncThunk(
  'chat/sendMessage',
  async ({ message, complaintId }, { rejectWithValue }) => {
    try {
      const res = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message, complaint_id: complaintId }),
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to send message');
      }
      return await res.json();
    } catch (err) {
      return rejectWithValue(err.message);
    }
  }
);

export const uploadDocument = createAsyncThunk(
  'chat/uploadDocument',
  async (file, { rejectWithValue }) => {
    try {
      const formData = new FormData();
      formData.append('file', file);
      const res = await fetch(`${API_BASE}/upload`, {
        method: 'POST',
        body: formData,
      });
      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to upload document');
      }
      return await res.json();
    } catch (err) {
      return rejectWithValue(err.message);
    }
  }
);

const chatSlice = createSlice({
  name: 'chat',
  initialState: {
    messages: [],
    isProcessing: false,
    error: null,
    uploadedDocument: null,
  },
  reducers: {
    clearError(state) {
      state.error = null;
    },
    clearChat(state) {
      state.messages = [];
      state.uploadedDocument = null;
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      .addCase(sendMessage.pending, (state) => {
        state.isProcessing = true;
        state.error = null;
      })
      .addCase(sendMessage.fulfilled, (state, action) => {
        state.isProcessing = false;
        const { reply, complaint, risk_assessment, updated_fields } = action.payload;
        // Add user message
        state.messages.push({
          role: 'user',
          text: action.meta.arg.message,
          timestamp: new Date().toISOString(),
        });
        // Add assistant reply
        state.messages.push({
          role: 'assistant',
          text: reply,
          complaint,
          risk_assessment,
          updated_fields,
          timestamp: new Date().toISOString(),
        });
      })
      .addCase(sendMessage.rejected, (state, action) => {
        state.isProcessing = false;
        state.error = action.payload || 'Request failed';
        state.messages.push({
          role: 'assistant',
          text: `Error: ${action.payload || 'Request failed. Please try again.'}`,
          isError: true,
          timestamp: new Date().toISOString(),
        });
      })
      .addCase(uploadDocument.pending, (state) => {
        state.isProcessing = true;
        state.error = null;
      })
      .addCase(uploadDocument.fulfilled, (state, action) => {
        state.isProcessing = false;
        state.uploadedDocument = action.payload.filename;
        state.messages.push({
          role: 'user',
          text: `[Uploaded document: ${action.payload.filename}]`,
          isUpload: true,
          timestamp: new Date().toISOString(),
        });
        state.messages.push({
          role: 'assistant',
          text: action.payload.extracted_text
            ? `Document processed. Extracted text available. Complaint data populated from the document.`
            : 'Document uploaded but no text could be extracted.',
          complaint: action.payload.complaint,
          timestamp: new Date().toISOString(),
        });
      })
      .addCase(uploadDocument.rejected, (state, action) => {
        state.isProcessing = false;
        state.error = action.payload || 'Upload failed';
        state.messages.push({
          role: 'assistant',
          text: `Upload Error: ${action.payload || 'Failed to upload document.'}`,
          isError: true,
          timestamp: new Date().toISOString(),
        });
      });
  },
});

export const { clearError, clearChat } = chatSlice.actions;
export default chatSlice.reducer;
