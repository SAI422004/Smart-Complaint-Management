import React from 'react';

const NOT_SPECIFIED = 'Not specified';

export default function ComplaintForm({ complaint }) {
  const {
    displayId,
    dateReceived,
    complainant,
    productName,
    productStrength,
    batchNumber,
    manufacturingDate,
    expiryDate,
    affectedQuantityValue,
    affectedQuantityUnit,
    complaintCategory,
    complaintDescription,
    marketRegion,
    status,
    lastUpdatedFields,
  } = complaint;

  const isHighlight = (fieldName) =>
    lastUpdatedFields?.includes(fieldName) ? 'highlight' : '';

  const Field = ({ label, value, fieldName }) => (
    <div className="form-group">
      <label>{label}</label>
      <div className={`field-value ${value ? '' : 'empty'} ${isHighlight(fieldName)}`}>
        {value || NOT_SPECIFIED}
      </div>
    </div>
  );

  const quantityDisplay =
    affectedQuantityValue != null
      ? `${affectedQuantityValue} ${affectedQuantityUnit || ''}`.trim()
      : null;

  const formatDate = (d) => {
    if (!d) return null;
    try {
      return new Date(d).toLocaleDateString('en-GB', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
      });
    } catch {
      return d;
    }
  };

  return (
    <div className="complaint-form">
      {!displayId && (
        <div style={{ textAlign: 'center', padding: '40px 20px', color: '#999' }}>
          <p style={{ fontSize: 14, marginBottom: 8 }}>
            No complaint loaded yet.
          </p>
          <p style={{ fontSize: 12 }}>
            Use the AIVOA Copilot on the right to describe a complaint.
          </p>
        </div>
      )}

      {displayId && (
        <>
          <div className="form-row">
            <Field label="Complaint ID" value={displayId} fieldName="display_id" />
            <Field label="Date Received" value={formatDate(dateReceived)} fieldName="date_received" />
          </div>

          <div className="form-row">
            <Field label="Complainant / Reporting Party" value={complainant} fieldName="complainant" />
            <Field label="Market / Region" value={marketRegion} fieldName="market_region" />
          </div>

          <div className="form-row">
            <Field label="Product Name" value={productName} fieldName="product_name" />
            <Field label="Strength / Grade" value={productStrength} fieldName="product_strength" />
          </div>

          <div className="form-row">
            <Field label="Batch / Lot Number" value={batchNumber} fieldName="batch_number" />
            <Field label="Status" value={status} fieldName="status" />
          </div>

          <div className="form-row">
            <Field label="Manufacturing Date" value={formatDate(manufacturingDate)} fieldName="manufacturing_date" />
            <Field label="Expiry Date" value={formatDate(expiryDate)} fieldName="expiry_date" />
          </div>

          <div className="form-row">
            <Field label="Affected Quantity" value={quantityDisplay} fieldName="affected_quantity" />
            <Field label="Complaint Category" value={complaintCategory} fieldName="complaint_category" />
          </div>

          <div className="form-row">
            <div className="form-group full-width">
              <label>Complaint Description</label>
              <div className={`field-value ${complaintDescription ? '' : 'empty'} ${isHighlight('complaint_description')}`}>
                {complaintDescription || NOT_SPECIFIED}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
