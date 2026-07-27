"""
Quick API smoke tests to verify the system works end-to-end.

Prerequisites:
  - Backend running on http://localhost:8000
  - Database seeded (python seed_data.py)

Usage: python tests/test_api.py
"""

import json
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    import httpx
except ImportError:
    print("httpx not installed. Run: pip install httpx")
    sys.exit(1)

BASE = "http://localhost:8000"


def test_health():
    r = httpx.get(f"{BASE}/health")
    assert r.status_code == 200, f"Health check failed: {r.text}"
    print("  [PASS] Health check")


def test_list_complaints():
    r = httpx.get(f"{BASE}/api/complaints/")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    print(f"  [PASS] List complaints: {len(data)} complaint(s)")


def test_chat_new():
    """Tool 1: Log a new complaint via chat."""
    payload = {
        "message": "Apollo Pharmacy reported discolored capsules in Amoxicillin Capsules 500mg."
    }
    r = httpx.post(f"{BASE}/api/complaint/chat", json=payload)
    assert r.status_code == 200, f"Chat failed: {r.text}"
    data = r.json()
    assert "reply" in data
    assert data.get("complaint") is not None, "No complaint created"
    print(f"  [PASS] Chat (new): Created {data['complaint']['display_id']}")
    return data["complaint"]["complaint_id"]


def test_chat_edit(complaint_id):
    """Tool 2: Edit an existing complaint via follow-up chat."""
    payload = {
        "message": "Sorry, the batch number is BMX240602, and the affected quantity is 48 capsules.",
        "complaint_id": complaint_id,
    }
    r = httpx.post(f"{BASE}/api/complaint/chat", json=payload)
    assert r.status_code == 200, f"Edit chat failed: {r.text}"
    data = r.json()
    assert "batch_number" in str(data.get("complaint", {})), "Batch number not updated"
    assert "updated_fields" in data
    print(f"  [PASS] Chat (edit): Updated fields: {data.get('updated_fields', [])}")
    return data


def test_upload():
    """Tool 3: Upload a complaint document."""
    sample_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads", "sample_complaint.pdf")
    if not os.path.exists(sample_path):
        print(f"  [SKIP] Upload: sample PDF not found at {sample_path}. Generate it first.")
        return None

    with open(sample_path, "rb") as f:
        r = httpx.post(f"{BASE}/api/complaint/upload", files={"file": f})
    assert r.status_code == 200, f"Upload failed: {r.text}"
    data = r.json()
    assert data.get("complaint") is not None, "No complaint from upload"
    print(f"  [PASS] Upload: Created {data['complaint']['display_id']}")
    return data["complaint"]["complaint_id"]


def test_summary(complaint_id):
    """Bonus: Generate summary."""
    payload = {"complaint_id": complaint_id}
    r = httpx.post(f"{BASE}/api/complaints/summary", json=payload)
    assert r.status_code == 200, f"Summary failed: {r.text}"
    data = r.json()
    assert "summary" in data
    assert len(data["summary"]) > 20
    print(f"  [PASS] Summary generated ({len(data['summary'])} chars)")


def main():
    print("AIVOA Copilot — Smoke Tests")
    print("=" * 40)
    print()

    test_health()
    test_list_complaints()

    print()
    print("--- Testing Tool 1: Log Complaint ---")
    cid = test_chat_new()

    print()
    print("--- Testing Tool 2: Edit Complaint ---")
    test_chat_edit(cid)

    print()
    print("--- Testing Tool 3: Document Upload ---")
    upload_cid = test_upload()

    print()
    print("--- Testing Summary (Bonus) ---")
    test_summary(cid)
    if upload_cid:
        test_summary(upload_cid)

    print()
    print("=" * 40)
    print("All tests passed!")
    print("=" * 40)


if __name__ == "__main__":
    main()
