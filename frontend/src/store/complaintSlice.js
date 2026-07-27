import { createSlice } from '@reduxjs/toolkit';

const initialState = {
  complaintId: null,
  displayId: null,
  dateReceived: null,
  complainant: null,
  productName: null,
  productStrength: null,
  batchNumber: null,
  manufacturingDate: null,
  expiryDate: null,
  affectedQuantityValue: null,
  affectedQuantityUnit: null,
  complaintCategory: null,
  complaintDescription: null,
  marketRegion: null,
  status: null,
  // Risk assessment
  riskAssessment: null,
  // UI state
  lastUpdatedFields: [],
};

const complaintSlice = createSlice({
  name: 'complaint',
  initialState,
  reducers: {
    setComplaint(state, action) {
      const data = action.payload;
      if (!data) return;
      state.complaintId = data.complaint_id ?? state.complaintId;
      state.displayId = data.display_id ?? state.displayId;
      state.dateReceived = data.date_received ?? state.dateReceived;
      state.complainant = data.complainant ?? state.complainant;
      state.productName = data.product_name ?? state.productName;
      state.productStrength = data.product_strength ?? state.productStrength;
      state.batchNumber = data.batch_number ?? state.batchNumber;
      state.manufacturingDate = data.manufacturing_date ?? state.manufacturingDate;
      state.expiryDate = data.expiry_date ?? state.expiryDate;
      state.affectedQuantityValue = data.affected_quantity_value ?? state.affectedQuantityValue;
      state.affectedQuantityUnit = data.affected_quantity_unit ?? state.affectedQuantityUnit;
      state.complaintCategory = data.complaint_category ?? state.complaintCategory;
      state.complaintDescription = data.complaint_description ?? state.complaintDescription;
      state.marketRegion = data.market_region ?? state.marketRegion;
      state.status = data.status ?? state.status;
    },
    setRiskAssessment(state, action) {
      state.riskAssessment = action.payload;
    },
    setUpdatedFields(state, action) {
      state.lastUpdatedFields = action.payload || [];
    },
    clearComplaint(state) {
      Object.assign(state, initialState);
    },
  },
});

export const { setComplaint, setRiskAssessment, setUpdatedFields, clearComplaint } = complaintSlice.actions;
export default complaintSlice.reducer;
