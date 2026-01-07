#!/usr/bin/env python3
"""
Generate synthetic sample documents for testing field detection.

Creates 10 varied contract documents with different field types and layouts.
"""

import os
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)
from reportlab.lib import colors
from reportlab.pdfgen import canvas


def create_nda(output_path: Path):
    """Create a Non-Disclosure Agreement."""
    doc = SimpleDocTemplate(str(output_path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Title
    title_style = ParagraphStyle(
        'Title', parent=styles['Heading1'], fontSize=18, alignment=1
    )
    story.append(Paragraph("NON-DISCLOSURE AGREEMENT", title_style))
    story.append(Spacer(1, 20))

    # Intro
    story.append(Paragraph(
        "This Non-Disclosure Agreement (\"Agreement\") is entered into as of "
        "_________________ (\"Effective Date\") by and between:",
        styles['Normal']
    ))
    story.append(Spacer(1, 10))

    # Parties
    story.append(Paragraph(
        "<b>Disclosing Party:</b> _______________________________ (\"Company\")",
        styles['Normal']
    ))
    story.append(Spacer(1, 5))
    story.append(Paragraph(
        "<b>Receiving Party:</b> ________________________________ (\"Contractor\")",
        styles['Normal']
    ))
    story.append(Spacer(1, 20))

    # Terms
    story.append(Paragraph("1. CONFIDENTIAL INFORMATION", styles['Heading2']))
    story.append(Paragraph(
        "\"Confidential Information\" means any non-public information disclosed by "
        "either party to the other, whether orally, in writing, or by any other means.",
        styles['Normal']
    ))
    story.append(Spacer(1, 10))

    story.append(Paragraph("2. OBLIGATIONS", styles['Heading2']))
    story.append(Paragraph(
        "The Receiving Party agrees to hold the Confidential Information in strict "
        "confidence and not to disclose it to any third party.",
        styles['Normal']
    ))
    story.append(Spacer(1, 10))

    story.append(Paragraph("3. TERM", styles['Heading2']))
    story.append(Paragraph(
        "This Agreement shall remain in effect for a period of ______ years from "
        "the Effective Date.",
        styles['Normal']
    ))
    story.append(Spacer(1, 30))

    # Signatures
    story.append(Paragraph("IN WITNESS WHEREOF, the parties have executed this Agreement:", styles['Normal']))
    story.append(Spacer(1, 20))

    sig_data = [
        ["COMPANY", "CONTRACTOR"],
        ["", ""],
        ["Signature: ____________________", "Signature: ____________________"],
        ["Name: ________________________", "Name: ________________________"],
        ["Title: ________________________", "Title: ________________________"],
        ["Date: _________________________", "Date: _________________________"],
    ]
    sig_table = Table(sig_data, colWidths=[3*inch, 3*inch])
    sig_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 12),
    ]))
    story.append(sig_table)

    doc.build(story)


def create_contractor_agreement(output_path: Path):
    """Create an Independent Contractor Agreement."""
    doc = SimpleDocTemplate(str(output_path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, alignment=1)
    story.append(Paragraph("INDEPENDENT CONTRACTOR AGREEMENT", title_style))
    story.append(Spacer(1, 20))

    story.append(Paragraph(
        "This Independent Contractor Agreement is made effective as of {{effective_date}}.",
        styles['Normal']
    ))
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>BETWEEN:</b>", styles['Normal']))
    story.append(Paragraph("Client Name: _________________________________", styles['Normal']))
    story.append(Paragraph("Client Email: ________________________________", styles['Normal']))
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>AND:</b>", styles['Normal']))
    story.append(Paragraph("Contractor Name: _____________________________", styles['Normal']))
    story.append(Paragraph("Contractor Email: ____________________________", styles['Normal']))
    story.append(Spacer(1, 20))

    story.append(Paragraph("SCOPE OF WORK", styles['Heading2']))
    story.append(Paragraph(
        "The Contractor agrees to perform the following services: _________________"
        "___________________________________________________________________",
        styles['Normal']
    ))
    story.append(Spacer(1, 10))

    story.append(Paragraph("COMPENSATION", styles['Heading2']))
    story.append(Paragraph(
        "The Client agrees to pay the Contractor $__________ per hour/project.",
        styles['Normal']
    ))
    story.append(Spacer(1, 10))

    # Checkboxes
    story.append(Paragraph("CONTRACTOR ACKNOWLEDGEMENTS:", styles['Heading2']))
    story.append(Paragraph("[ ] I acknowledge that I am an independent contractor", styles['Normal']))
    story.append(Paragraph("[ ] I will provide my own equipment and tools", styles['Normal']))
    story.append(Paragraph("[ ] I understand I am responsible for my own taxes", styles['Normal']))
    story.append(Spacer(1, 30))

    # Signatures
    story.append(Paragraph("<b>CLIENT SIGNATURE</b>", styles['Normal']))
    story.append(Paragraph("Signature: ___________________________ Date: ____________", styles['Normal']))
    story.append(Paragraph("Print Name: __________________________", styles['Normal']))
    story.append(Spacer(1, 20))

    story.append(Paragraph("<b>CONTRACTOR SIGNATURE</b>", styles['Normal']))
    story.append(Paragraph("Signature: ___________________________ Date: ____________", styles['Normal']))
    story.append(Paragraph("Print Name: __________________________", styles['Normal']))
    story.append(Paragraph("Initials: _____", styles['Normal']))

    doc.build(story)


def create_lease_agreement(output_path: Path):
    """Create a Residential Lease Agreement."""
    doc = SimpleDocTemplate(str(output_path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, alignment=1)
    story.append(Paragraph("RESIDENTIAL LEASE AGREEMENT", title_style))
    story.append(Spacer(1, 20))

    story.append(Paragraph(
        "This Lease Agreement (\"Lease\") is entered into on _________________ "
        "between the Landlord and Tenant identified below.",
        styles['Normal']
    ))
    story.append(Spacer(1, 15))

    # Parties
    story.append(Paragraph("<b>LANDLORD INFORMATION</b>", styles['Heading2']))
    story.append(Paragraph("Name: _______________________________________", styles['Normal']))
    story.append(Paragraph("Address: _____________________________________", styles['Normal']))
    story.append(Paragraph("Phone: _______________________________________", styles['Normal']))
    story.append(Paragraph("Email: _______________________________________", styles['Normal']))
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>TENANT INFORMATION</b>", styles['Heading2']))
    story.append(Paragraph("Name: _______________________________________", styles['Normal']))
    story.append(Paragraph("Current Address: _____________________________", styles['Normal']))
    story.append(Paragraph("Phone: _______________________________________", styles['Normal']))
    story.append(Paragraph("Email: _______________________________________", styles['Normal']))
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>PROPERTY</b>", styles['Heading2']))
    story.append(Paragraph("Address: _____________________________________", styles['Normal']))
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>LEASE TERMS</b>", styles['Heading2']))
    story.append(Paragraph("Monthly Rent: $______________", styles['Normal']))
    story.append(Paragraph("Security Deposit: $__________", styles['Normal']))
    story.append(Paragraph("Lease Start Date: ___________", styles['Normal']))
    story.append(Paragraph("Lease End Date: _____________", styles['Normal']))
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>ACKNOWLEDGEMENTS</b>", styles['Normal']))
    story.append(Paragraph("[ ] Tenant has received a copy of the lease", styles['Normal']))
    story.append(Paragraph("[ ] Tenant has inspected the property", styles['Normal']))
    story.append(Paragraph("[ ] Tenant agrees to the terms and conditions", styles['Normal']))
    story.append(Spacer(1, 30))

    # Signatures
    story.append(Paragraph("<b>LANDLORD</b>", styles['Normal']))
    story.append(Paragraph("Signature: _________________________ Date: ____________", styles['Normal']))
    story.append(Paragraph("Print Name: ________________________", styles['Normal']))
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>TENANT</b>", styles['Normal']))
    story.append(Paragraph("Signature: _________________________ Date: ____________", styles['Normal']))
    story.append(Paragraph("Print Name: ________________________", styles['Normal']))

    doc.build(story)


def create_employment_offer(output_path: Path):
    """Create an Employment Offer Letter."""
    doc = SimpleDocTemplate(str(output_path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    # Date
    story.append(Paragraph("Date: ________________", styles['Normal']))
    story.append(Spacer(1, 20))

    # Recipient
    story.append(Paragraph("To: _________________________________", styles['Normal']))
    story.append(Paragraph("Address: _____________________________", styles['Normal']))
    story.append(Paragraph("Email: _______________________________", styles['Normal']))
    story.append(Spacer(1, 20))

    story.append(Paragraph("<b>RE: OFFER OF EMPLOYMENT</b>", styles['Heading2']))
    story.append(Spacer(1, 10))

    story.append(Paragraph(
        "We are pleased to offer you the position of _____________________ "
        "at our company. This letter outlines the terms of your employment.",
        styles['Normal']
    ))
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>Position:</b> ____________________________", styles['Normal']))
    story.append(Paragraph("<b>Department:</b> __________________________", styles['Normal']))
    story.append(Paragraph("<b>Start Date:</b> {{start_date}}", styles['Normal']))
    story.append(Paragraph("<b>Salary:</b> $______________ per year", styles['Normal']))
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>BENEFITS</b>", styles['Heading2']))
    story.append(Paragraph("[ ] Health Insurance", styles['Normal']))
    story.append(Paragraph("[ ] Dental Insurance", styles['Normal']))
    story.append(Paragraph("[ ] 401(k) Plan", styles['Normal']))
    story.append(Paragraph("[ ] Paid Time Off", styles['Normal']))
    story.append(Spacer(1, 20))

    story.append(Paragraph(
        "Please sign below to indicate your acceptance of this offer.",
        styles['Normal']
    ))
    story.append(Spacer(1, 30))

    story.append(Paragraph("<b>EMPLOYEE ACCEPTANCE</b>", styles['Normal']))
    story.append(Paragraph("Signature: ___________________________", styles['Normal']))
    story.append(Paragraph("Print Name: __________________________", styles['Normal']))
    story.append(Paragraph("Date: ________________________________", styles['Normal']))
    story.append(Spacer(1, 20))

    story.append(Paragraph("<b>COMPANY REPRESENTATIVE</b>", styles['Normal']))
    story.append(Paragraph("Signature: ___________________________", styles['Normal']))
    story.append(Paragraph("Print Name: __________________________", styles['Normal']))
    story.append(Paragraph("Title: _______________________________", styles['Normal']))
    story.append(Paragraph("Date: ________________________________", styles['Normal']))

    doc.build(story)


def create_service_agreement(output_path: Path):
    """Create a Service Agreement with anchor tags."""
    doc = SimpleDocTemplate(str(output_path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, alignment=1)
    story.append(Paragraph("SERVICE AGREEMENT", title_style))
    story.append(Spacer(1, 20))

    story.append(Paragraph(
        "This Service Agreement (\"Agreement\") is made effective as of [date|sender].",
        styles['Normal']
    ))
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>SERVICE PROVIDER</b>", styles['Heading2']))
    story.append(Paragraph("Company Name: [text|sender]", styles['Normal']))
    story.append(Paragraph("Contact Name: [name|signer2]", styles['Normal']))
    story.append(Paragraph("Email: [email|signer2]", styles['Normal']))
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>CLIENT</b>", styles['Heading2']))
    story.append(Paragraph("Name: [name|signer1]", styles['Normal']))
    story.append(Paragraph("Email: [email|signer1]", styles['Normal']))
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>SERVICES</b>", styles['Heading2']))
    story.append(Paragraph(
        "The Service Provider agrees to provide the following services: {{service_description}}",
        styles['Normal']
    ))
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>PAYMENT</b>", styles['Heading2']))
    story.append(Paragraph("Total Fee: {{total_fee}}", styles['Normal']))
    story.append(Paragraph("Payment Terms: {{payment_terms}}", styles['Normal']))
    story.append(Spacer(1, 30))

    story.append(Paragraph("<b>SIGNATURES</b>", styles['Heading2']))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Client Signature: [sig|signer1]", styles['Normal']))
    story.append(Paragraph("Client Date: [date|signer1]", styles['Normal']))
    story.append(Spacer(1, 15))

    story.append(Paragraph("Provider Signature: [sig|signer2]", styles['Normal']))
    story.append(Paragraph("Provider Date: [date|signer2]", styles['Normal']))

    doc.build(story)


def create_consent_form(output_path: Path):
    """Create a Consent Form."""
    doc = SimpleDocTemplate(str(output_path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, alignment=1)
    story.append(Paragraph("CONSENT FORM", title_style))
    story.append(Spacer(1, 20))

    story.append(Paragraph("<b>PARTICIPANT INFORMATION</b>", styles['Heading2']))
    story.append(Paragraph("Full Name: _________________________________", styles['Normal']))
    story.append(Paragraph("Date of Birth: _____________________________", styles['Normal']))
    story.append(Paragraph("Email Address: _____________________________", styles['Normal']))
    story.append(Paragraph("Phone Number: ______________________________", styles['Normal']))
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>CONSENT STATEMENTS</b>", styles['Heading2']))
    story.append(Paragraph(
        "Please read each statement carefully and check the box if you agree:",
        styles['Normal']
    ))
    story.append(Spacer(1, 10))

    story.append(Paragraph("[ ] I consent to participate in this study", styles['Normal']))
    story.append(Paragraph("[ ] I understand the risks and benefits", styles['Normal']))
    story.append(Paragraph("[ ] I agree to have my data collected and analyzed", styles['Normal']))
    story.append(Paragraph("[ ] I understand I can withdraw at any time", styles['Normal']))
    story.append(Paragraph("[ ] I am at least 18 years of age", styles['Normal']))
    story.append(Spacer(1, 30))

    story.append(Paragraph("<b>PARTICIPANT</b>", styles['Normal']))
    story.append(Paragraph("Signature: _________________________________", styles['Normal']))
    story.append(Paragraph("Date Signed: _______________________________", styles['Normal']))
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>WITNESS</b>", styles['Normal']))
    story.append(Paragraph("Signature: _________________________________", styles['Normal']))
    story.append(Paragraph("Print Name: ________________________________", styles['Normal']))
    story.append(Paragraph("Date: ______________________________________", styles['Normal']))

    doc.build(story)


def create_purchase_agreement(output_path: Path):
    """Create a Purchase Agreement."""
    doc = SimpleDocTemplate(str(output_path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, alignment=1)
    story.append(Paragraph("PURCHASE AGREEMENT", title_style))
    story.append(Spacer(1, 20))

    story.append(Paragraph(
        "This Purchase Agreement is entered into as of _________________.",
        styles['Normal']
    ))
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>SELLER</b>", styles['Heading2']))
    story.append(Paragraph("Name: _____________________________________", styles['Normal']))
    story.append(Paragraph("Address: __________________________________", styles['Normal']))
    story.append(Paragraph("Email: ____________________________________", styles['Normal']))
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>BUYER</b>", styles['Heading2']))
    story.append(Paragraph("Name: _____________________________________", styles['Normal']))
    story.append(Paragraph("Address: __________________________________", styles['Normal']))
    story.append(Paragraph("Email: ____________________________________", styles['Normal']))
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>ITEM DESCRIPTION</b>", styles['Heading2']))
    story.append(Paragraph("Description: ______________________________", styles['Normal']))
    story.append(Paragraph("Serial Number: ____________________________", styles['Normal']))
    story.append(Paragraph("Condition: ________________________________", styles['Normal']))
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>PURCHASE PRICE</b>", styles['Heading2']))
    story.append(Paragraph("Amount: $__________________________________", styles['Normal']))
    story.append(Paragraph("Payment Method: ___________________________", styles['Normal']))
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>ACKNOWLEDGEMENTS</b>", styles['Normal']))
    story.append(Paragraph("[ ] Seller confirms ownership of the item", styles['Normal']))
    story.append(Paragraph("[ ] Buyer has inspected the item", styles['Normal']))
    story.append(Paragraph("[ ] Both parties agree to the terms", styles['Normal']))
    story.append(Spacer(1, 30))

    story.append(Paragraph("<b>SELLER</b>", styles['Normal']))
    story.append(Paragraph("Signature: _________________ Date: ___________", styles['Normal']))
    story.append(Paragraph("Print Name: ________________________________", styles['Normal']))
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>BUYER</b>", styles['Normal']))
    story.append(Paragraph("Signature: _________________ Date: ___________", styles['Normal']))
    story.append(Paragraph("Print Name: ________________________________", styles['Normal']))

    doc.build(story)


def create_release_waiver(output_path: Path):
    """Create a Release and Waiver form."""
    doc = SimpleDocTemplate(str(output_path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, alignment=1)
    story.append(Paragraph("RELEASE AND WAIVER OF LIABILITY", title_style))
    story.append(Spacer(1, 20))

    story.append(Paragraph("<b>PARTICIPANT INFORMATION</b>", styles['Heading2']))
    story.append(Paragraph("Name: ______________________________________", styles['Normal']))
    story.append(Paragraph("Address: ___________________________________", styles['Normal']))
    story.append(Paragraph("Phone: _____________________________________", styles['Normal']))
    story.append(Paragraph("Email: _____________________________________", styles['Normal']))
    story.append(Paragraph("Emergency Contact: __________________________", styles['Normal']))
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>ACTIVITY</b>", styles['Heading2']))
    story.append(Paragraph("Event/Activity: _____________________________", styles['Normal']))
    story.append(Paragraph("Date(s): ___________________________________", styles['Normal']))
    story.append(Paragraph("Location: __________________________________", styles['Normal']))
    story.append(Spacer(1, 15))

    story.append(Paragraph(
        "I understand and acknowledge that participation in this activity involves "
        "inherent risks. I voluntarily assume all risks associated with participation.",
        styles['Normal']
    ))
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>INITIAL EACH:</b>", styles['Normal']))
    story.append(Paragraph("_____ I have read and understand this waiver", styles['Normal']))
    story.append(Paragraph("_____ I am at least 18 years old", styles['Normal']))
    story.append(Paragraph("_____ I am in good physical condition", styles['Normal']))
    story.append(Spacer(1, 30))

    story.append(Paragraph("<b>PARTICIPANT</b>", styles['Normal']))
    story.append(Paragraph("Signature: _________________________________", styles['Normal']))
    story.append(Paragraph("Print Name: ________________________________", styles['Normal']))
    story.append(Paragraph("Date: ______________________________________", styles['Normal']))

    doc.build(story)


def create_power_of_attorney(output_path: Path):
    """Create a Power of Attorney form."""
    doc = SimpleDocTemplate(str(output_path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, alignment=1)
    story.append(Paragraph("POWER OF ATTORNEY", title_style))
    story.append(Spacer(1, 20))

    story.append(Paragraph(
        "I, ______________________________ (\"Principal\"), of legal age and sound mind, "
        "hereby appoint:",
        styles['Normal']
    ))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Name: ______________________________________", styles['Normal']))
    story.append(Paragraph("Address: ___________________________________", styles['Normal']))
    story.append(Paragraph("Phone: _____________________________________", styles['Normal']))
    story.append(Paragraph("Email: _____________________________________", styles['Normal']))
    story.append(Spacer(1, 10))

    story.append(Paragraph(
        "as my Attorney-in-Fact (\"Agent\") to act in my name and on my behalf.",
        styles['Normal']
    ))
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>POWERS GRANTED</b>", styles['Heading2']))
    story.append(Paragraph("[ ] Financial matters", styles['Normal']))
    story.append(Paragraph("[ ] Real estate transactions", styles['Normal']))
    story.append(Paragraph("[ ] Legal proceedings", styles['Normal']))
    story.append(Paragraph("[ ] Healthcare decisions", styles['Normal']))
    story.append(Paragraph("[ ] All matters", styles['Normal']))
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>EFFECTIVE DATE</b>", styles['Heading2']))
    story.append(Paragraph("This Power of Attorney is effective: _______________", styles['Normal']))
    story.append(Spacer(1, 30))

    story.append(Paragraph("<b>PRINCIPAL</b>", styles['Normal']))
    story.append(Paragraph("Signature: _________________________________", styles['Normal']))
    story.append(Paragraph("Print Name: ________________________________", styles['Normal']))
    story.append(Paragraph("Date: ______________________________________", styles['Normal']))
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>WITNESS 1</b>", styles['Normal']))
    story.append(Paragraph("Signature: _________________________________", styles['Normal']))
    story.append(Paragraph("Print Name: ________________________________", styles['Normal']))
    story.append(Paragraph("Date: ______________________________________", styles['Normal']))
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>WITNESS 2</b>", styles['Normal']))
    story.append(Paragraph("Signature: _________________________________", styles['Normal']))
    story.append(Paragraph("Print Name: ________________________________", styles['Normal']))
    story.append(Paragraph("Date: ______________________________________", styles['Normal']))
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>NOTARY</b>", styles['Normal']))
    story.append(Paragraph("Signature: _________________________________", styles['Normal']))
    story.append(Paragraph("Commission Expires: _________________________", styles['Normal']))

    doc.build(story)


def create_partnership_agreement(output_path: Path):
    """Create a Partnership Agreement."""
    doc = SimpleDocTemplate(str(output_path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, alignment=1)
    story.append(Paragraph("PARTNERSHIP AGREEMENT", title_style))
    story.append(Spacer(1, 20))

    story.append(Paragraph(
        "This Partnership Agreement (\"Agreement\") is made and entered into as of "
        "{{effective_date}} by and between:",
        styles['Normal']
    ))
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>PARTNER 1</b>", styles['Heading2']))
    story.append(Paragraph("Name: ______________________________________", styles['Normal']))
    story.append(Paragraph("Address: ___________________________________", styles['Normal']))
    story.append(Paragraph("Email: _____________________________________", styles['Normal']))
    story.append(Paragraph("Ownership %: _______________________________", styles['Normal']))
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>PARTNER 2</b>", styles['Heading2']))
    story.append(Paragraph("Name: ______________________________________", styles['Normal']))
    story.append(Paragraph("Address: ___________________________________", styles['Normal']))
    story.append(Paragraph("Email: _____________________________________", styles['Normal']))
    story.append(Paragraph("Ownership %: _______________________________", styles['Normal']))
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>PARTNERSHIP DETAILS</b>", styles['Heading2']))
    story.append(Paragraph("Partnership Name: ___________________________", styles['Normal']))
    story.append(Paragraph("Business Purpose: ___________________________", styles['Normal']))
    story.append(Paragraph("Initial Capital: $___________________________", styles['Normal']))
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>ACKNOWLEDGEMENTS</b>", styles['Normal']))
    story.append(Paragraph("[ ] Both partners agree to the ownership percentages", styles['Normal']))
    story.append(Paragraph("[ ] Both partners agree to the capital contributions", styles['Normal']))
    story.append(Paragraph("[ ] Both partners have reviewed the agreement", styles['Normal']))
    story.append(Spacer(1, 30))

    story.append(Paragraph("<b>PARTNER 1</b>", styles['Normal']))
    story.append(Paragraph("Signature: _________________________________", styles['Normal']))
    story.append(Paragraph("Print Name: ________________________________", styles['Normal']))
    story.append(Paragraph("Date: ______________________________________", styles['Normal']))
    story.append(Paragraph("Initials: __________________________________", styles['Normal']))
    story.append(Spacer(1, 15))

    story.append(Paragraph("<b>PARTNER 2</b>", styles['Normal']))
    story.append(Paragraph("Signature: _________________________________", styles['Normal']))
    story.append(Paragraph("Print Name: ________________________________", styles['Normal']))
    story.append(Paragraph("Date: ______________________________________", styles['Normal']))
    story.append(Paragraph("Initials: __________________________________", styles['Normal']))

    doc.build(story)


def create_loan_agreement(output_path: Path):
    """Create a Loan Agreement with 3 signers: borrower, lender, guarantor."""
    doc = SimpleDocTemplate(str(output_path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=16, alignment=1)
    story.append(Paragraph("LOAN AGREEMENT", title_style))
    story.append(Spacer(1, 15))

    story.append(Paragraph(
        "This Loan Agreement is entered into as of {{agreement_date}} by and among:",
        styles['Normal']
    ))
    story.append(Spacer(1, 15))

    # Loan terms
    story.append(Paragraph("<b>LOAN TERMS</b>", styles['Heading2']))
    story.append(Paragraph("Loan Amount: $______________________________", styles['Normal']))
    story.append(Paragraph("Interest Rate: _____________________________", styles['Normal']))
    story.append(Paragraph("Term (months): _____________________________", styles['Normal']))
    story.append(Spacer(1, 15))

    # Borrower
    story.append(Paragraph("<b>BORROWER</b>", styles['Heading2']))
    story.append(Paragraph("Borrower Name: _____________________________", styles['Normal']))
    story.append(Paragraph("Borrower Address: __________________________", styles['Normal']))
    story.append(Paragraph("Borrower Email: ____________________________", styles['Normal']))
    story.append(Spacer(1, 10))

    # Lender
    story.append(Paragraph("<b>LENDER</b>", styles['Heading2']))
    story.append(Paragraph("Lender Name: _______________________________", styles['Normal']))
    story.append(Paragraph("Lender Address: ____________________________", styles['Normal']))
    story.append(Paragraph("Lender Email: ______________________________", styles['Normal']))
    story.append(Spacer(1, 10))

    # Guarantor
    story.append(Paragraph("<b>GUARANTOR</b>", styles['Heading2']))
    story.append(Paragraph("Guarantor Name: ____________________________", styles['Normal']))
    story.append(Paragraph("Guarantor Address: _________________________", styles['Normal']))
    story.append(Paragraph("Guarantor Email: ___________________________", styles['Normal']))
    story.append(Spacer(1, 15))

    # Acknowledgements
    story.append(Paragraph("[ ] Borrower agrees to the loan terms", styles['Normal']))
    story.append(Paragraph("[ ] Guarantor agrees to guarantee repayment", styles['Normal']))
    story.append(Spacer(1, 20))

    # Signatures
    story.append(Paragraph("<b>BORROWER SIGNATURE</b>", styles['Normal']))
    story.append(Paragraph("Signature: _________________________________", styles['Normal']))
    story.append(Paragraph("Date: ______________________________________", styles['Normal']))
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>LENDER SIGNATURE</b>", styles['Normal']))
    story.append(Paragraph("Signature: _________________________________", styles['Normal']))
    story.append(Paragraph("Date: ______________________________________", styles['Normal']))
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>GUARANTOR SIGNATURE</b>", styles['Normal']))
    story.append(Paragraph("Signature: _________________________________", styles['Normal']))
    story.append(Paragraph("Date: ______________________________________", styles['Normal']))

    doc.build(story)


def create_real_estate_contract(output_path: Path):
    """Create a Real Estate Contract with 5 signers using new anchor tag format."""
    doc = SimpleDocTemplate(str(output_path), pagesize=letter)
    styles = getSampleStyleSheet()
    story = []

    title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=14, alignment=1)
    story.append(Paragraph("REAL ESTATE PURCHASE CONTRACT", title_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph(
        "Contract Date: {{contract_date}}",
        styles['Normal']
    ))
    story.append(Paragraph("Property Address: {{property_address}}", styles['Normal']))
    story.append(Paragraph("Purchase Price: ${{purchase_price}}", styles['Normal']))
    story.append(Spacer(1, 10))

    # Buyer
    story.append(Paragraph("<b>BUYER</b>", styles['Heading2']))
    story.append(Paragraph("Buyer Name: ________________________________", styles['Normal']))
    story.append(Paragraph("Buyer Email: _______________________________", styles['Normal']))
    story.append(Spacer(1, 8))

    # Seller
    story.append(Paragraph("<b>SELLER</b>", styles['Heading2']))
    story.append(Paragraph("Seller Name: _______________________________", styles['Normal']))
    story.append(Paragraph("Seller Email: ______________________________", styles['Normal']))
    story.append(Spacer(1, 8))

    # Buyer's Agent
    story.append(Paragraph("<b>BUYER'S AGENT</b>", styles['Heading2']))
    story.append(Paragraph("Agent Name: ________________________________", styles['Normal']))
    story.append(Paragraph("License #: _________________________________", styles['Normal']))
    story.append(Spacer(1, 8))

    # Seller's Agent
    story.append(Paragraph("<b>SELLER'S AGENT</b>", styles['Heading2']))
    story.append(Paragraph("Agent Name: ________________________________", styles['Normal']))
    story.append(Paragraph("License #: _________________________________", styles['Normal']))
    story.append(Spacer(1, 8))

    # Escrow Officer
    story.append(Paragraph("<b>ESCROW OFFICER</b>", styles['Heading2']))
    story.append(Paragraph("Officer Name: ______________________________", styles['Normal']))
    story.append(Paragraph("Escrow Company: ____________________________", styles['Normal']))
    story.append(Spacer(1, 15))

    # Signature section with new anchor tag format
    story.append(Paragraph("<b>SIGNATURES</b>", styles['Heading2']))
    story.append(Spacer(1, 8))

    story.append(Paragraph("Buyer: [sig|role:buyer] Date: [date|role:buyer]", styles['Normal']))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Seller: [sig|role:seller] Date: [date|role:seller]", styles['Normal']))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Buyer Agent: [sig|role:buyer_agent] Date: [date|role:buyer_agent]", styles['Normal']))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Seller Agent: [sig|role:seller_agent] Date: [date|role:seller_agent]", styles['Normal']))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Escrow: [sig|role:escrow] Date: [date|role:escrow]", styles['Normal']))

    doc.build(story)


def main():
    """Generate all sample documents."""
    output_dir = Path(__file__).parent.parent / "sample_docs"
    output_dir.mkdir(exist_ok=True)

    documents = [
        ("01_nda.pdf", create_nda),
        ("02_contractor_agreement.pdf", create_contractor_agreement),
        ("03_lease_agreement.pdf", create_lease_agreement),
        ("04_employment_offer.pdf", create_employment_offer),
        ("05_service_agreement.pdf", create_service_agreement),
        ("06_consent_form.pdf", create_consent_form),
        ("07_purchase_agreement.pdf", create_purchase_agreement),
        ("08_release_waiver.pdf", create_release_waiver),
        ("09_power_of_attorney.pdf", create_power_of_attorney),
        ("10_partnership_agreement.pdf", create_partnership_agreement),
        # NEW: N-signer documents (3+ signers)
        ("11_loan_agreement.pdf", create_loan_agreement),  # 3 signers: borrower, lender, guarantor
        ("12_real_estate_contract.pdf", create_real_estate_contract),  # 5 signers using anchor tags
    ]

    print(f"Generating {len(documents)} sample documents...")

    for filename, generator in documents:
        output_path = output_dir / filename
        generator(output_path)
        print(f"  Created: {filename}")

    print(f"\nAll documents generated in: {output_dir}")


if __name__ == "__main__":
    main()
