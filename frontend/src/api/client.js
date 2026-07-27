const API_BASE = '/api/complaint';

export async function fetchComplaints() {
  const res = await fetch('/api/complaints/');
  if (!res.ok) throw new Error('Failed to fetch complaints');
  return res.json();
}

export async function fetchComplaint(id) {
  const res = await fetch(`/api/complaints/${id}`);
  if (!res.ok) throw new Error('Complaint not found');
  return res.json();
}

export async function fetchSummary(complaintId) {
  const res = await fetch('/api/complaints/summary', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ complaint_id: complaintId }),
  });
  if (!res.ok) throw new Error('Failed to generate summary');
  return res.json();
}
