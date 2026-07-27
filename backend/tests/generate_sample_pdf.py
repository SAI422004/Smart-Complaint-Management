"""
Generate a realistic sample pharmaceutical complaint PDF for demo purposes.
Creates a formal customer complaint letter from a pharmacy chain about
Metformin Hydrochloride API.

Usage: python generate_sample_pdf.py
Output: ../uploads/sample_complaint.pdf
"""

import os
from datetime import datetime

try:
    from fpdf import FPDF
except ImportError:
    print("fpdf2 not installed. Install it with: pip install fpdf2")
    raise


class ComplaintPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 8)
        self.cell(0, 5, "CONFIDENTIAL -- CUSTOMER COMPLAINT", align="L")
        self.cell(0, 5, f"Date: {datetime.utcnow().strftime('%d-%b-%Y')}", align="R", new_x="LMARGIN", new_y="NEXT")
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 6)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")


def generate_pdf(output_path: str):
    pdf = ComplaintPDF()
    pdf.alias_nb_pages()
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, "FORMAL CUSTOMER COMPLAINT NOTIFICATION", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # Sender info
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "FROM:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, "MediCare Plus Pharmacy Chain", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, "Quality Assurance Department", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, "42 Healthcare Boulevard, Mumbai - 400001, India", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, "Contact: Dr. Priya Sharma, QA Manager | priya.sharma@medicareplus.in", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, "Phone: +91-22-2345-6789", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # To
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(0, 6, "TO:", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 5, "AIVOA Pharma Ltd.", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, "Quality Complaints Division", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, "Unit 7, Pharmaceutical Industrial Zone", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5, "Hyderabad - 500032, India", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    # Subject
    pdf.set_font("Helvetica", "B", 11)
    pdf.cell(0, 7, "SUBJECT: QUALITY COMPLAINT -- METFORMIN HYDROCHLORIDE API (IP/BP)", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    # Body
    pdf.set_font("Helvetica", "", 10)
    body_lines = [
        "Dear Sir/Madam,",
        "",
        "We are writing to formally report a quality complaint regarding the above-referenced product.",
        "",
        "Product Details:",
        "- Product: Metformin Hydrochloride API",
        "- Grade: IP/BP",
        "- Batch/Lot Number: MFA260712A",
        "- Manufacturing Date: 12-Jul-2026",
        "- Expiry Date: 11-Jul-2028",
        "- Quantity Received: 100 kg (4 HDPE drums, 25 kg each)",
        "- Affected Quantity: 50 kg (2 HDPE drums)",
        "",
        "Description of Defect:",
        "Upon receipt and visual inspection of the shipment, two of the four HDPE drums (Drums #2 and #4) "
        "were found to have compromised tamper-evident seals. Upon opening, the API powder in these drums "
        "appeared to have an abnormal off-white discoloration with visible agglomeration/clumping, "
        "suggesting possible moisture ingress. The material also had a slight odor not characteristic "
        "of the standard product.",
        "",
        "We have quarantined the affected drums pending your investigation. The remaining two drums "
        "(#1 and #3) appear satisfactory and have been accepted into inventory.",
        "",
        "Market: India (Mumbai region, domestic supply chain)",
        "",
        "We request an urgent investigation and replacement of the affected 50 kg. Please advise on "
        "return of the impacted material and any documentation required for your investigation.",
        "",
        "Thank you,",
        "",
        "Dr. Priya Sharma",
        "Quality Assurance Manager",
        "MediCare Plus Pharmacy Chain",
    ]
    for line in body_lines:
        pdf.cell(0, 5, line, new_x="LMARGIN", new_y="NEXT")

    pdf.output(output_path)
    print(f"Sample complaint PDF generated: {output_path}")


if __name__ == "__main__":
    output_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "sample_complaint.pdf")
    generate_pdf(output_path)
