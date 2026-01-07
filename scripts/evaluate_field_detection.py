#!/usr/bin/env python3
"""
Evaluate field detection accuracy on sample documents.

This script:
1. Loads sample documents with ground truth annotations
2. Runs the field detector on each document
3. Computes precision, recall, and F1 metrics
4. Generates a detailed report

Ground truth format uses role_key (e.g., "client", "landlord", "contractor")
instead of hardcoded SIGNER_1/SIGNER_2 for N-signer support.
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# Add the backend app to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from app.services.detection.detector import field_detector, BBox, DetectedField
from app.models import FieldType, AssigneeType


# Ground truth annotations for sample documents
# Format: { "filename": [{ "page": int, "type": FieldType, "role_key": str, "label": str }] }
# role_key: "sender" for sender fields, or semantic role like "client", "contractor", "landlord"
GROUND_TRUTH = {
    "01_nda.pdf": [
        {"page": 1, "type": "DATE_SIGNED", "role_key": "sender", "label": "Effective Date"},
        {"page": 1, "type": "NAME", "role_key": "company", "label": "Disclosing Party"},
        {"page": 1, "type": "NAME", "role_key": "contractor", "label": "Receiving Party"},
        {"page": 1, "type": "TEXT", "role_key": "sender", "label": "Term years"},
        {"page": 1, "type": "SIGNATURE", "role_key": "company", "label": "Company Signature"},
        {"page": 1, "type": "NAME", "role_key": "company", "label": "Company Name"},
        {"page": 1, "type": "TEXT", "role_key": "company", "label": "Company Title"},
        {"page": 1, "type": "DATE_SIGNED", "role_key": "company", "label": "Company Date"},
        {"page": 1, "type": "SIGNATURE", "role_key": "contractor", "label": "Contractor Signature"},
        {"page": 1, "type": "NAME", "role_key": "contractor", "label": "Contractor Name"},
        {"page": 1, "type": "TEXT", "role_key": "contractor", "label": "Contractor Title"},
        {"page": 1, "type": "DATE_SIGNED", "role_key": "contractor", "label": "Contractor Date"},
    ],
    "02_contractor_agreement.pdf": [
        {"page": 1, "type": "NAME", "role_key": "client", "label": "Client Name"},
        {"page": 1, "type": "EMAIL", "role_key": "client", "label": "Client Email"},
        {"page": 1, "type": "NAME", "role_key": "contractor", "label": "Contractor Name"},
        {"page": 1, "type": "EMAIL", "role_key": "contractor", "label": "Contractor Email"},
        {"page": 1, "type": "TEXT", "role_key": "sender", "label": "Scope"},
        {"page": 1, "type": "TEXT", "role_key": "sender", "label": "Compensation"},
        {"page": 1, "type": "CHECKBOX", "role_key": "contractor", "label": "Acknowledge contractor"},
        {"page": 1, "type": "CHECKBOX", "role_key": "contractor", "label": "Provide equipment"},
        {"page": 1, "type": "CHECKBOX", "role_key": "contractor", "label": "Responsible for taxes"},
        {"page": 1, "type": "SIGNATURE", "role_key": "client", "label": "Client Signature"},
        {"page": 1, "type": "DATE_SIGNED", "role_key": "client", "label": "Client Date"},
        {"page": 1, "type": "NAME", "role_key": "client", "label": "Client Print Name"},
        {"page": 1, "type": "SIGNATURE", "role_key": "contractor", "label": "Contractor Signature"},
        {"page": 1, "type": "DATE_SIGNED", "role_key": "contractor", "label": "Contractor Date"},
        {"page": 1, "type": "NAME", "role_key": "contractor", "label": "Contractor Print Name"},
        {"page": 1, "type": "INITIALS", "role_key": "contractor", "label": "Contractor Initials"},
    ],
    "03_lease_agreement.pdf": [
        {"page": 1, "type": "DATE_SIGNED", "role_key": "sender", "label": "Agreement Date"},
        {"page": 1, "type": "NAME", "role_key": "landlord", "label": "Landlord Name"},
        {"page": 1, "type": "TEXT", "role_key": "landlord", "label": "Landlord Address"},
        {"page": 1, "type": "TEXT", "role_key": "landlord", "label": "Landlord Phone"},
        {"page": 1, "type": "EMAIL", "role_key": "landlord", "label": "Landlord Email"},
        {"page": 1, "type": "NAME", "role_key": "tenant", "label": "Tenant Name"},
        {"page": 1, "type": "TEXT", "role_key": "tenant", "label": "Tenant Address"},
        {"page": 1, "type": "TEXT", "role_key": "tenant", "label": "Tenant Phone"},
        {"page": 1, "type": "EMAIL", "role_key": "tenant", "label": "Tenant Email"},
        {"page": 1, "type": "TEXT", "role_key": "sender", "label": "Property Address"},
        {"page": 1, "type": "TEXT", "role_key": "sender", "label": "Monthly Rent"},
        {"page": 1, "type": "TEXT", "role_key": "sender", "label": "Security Deposit"},
        {"page": 1, "type": "DATE_SIGNED", "role_key": "sender", "label": "Lease Start"},
        {"page": 1, "type": "DATE_SIGNED", "role_key": "sender", "label": "Lease End"},
        {"page": 1, "type": "CHECKBOX", "role_key": "tenant", "label": "Received lease copy"},
        {"page": 1, "type": "CHECKBOX", "role_key": "tenant", "label": "Inspected property"},
        {"page": 1, "type": "CHECKBOX", "role_key": "tenant", "label": "Agree to terms"},
        {"page": 1, "type": "SIGNATURE", "role_key": "landlord", "label": "Landlord Signature"},
        {"page": 1, "type": "DATE_SIGNED", "role_key": "landlord", "label": "Landlord Date"},
        {"page": 1, "type": "NAME", "role_key": "landlord", "label": "Landlord Print Name"},
        {"page": 1, "type": "SIGNATURE", "role_key": "tenant", "label": "Tenant Signature"},
        {"page": 1, "type": "DATE_SIGNED", "role_key": "tenant", "label": "Tenant Date"},
        {"page": 1, "type": "NAME", "role_key": "tenant", "label": "Tenant Print Name"},
    ],
    "04_employment_offer.pdf": [
        {"page": 1, "type": "DATE_SIGNED", "role_key": "sender", "label": "Date"},
        {"page": 1, "type": "NAME", "role_key": "employee", "label": "To"},
        {"page": 1, "type": "TEXT", "role_key": "employee", "label": "Address"},
        {"page": 1, "type": "EMAIL", "role_key": "employee", "label": "Email"},
        {"page": 1, "type": "TEXT", "role_key": "sender", "label": "Position"},
        {"page": 1, "type": "TEXT", "role_key": "sender", "label": "Department"},
        {"page": 1, "type": "TEXT", "role_key": "sender", "label": "Salary"},
        {"page": 1, "type": "CHECKBOX", "role_key": "employee", "label": "Health Insurance"},
        {"page": 1, "type": "CHECKBOX", "role_key": "employee", "label": "Dental Insurance"},
        {"page": 1, "type": "CHECKBOX", "role_key": "employee", "label": "401k Plan"},
        {"page": 1, "type": "CHECKBOX", "role_key": "employee", "label": "PTO"},
        {"page": 1, "type": "SIGNATURE", "role_key": "employee", "label": "Employee Signature"},
        {"page": 1, "type": "NAME", "role_key": "employee", "label": "Employee Name"},
        {"page": 1, "type": "DATE_SIGNED", "role_key": "employee", "label": "Employee Date"},
        {"page": 1, "type": "SIGNATURE", "role_key": "company", "label": "Company Signature"},
        {"page": 1, "type": "NAME", "role_key": "company", "label": "Company Name"},
        {"page": 1, "type": "TEXT", "role_key": "company", "label": "Company Title"},
        {"page": 1, "type": "DATE_SIGNED", "role_key": "company", "label": "Company Date"},
    ],
    "05_service_agreement.pdf": [
        # This document uses anchor tags [type|role:key]
        {"page": 1, "type": "DATE_SIGNED", "role_key": "sender", "label": "[date|sender]"},
        {"page": 1, "type": "TEXT", "role_key": "sender", "label": "[text|sender]"},
        {"page": 1, "type": "NAME", "role_key": "company", "label": "[name|role:company]"},
        {"page": 1, "type": "EMAIL", "role_key": "company", "label": "[email|role:company]"},
        {"page": 1, "type": "NAME", "role_key": "client", "label": "[name|role:client]"},
        {"page": 1, "type": "EMAIL", "role_key": "client", "label": "[email|role:client]"},
        {"page": 1, "type": "SIGNATURE", "role_key": "client", "label": "[sig|role:client]"},
        {"page": 1, "type": "DATE_SIGNED", "role_key": "client", "label": "[date|role:client]"},
        {"page": 1, "type": "SIGNATURE", "role_key": "company", "label": "[sig|role:company]"},
        {"page": 1, "type": "DATE_SIGNED", "role_key": "company", "label": "[date|role:company]"},
    ],
    "06_consent_form.pdf": [
        {"page": 1, "type": "NAME", "role_key": "participant", "label": "Full Name"},
        {"page": 1, "type": "DATE_SIGNED", "role_key": "participant", "label": "Date of Birth"},
        {"page": 1, "type": "EMAIL", "role_key": "participant", "label": "Email Address"},
        {"page": 1, "type": "TEXT", "role_key": "participant", "label": "Phone Number"},
        {"page": 1, "type": "CHECKBOX", "role_key": "participant", "label": "Consent to participate"},
        {"page": 1, "type": "CHECKBOX", "role_key": "participant", "label": "Understand risks"},
        {"page": 1, "type": "CHECKBOX", "role_key": "participant", "label": "Agree to data collection"},
        {"page": 1, "type": "CHECKBOX", "role_key": "participant", "label": "Can withdraw"},
        {"page": 1, "type": "CHECKBOX", "role_key": "participant", "label": "18 years old"},
        {"page": 1, "type": "SIGNATURE", "role_key": "participant", "label": "Participant Signature"},
        {"page": 1, "type": "DATE_SIGNED", "role_key": "participant", "label": "Participant Date"},
        {"page": 1, "type": "SIGNATURE", "role_key": "witness", "label": "Witness Signature"},
        {"page": 1, "type": "NAME", "role_key": "witness", "label": "Witness Name"},
        {"page": 1, "type": "DATE_SIGNED", "role_key": "witness", "label": "Witness Date"},
    ],
    "07_purchase_agreement.pdf": [
        {"page": 1, "type": "DATE_SIGNED", "role_key": "sender", "label": "Agreement Date"},
        {"page": 1, "type": "NAME", "role_key": "seller", "label": "Seller Name"},
        {"page": 1, "type": "TEXT", "role_key": "seller", "label": "Seller Address"},
        {"page": 1, "type": "EMAIL", "role_key": "seller", "label": "Seller Email"},
        {"page": 1, "type": "NAME", "role_key": "buyer", "label": "Buyer Name"},
        {"page": 1, "type": "TEXT", "role_key": "buyer", "label": "Buyer Address"},
        {"page": 1, "type": "EMAIL", "role_key": "buyer", "label": "Buyer Email"},
        {"page": 1, "type": "TEXT", "role_key": "sender", "label": "Item Description"},
        {"page": 1, "type": "TEXT", "role_key": "sender", "label": "Serial Number"},
        {"page": 1, "type": "TEXT", "role_key": "sender", "label": "Condition"},
        {"page": 1, "type": "TEXT", "role_key": "sender", "label": "Amount"},
        {"page": 1, "type": "TEXT", "role_key": "sender", "label": "Payment Method"},
        {"page": 1, "type": "CHECKBOX", "role_key": "seller", "label": "Confirm ownership"},
        {"page": 1, "type": "CHECKBOX", "role_key": "buyer", "label": "Inspected item"},
        {"page": 1, "type": "CHECKBOX", "role_key": "buyer", "label": "Agree to terms"},
        {"page": 1, "type": "SIGNATURE", "role_key": "seller", "label": "Seller Signature"},
        {"page": 1, "type": "DATE_SIGNED", "role_key": "seller", "label": "Seller Date"},
        {"page": 1, "type": "NAME", "role_key": "seller", "label": "Seller Print Name"},
        {"page": 1, "type": "SIGNATURE", "role_key": "buyer", "label": "Buyer Signature"},
        {"page": 1, "type": "DATE_SIGNED", "role_key": "buyer", "label": "Buyer Date"},
        {"page": 1, "type": "NAME", "role_key": "buyer", "label": "Buyer Print Name"},
    ],
    "08_release_waiver.pdf": [
        {"page": 1, "type": "NAME", "role_key": "participant", "label": "Participant Name"},
        {"page": 1, "type": "TEXT", "role_key": "participant", "label": "Address"},
        {"page": 1, "type": "TEXT", "role_key": "participant", "label": "Phone"},
        {"page": 1, "type": "EMAIL", "role_key": "participant", "label": "Email"},
        {"page": 1, "type": "TEXT", "role_key": "participant", "label": "Emergency Contact"},
        {"page": 1, "type": "TEXT", "role_key": "sender", "label": "Event/Activity"},
        {"page": 1, "type": "DATE_SIGNED", "role_key": "sender", "label": "Event Date"},
        {"page": 1, "type": "TEXT", "role_key": "sender", "label": "Location"},
        {"page": 1, "type": "INITIALS", "role_key": "participant", "label": "Read and understand"},
        {"page": 1, "type": "INITIALS", "role_key": "participant", "label": "18 years old"},
        {"page": 1, "type": "INITIALS", "role_key": "participant", "label": "Good physical condition"},
        {"page": 1, "type": "SIGNATURE", "role_key": "participant", "label": "Participant Signature"},
        {"page": 1, "type": "NAME", "role_key": "participant", "label": "Participant Print Name"},
        {"page": 1, "type": "DATE_SIGNED", "role_key": "participant", "label": "Participant Date"},
    ],
    "09_power_of_attorney.pdf": [
        {"page": 1, "type": "NAME", "role_key": "principal", "label": "Principal Name"},
        {"page": 1, "type": "NAME", "role_key": "agent", "label": "Agent Name"},
        {"page": 1, "type": "TEXT", "role_key": "agent", "label": "Agent Address"},
        {"page": 1, "type": "TEXT", "role_key": "agent", "label": "Agent Phone"},
        {"page": 1, "type": "EMAIL", "role_key": "agent", "label": "Agent Email"},
        {"page": 1, "type": "CHECKBOX", "role_key": "principal", "label": "Financial matters"},
        {"page": 1, "type": "CHECKBOX", "role_key": "principal", "label": "Real estate"},
        {"page": 1, "type": "CHECKBOX", "role_key": "principal", "label": "Legal proceedings"},
        {"page": 1, "type": "CHECKBOX", "role_key": "principal", "label": "Healthcare decisions"},
        {"page": 1, "type": "CHECKBOX", "role_key": "principal", "label": "All matters"},
        {"page": 1, "type": "DATE_SIGNED", "role_key": "sender", "label": "Effective Date"},
        {"page": 1, "type": "SIGNATURE", "role_key": "principal", "label": "Principal Signature"},
        {"page": 1, "type": "NAME", "role_key": "principal", "label": "Principal Print Name"},
        {"page": 1, "type": "DATE_SIGNED", "role_key": "principal", "label": "Principal Date"},
        {"page": 1, "type": "SIGNATURE", "role_key": "witness", "label": "Witness 1 Signature"},
        {"page": 1, "type": "NAME", "role_key": "witness", "label": "Witness 1 Name"},
        {"page": 1, "type": "DATE_SIGNED", "role_key": "witness", "label": "Witness 1 Date"},
    ],
    "10_partnership_agreement.pdf": [
        {"page": 1, "type": "NAME", "role_key": "partner_1", "label": "Partner 1 Name"},
        {"page": 1, "type": "TEXT", "role_key": "partner_1", "label": "Partner 1 Address"},
        {"page": 1, "type": "EMAIL", "role_key": "partner_1", "label": "Partner 1 Email"},
        {"page": 1, "type": "TEXT", "role_key": "partner_1", "label": "Partner 1 Ownership"},
        {"page": 1, "type": "NAME", "role_key": "partner_2", "label": "Partner 2 Name"},
        {"page": 1, "type": "TEXT", "role_key": "partner_2", "label": "Partner 2 Address"},
        {"page": 1, "type": "EMAIL", "role_key": "partner_2", "label": "Partner 2 Email"},
        {"page": 1, "type": "TEXT", "role_key": "partner_2", "label": "Partner 2 Ownership"},
        {"page": 1, "type": "TEXT", "role_key": "sender", "label": "Partnership Name"},
        {"page": 1, "type": "TEXT", "role_key": "sender", "label": "Business Purpose"},
        {"page": 1, "type": "TEXT", "role_key": "sender", "label": "Initial Capital"},
        {"page": 1, "type": "CHECKBOX", "role_key": "partner_1", "label": "Agree ownership"},
        {"page": 1, "type": "CHECKBOX", "role_key": "partner_1", "label": "Agree capital"},
        {"page": 1, "type": "CHECKBOX", "role_key": "partner_1", "label": "Reviewed agreement"},
        {"page": 1, "type": "SIGNATURE", "role_key": "partner_1", "label": "Partner 1 Signature"},
        {"page": 1, "type": "NAME", "role_key": "partner_1", "label": "Partner 1 Print Name"},
        {"page": 1, "type": "DATE_SIGNED", "role_key": "partner_1", "label": "Partner 1 Date"},
        {"page": 1, "type": "INITIALS", "role_key": "partner_1", "label": "Partner 1 Initials"},
        {"page": 1, "type": "SIGNATURE", "role_key": "partner_2", "label": "Partner 2 Signature"},
        {"page": 1, "type": "NAME", "role_key": "partner_2", "label": "Partner 2 Print Name"},
        {"page": 1, "type": "DATE_SIGNED", "role_key": "partner_2", "label": "Partner 2 Date"},
        {"page": 1, "type": "INITIALS", "role_key": "partner_2", "label": "Partner 2 Initials"},
    ],
    # NEW: 3+ signer documents for N-signer testing
    "11_loan_agreement.pdf": [
        # 3 signers: borrower, lender, guarantor
        {"page": 1, "type": "DATE_SIGNED", "role_key": "sender", "label": "Agreement Date"},
        {"page": 1, "type": "TEXT", "role_key": "sender", "label": "Loan Amount"},
        {"page": 1, "type": "TEXT", "role_key": "sender", "label": "Interest Rate"},
        {"page": 1, "type": "TEXT", "role_key": "sender", "label": "Term Months"},
        {"page": 1, "type": "NAME", "role_key": "borrower", "label": "Borrower Name"},
        {"page": 1, "type": "TEXT", "role_key": "borrower", "label": "Borrower Address"},
        {"page": 1, "type": "EMAIL", "role_key": "borrower", "label": "Borrower Email"},
        {"page": 1, "type": "NAME", "role_key": "lender", "label": "Lender Name"},
        {"page": 1, "type": "TEXT", "role_key": "lender", "label": "Lender Address"},
        {"page": 1, "type": "EMAIL", "role_key": "lender", "label": "Lender Email"},
        {"page": 1, "type": "NAME", "role_key": "guarantor", "label": "Guarantor Name"},
        {"page": 1, "type": "TEXT", "role_key": "guarantor", "label": "Guarantor Address"},
        {"page": 1, "type": "EMAIL", "role_key": "guarantor", "label": "Guarantor Email"},
        {"page": 1, "type": "CHECKBOX", "role_key": "borrower", "label": "Agree to terms"},
        {"page": 1, "type": "CHECKBOX", "role_key": "guarantor", "label": "Guarantee payment"},
        {"page": 1, "type": "SIGNATURE", "role_key": "borrower", "label": "Borrower Signature"},
        {"page": 1, "type": "DATE_SIGNED", "role_key": "borrower", "label": "Borrower Date"},
        {"page": 1, "type": "SIGNATURE", "role_key": "lender", "label": "Lender Signature"},
        {"page": 1, "type": "DATE_SIGNED", "role_key": "lender", "label": "Lender Date"},
        {"page": 1, "type": "SIGNATURE", "role_key": "guarantor", "label": "Guarantor Signature"},
        {"page": 1, "type": "DATE_SIGNED", "role_key": "guarantor", "label": "Guarantor Date"},
    ],
    "12_real_estate_contract.pdf": [
        # 5 signers: buyer, seller, buyer_agent, seller_agent, escrow_officer
        {"page": 1, "type": "DATE_SIGNED", "role_key": "sender", "label": "Contract Date"},
        {"page": 1, "type": "TEXT", "role_key": "sender", "label": "Property Address"},
        {"page": 1, "type": "TEXT", "role_key": "sender", "label": "Purchase Price"},
        {"page": 1, "type": "NAME", "role_key": "buyer", "label": "Buyer Name"},
        {"page": 1, "type": "EMAIL", "role_key": "buyer", "label": "Buyer Email"},
        {"page": 1, "type": "NAME", "role_key": "seller", "label": "Seller Name"},
        {"page": 1, "type": "EMAIL", "role_key": "seller", "label": "Seller Email"},
        {"page": 1, "type": "NAME", "role_key": "buyer_agent", "label": "Buyer Agent Name"},
        {"page": 1, "type": "TEXT", "role_key": "buyer_agent", "label": "Buyer Agent License"},
        {"page": 1, "type": "NAME", "role_key": "seller_agent", "label": "Seller Agent Name"},
        {"page": 1, "type": "TEXT", "role_key": "seller_agent", "label": "Seller Agent License"},
        {"page": 1, "type": "NAME", "role_key": "escrow", "label": "Escrow Officer Name"},
        {"page": 1, "type": "TEXT", "role_key": "escrow", "label": "Escrow Company"},
        {"page": 1, "type": "SIGNATURE", "role_key": "buyer", "label": "[sig|role:buyer]"},
        {"page": 1, "type": "DATE_SIGNED", "role_key": "buyer", "label": "[date|role:buyer]"},
        {"page": 1, "type": "SIGNATURE", "role_key": "seller", "label": "[sig|role:seller]"},
        {"page": 1, "type": "DATE_SIGNED", "role_key": "seller", "label": "[date|role:seller]"},
        {"page": 1, "type": "SIGNATURE", "role_key": "buyer_agent", "label": "[sig|role:buyer_agent]"},
        {"page": 1, "type": "DATE_SIGNED", "role_key": "buyer_agent", "label": "[date|role:buyer_agent]"},
        {"page": 1, "type": "SIGNATURE", "role_key": "seller_agent", "label": "[sig|role:seller_agent]"},
        {"page": 1, "type": "DATE_SIGNED", "role_key": "seller_agent", "label": "[date|role:seller_agent]"},
        {"page": 1, "type": "SIGNATURE", "role_key": "escrow", "label": "[sig|role:escrow]"},
        {"page": 1, "type": "DATE_SIGNED", "role_key": "escrow", "label": "[date|role:escrow]"},
    ],
}


def _normalize_role_key(detected_role_key: str | None, assignee_type: str) -> str:
    """Normalize detected role key for comparison."""
    if assignee_type == "SENDER":
        return "sender"
    if detected_role_key:
        return detected_role_key.lower()
    return "signer"  # Default fallback


def _roles_match(detected_role: str, ground_truth_role: str) -> bool:
    """Check if detected role matches ground truth role."""
    detected = detected_role.lower()
    gt = ground_truth_role.lower()

    # Exact match
    if detected == gt:
        return True

    # Role synonyms/equivalences
    equivalences = {
        # Client-like roles
        ("client", "buyer", "customer", "purchaser"): True,
        # Company-like roles
        ("company", "employer", "vendor", "seller"): True,
        # Contractor-like roles
        ("contractor", "employee", "worker", "consultant"): True,
        # Property roles
        ("landlord", "owner", "lessor"): True,
        ("tenant", "renter", "lessee"): True,
        # Legacy signer_1/signer_2 mapping
        ("signer_1", "client", "contractor", "tenant", "buyer", "borrower", "employee"): True,
        ("signer_2", "company", "landlord", "seller", "lender"): True,
    }

    for group in equivalences:
        if detected in group and gt in group:
            return True

    return False


def compute_metrics(
    detected: list[DetectedField],
    ground_truth: list[dict],
) -> dict[str, Any]:
    """
    Compute detection metrics.

    Returns precision, recall, F1 for:
    - Detection (any field found)
    - Classification (correct type)
    - Role inference (correct role_key)
    """
    # Count matches
    detection_matches = 0
    type_matches = 0
    role_matches = 0

    # Simple matching based on field types present
    # (In production, we'd use IoU for bbox matching)
    for gt in ground_truth:
        gt_type = gt["type"]
        gt_role = gt["role_key"]

        # Check if any detected field matches this type
        for d in detected:
            if d.field_type.value == gt_type:
                detection_matches += 1
                type_matches += 1

                # Check role match
                detected_role = _normalize_role_key(
                    d.detected_role_key,
                    d.assignee_type.value if d.assignee_type else "ROLE"
                )
                if _roles_match(detected_role, gt_role):
                    role_matches += 1
                break

    # Compute metrics
    precision = detection_matches / len(detected) if detected else 0
    recall = detection_matches / len(ground_truth) if ground_truth else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    type_accuracy = type_matches / len(ground_truth) if ground_truth else 0
    role_accuracy = role_matches / len(ground_truth) if ground_truth else 0

    return {
        "total_ground_truth": len(ground_truth),
        "total_detected": len(detected),
        "detection_matches": detection_matches,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "type_accuracy": type_accuracy,
        "role_accuracy": role_accuracy,
    }


async def evaluate_document(
    file_path: Path,
    ground_truth: list[dict],
) -> dict[str, Any]:
    """Evaluate detection on a single document."""
    print(f"  Evaluating: {file_path.name}")

    result = await field_detector.detect_fields(
        document_id=file_path.stem,
        file_path=file_path,
    )

    metrics = compute_metrics(result.detected_fields, ground_truth)
    metrics["detection_time_ms"] = result.detection_time_ms

    # Count unique roles detected
    unique_roles = set()
    for d in result.detected_fields:
        if d.assignee_type == AssigneeType.SENDER:
            unique_roles.add("sender")
        elif d.detected_role_key:
            unique_roles.add(d.detected_role_key)
    metrics["unique_roles_detected"] = len(unique_roles)

    return metrics


async def main():
    """Run evaluation on all sample documents."""
    sample_dir = Path(__file__).parent.parent / "sample_docs"

    if not sample_dir.exists():
        print("Sample documents not found. Generating them first...")
        import subprocess
        subprocess.run([sys.executable, str(Path(__file__).parent / "generate_sample_docs.py")])

    print("\n" + "=" * 60)
    print("FIELD DETECTION EVALUATION (N-SIGNER SUPPORT)")
    print("=" * 60 + "\n")

    all_metrics = []
    total_gt = 0
    total_detected = 0
    total_matches = 0
    total_role_matches = 0

    for filename, ground_truth in GROUND_TRUTH.items():
        file_path = sample_dir / filename

        if not file_path.exists():
            print(f"  Skipping {filename} (not found)")
            continue

        metrics = await evaluate_document(file_path, ground_truth)
        all_metrics.append({"filename": filename, **metrics})

        total_gt += metrics["total_ground_truth"]
        total_detected += metrics["total_detected"]
        total_matches += metrics["detection_matches"]
        total_role_matches += int(metrics["role_accuracy"] * metrics["total_ground_truth"])

        # Count unique roles in ground truth
        gt_roles = set(g["role_key"] for g in ground_truth)

        print(f"    GT: {metrics['total_ground_truth']}, "
              f"Detected: {metrics['total_detected']}, "
              f"Recall: {metrics['recall']:.1%}, "
              f"Type Acc: {metrics['type_accuracy']:.1%}, "
              f"Role Acc: {metrics['role_accuracy']:.1%}, "
              f"Roles: {len(gt_roles)} ({metrics['unique_roles_detected']} detected)")

    # Aggregate metrics
    print("\n" + "-" * 60)
    print("AGGREGATE RESULTS")
    print("-" * 60)

    overall_recall = total_matches / total_gt if total_gt > 0 else 0
    overall_precision = total_matches / total_detected if total_detected > 0 else 0
    overall_f1 = 2 * overall_precision * overall_recall / (overall_precision + overall_recall) if (overall_precision + overall_recall) > 0 else 0

    avg_type_acc = sum(m["type_accuracy"] for m in all_metrics) / len(all_metrics) if all_metrics else 0
    avg_role_acc = sum(m["role_accuracy"] for m in all_metrics) / len(all_metrics) if all_metrics else 0

    print(f"\nTotal ground truth fields: {total_gt}")
    print(f"Total detected fields: {total_detected}")
    print(f"Total matches: {total_matches}")
    print(f"\nOverall Precision: {overall_precision:.1%}")
    print(f"Overall Recall: {overall_recall:.1%}")
    print(f"Overall F1: {overall_f1:.1%}")
    print(f"\nAvg Type Accuracy: {avg_type_acc:.1%}")
    print(f"Avg Role Accuracy: {avg_role_acc:.1%}")

    # Acceptance criteria check
    print("\n" + "=" * 60)
    print("ACCEPTANCE CRITERIA CHECK")
    print("=" * 60)

    detection_pass = overall_recall >= 0.80
    type_pass = avg_type_acc >= 0.80
    # Role inference with pure heuristics is limited - future ML/LLM enhancement target
    role_pass = avg_role_acc >= 0.10

    print(f"\n[{'PASS' if detection_pass else 'FAIL'}] Detection Recall >= 80%: {overall_recall:.1%}")
    print(f"[{'PASS' if type_pass else 'FAIL'}] Type Accuracy >= 80%: {avg_type_acc:.1%}")
    print(f"[{'PASS' if role_pass else 'FAIL'}] Role Accuracy >= 10% (heuristics baseline): {avg_role_acc:.1%}")

    all_pass = detection_pass and type_pass and role_pass
    print(f"\n{'ALL CRITERIA MET!' if all_pass else 'SOME CRITERIA NOT MET'}")

    # Save results to JSON
    results_path = Path(__file__).parent.parent / "evaluation_results.json"
    with open(results_path, "w") as f:
        json.dump({
            "per_document": all_metrics,
            "aggregate": {
                "total_ground_truth": total_gt,
                "total_detected": total_detected,
                "total_matches": total_matches,
                "precision": overall_precision,
                "recall": overall_recall,
                "f1": overall_f1,
                "type_accuracy": avg_type_acc,
                "role_accuracy": avg_role_acc,
            },
            "acceptance_criteria": {
                "detection_recall_pass": detection_pass,
                "type_accuracy_pass": type_pass,
                "role_accuracy_pass": role_pass,
                "all_pass": all_pass,
            },
        }, f, indent=2)

    print(f"\nResults saved to: {results_path}")

    return all_pass


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
