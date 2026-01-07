#!/usr/bin/env python3
"""
Evaluate field detection accuracy on sample documents.

This script:
1. Loads sample documents with ground truth annotations
2. Runs the field detector on each document
3. Computes precision, recall, and F1 metrics
4. Generates a detailed report
"""

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

# Add the backend app to the path
sys.path.insert(0, str(Path(__file__).parent.parent / "apps" / "backend"))

from app.services.detection.detector import field_detector, BBox, DetectedField
from app.models import FieldType, FieldOwner


# Ground truth annotations for sample documents
# Format: { "filename": [{ "page": int, "type": FieldType, "owner": FieldOwner, "label": str }] }
GROUND_TRUTH = {
    "01_nda.pdf": [
        {"page": 1, "type": "DATE_SIGNED", "owner": "SENDER", "label": "Effective Date"},
        {"page": 1, "type": "NAME", "owner": "SIGNER_2", "label": "Disclosing Party"},
        {"page": 1, "type": "NAME", "owner": "SIGNER_1", "label": "Receiving Party"},
        {"page": 1, "type": "TEXT", "owner": "SENDER", "label": "Term years"},
        {"page": 1, "type": "SIGNATURE", "owner": "SIGNER_2", "label": "Company Signature"},
        {"page": 1, "type": "NAME", "owner": "SIGNER_2", "label": "Company Name"},
        {"page": 1, "type": "TEXT", "owner": "SIGNER_2", "label": "Company Title"},
        {"page": 1, "type": "DATE_SIGNED", "owner": "SIGNER_2", "label": "Company Date"},
        {"page": 1, "type": "SIGNATURE", "owner": "SIGNER_1", "label": "Contractor Signature"},
        {"page": 1, "type": "NAME", "owner": "SIGNER_1", "label": "Contractor Name"},
        {"page": 1, "type": "TEXT", "owner": "SIGNER_1", "label": "Contractor Title"},
        {"page": 1, "type": "DATE_SIGNED", "owner": "SIGNER_1", "label": "Contractor Date"},
    ],
    "02_contractor_agreement.pdf": [
        {"page": 1, "type": "NAME", "owner": "SIGNER_2", "label": "Client Name"},
        {"page": 1, "type": "EMAIL", "owner": "SIGNER_2", "label": "Client Email"},
        {"page": 1, "type": "NAME", "owner": "SIGNER_1", "label": "Contractor Name"},
        {"page": 1, "type": "EMAIL", "owner": "SIGNER_1", "label": "Contractor Email"},
        {"page": 1, "type": "TEXT", "owner": "SENDER", "label": "Scope"},
        {"page": 1, "type": "TEXT", "owner": "SENDER", "label": "Compensation"},
        {"page": 1, "type": "CHECKBOX", "owner": "SIGNER_1", "label": "Acknowledge contractor"},
        {"page": 1, "type": "CHECKBOX", "owner": "SIGNER_1", "label": "Provide equipment"},
        {"page": 1, "type": "CHECKBOX", "owner": "SIGNER_1", "label": "Responsible for taxes"},
        {"page": 1, "type": "SIGNATURE", "owner": "SIGNER_2", "label": "Client Signature"},
        {"page": 1, "type": "DATE_SIGNED", "owner": "SIGNER_2", "label": "Client Date"},
        {"page": 1, "type": "NAME", "owner": "SIGNER_2", "label": "Client Print Name"},
        {"page": 1, "type": "SIGNATURE", "owner": "SIGNER_1", "label": "Contractor Signature"},
        {"page": 1, "type": "DATE_SIGNED", "owner": "SIGNER_1", "label": "Contractor Date"},
        {"page": 1, "type": "NAME", "owner": "SIGNER_1", "label": "Contractor Print Name"},
        {"page": 1, "type": "INITIALS", "owner": "SIGNER_1", "label": "Contractor Initials"},
    ],
    "03_lease_agreement.pdf": [
        {"page": 1, "type": "DATE_SIGNED", "owner": "SENDER", "label": "Agreement Date"},
        {"page": 1, "type": "NAME", "owner": "SIGNER_2", "label": "Landlord Name"},
        {"page": 1, "type": "TEXT", "owner": "SIGNER_2", "label": "Landlord Address"},
        {"page": 1, "type": "TEXT", "owner": "SIGNER_2", "label": "Landlord Phone"},
        {"page": 1, "type": "EMAIL", "owner": "SIGNER_2", "label": "Landlord Email"},
        {"page": 1, "type": "NAME", "owner": "SIGNER_1", "label": "Tenant Name"},
        {"page": 1, "type": "TEXT", "owner": "SIGNER_1", "label": "Tenant Address"},
        {"page": 1, "type": "TEXT", "owner": "SIGNER_1", "label": "Tenant Phone"},
        {"page": 1, "type": "EMAIL", "owner": "SIGNER_1", "label": "Tenant Email"},
        {"page": 1, "type": "TEXT", "owner": "SENDER", "label": "Property Address"},
        {"page": 1, "type": "TEXT", "owner": "SENDER", "label": "Monthly Rent"},
        {"page": 1, "type": "TEXT", "owner": "SENDER", "label": "Security Deposit"},
        {"page": 1, "type": "DATE_SIGNED", "owner": "SENDER", "label": "Lease Start"},
        {"page": 1, "type": "DATE_SIGNED", "owner": "SENDER", "label": "Lease End"},
        {"page": 1, "type": "CHECKBOX", "owner": "SIGNER_1", "label": "Received lease copy"},
        {"page": 1, "type": "CHECKBOX", "owner": "SIGNER_1", "label": "Inspected property"},
        {"page": 1, "type": "CHECKBOX", "owner": "SIGNER_1", "label": "Agree to terms"},
        {"page": 1, "type": "SIGNATURE", "owner": "SIGNER_2", "label": "Landlord Signature"},
        {"page": 1, "type": "DATE_SIGNED", "owner": "SIGNER_2", "label": "Landlord Date"},
        {"page": 1, "type": "NAME", "owner": "SIGNER_2", "label": "Landlord Print Name"},
        {"page": 1, "type": "SIGNATURE", "owner": "SIGNER_1", "label": "Tenant Signature"},
        {"page": 1, "type": "DATE_SIGNED", "owner": "SIGNER_1", "label": "Tenant Date"},
        {"page": 1, "type": "NAME", "owner": "SIGNER_1", "label": "Tenant Print Name"},
    ],
    "04_employment_offer.pdf": [
        {"page": 1, "type": "DATE_SIGNED", "owner": "SENDER", "label": "Date"},
        {"page": 1, "type": "NAME", "owner": "SIGNER_1", "label": "To"},
        {"page": 1, "type": "TEXT", "owner": "SIGNER_1", "label": "Address"},
        {"page": 1, "type": "EMAIL", "owner": "SIGNER_1", "label": "Email"},
        {"page": 1, "type": "TEXT", "owner": "SENDER", "label": "Position"},
        {"page": 1, "type": "TEXT", "owner": "SENDER", "label": "Department"},
        {"page": 1, "type": "TEXT", "owner": "SENDER", "label": "Salary"},
        {"page": 1, "type": "CHECKBOX", "owner": "SIGNER_1", "label": "Health Insurance"},
        {"page": 1, "type": "CHECKBOX", "owner": "SIGNER_1", "label": "Dental Insurance"},
        {"page": 1, "type": "CHECKBOX", "owner": "SIGNER_1", "label": "401k Plan"},
        {"page": 1, "type": "CHECKBOX", "owner": "SIGNER_1", "label": "PTO"},
        {"page": 1, "type": "SIGNATURE", "owner": "SIGNER_1", "label": "Employee Signature"},
        {"page": 1, "type": "NAME", "owner": "SIGNER_1", "label": "Employee Name"},
        {"page": 1, "type": "DATE_SIGNED", "owner": "SIGNER_1", "label": "Employee Date"},
        {"page": 1, "type": "SIGNATURE", "owner": "SIGNER_2", "label": "Company Signature"},
        {"page": 1, "type": "NAME", "owner": "SIGNER_2", "label": "Company Name"},
        {"page": 1, "type": "TEXT", "owner": "SIGNER_2", "label": "Company Title"},
        {"page": 1, "type": "DATE_SIGNED", "owner": "SIGNER_2", "label": "Company Date"},
    ],
    "05_service_agreement.pdf": [
        # This document uses anchor tags [type|role]
        {"page": 1, "type": "DATE_SIGNED", "owner": "SENDER", "label": "[date|sender]"},
        {"page": 1, "type": "TEXT", "owner": "SENDER", "label": "[text|sender]"},
        {"page": 1, "type": "NAME", "owner": "SIGNER_2", "label": "[name|signer2]"},
        {"page": 1, "type": "EMAIL", "owner": "SIGNER_2", "label": "[email|signer2]"},
        {"page": 1, "type": "NAME", "owner": "SIGNER_1", "label": "[name|signer1]"},
        {"page": 1, "type": "EMAIL", "owner": "SIGNER_1", "label": "[email|signer1]"},
        {"page": 1, "type": "SIGNATURE", "owner": "SIGNER_1", "label": "[sig|signer1]"},
        {"page": 1, "type": "DATE_SIGNED", "owner": "SIGNER_1", "label": "[date|signer1]"},
        {"page": 1, "type": "SIGNATURE", "owner": "SIGNER_2", "label": "[sig|signer2]"},
        {"page": 1, "type": "DATE_SIGNED", "owner": "SIGNER_2", "label": "[date|signer2]"},
    ],
    "06_consent_form.pdf": [
        {"page": 1, "type": "NAME", "owner": "SIGNER_1", "label": "Full Name"},
        {"page": 1, "type": "DATE_SIGNED", "owner": "SIGNER_1", "label": "Date of Birth"},
        {"page": 1, "type": "EMAIL", "owner": "SIGNER_1", "label": "Email Address"},
        {"page": 1, "type": "TEXT", "owner": "SIGNER_1", "label": "Phone Number"},
        {"page": 1, "type": "CHECKBOX", "owner": "SIGNER_1", "label": "Consent to participate"},
        {"page": 1, "type": "CHECKBOX", "owner": "SIGNER_1", "label": "Understand risks"},
        {"page": 1, "type": "CHECKBOX", "owner": "SIGNER_1", "label": "Agree to data collection"},
        {"page": 1, "type": "CHECKBOX", "owner": "SIGNER_1", "label": "Can withdraw"},
        {"page": 1, "type": "CHECKBOX", "owner": "SIGNER_1", "label": "18 years old"},
        {"page": 1, "type": "SIGNATURE", "owner": "SIGNER_1", "label": "Participant Signature"},
        {"page": 1, "type": "DATE_SIGNED", "owner": "SIGNER_1", "label": "Participant Date"},
        {"page": 1, "type": "SIGNATURE", "owner": "SIGNER_2", "label": "Witness Signature"},
        {"page": 1, "type": "NAME", "owner": "SIGNER_2", "label": "Witness Name"},
        {"page": 1, "type": "DATE_SIGNED", "owner": "SIGNER_2", "label": "Witness Date"},
    ],
    "07_purchase_agreement.pdf": [
        {"page": 1, "type": "DATE_SIGNED", "owner": "SENDER", "label": "Agreement Date"},
        {"page": 1, "type": "NAME", "owner": "SIGNER_2", "label": "Seller Name"},
        {"page": 1, "type": "TEXT", "owner": "SIGNER_2", "label": "Seller Address"},
        {"page": 1, "type": "EMAIL", "owner": "SIGNER_2", "label": "Seller Email"},
        {"page": 1, "type": "NAME", "owner": "SIGNER_1", "label": "Buyer Name"},
        {"page": 1, "type": "TEXT", "owner": "SIGNER_1", "label": "Buyer Address"},
        {"page": 1, "type": "EMAIL", "owner": "SIGNER_1", "label": "Buyer Email"},
        {"page": 1, "type": "TEXT", "owner": "SENDER", "label": "Item Description"},
        {"page": 1, "type": "TEXT", "owner": "SENDER", "label": "Serial Number"},
        {"page": 1, "type": "TEXT", "owner": "SENDER", "label": "Condition"},
        {"page": 1, "type": "TEXT", "owner": "SENDER", "label": "Amount"},
        {"page": 1, "type": "TEXT", "owner": "SENDER", "label": "Payment Method"},
        {"page": 1, "type": "CHECKBOX", "owner": "SIGNER_2", "label": "Confirm ownership"},
        {"page": 1, "type": "CHECKBOX", "owner": "SIGNER_1", "label": "Inspected item"},
        {"page": 1, "type": "CHECKBOX", "owner": "SIGNER_1", "label": "Agree to terms"},
        {"page": 1, "type": "SIGNATURE", "owner": "SIGNER_2", "label": "Seller Signature"},
        {"page": 1, "type": "DATE_SIGNED", "owner": "SIGNER_2", "label": "Seller Date"},
        {"page": 1, "type": "NAME", "owner": "SIGNER_2", "label": "Seller Print Name"},
        {"page": 1, "type": "SIGNATURE", "owner": "SIGNER_1", "label": "Buyer Signature"},
        {"page": 1, "type": "DATE_SIGNED", "owner": "SIGNER_1", "label": "Buyer Date"},
        {"page": 1, "type": "NAME", "owner": "SIGNER_1", "label": "Buyer Print Name"},
    ],
    "08_release_waiver.pdf": [
        {"page": 1, "type": "NAME", "owner": "SIGNER_1", "label": "Participant Name"},
        {"page": 1, "type": "TEXT", "owner": "SIGNER_1", "label": "Address"},
        {"page": 1, "type": "TEXT", "owner": "SIGNER_1", "label": "Phone"},
        {"page": 1, "type": "EMAIL", "owner": "SIGNER_1", "label": "Email"},
        {"page": 1, "type": "TEXT", "owner": "SIGNER_1", "label": "Emergency Contact"},
        {"page": 1, "type": "TEXT", "owner": "SENDER", "label": "Event/Activity"},
        {"page": 1, "type": "DATE_SIGNED", "owner": "SENDER", "label": "Event Date"},
        {"page": 1, "type": "TEXT", "owner": "SENDER", "label": "Location"},
        {"page": 1, "type": "INITIALS", "owner": "SIGNER_1", "label": "Read and understand"},
        {"page": 1, "type": "INITIALS", "owner": "SIGNER_1", "label": "18 years old"},
        {"page": 1, "type": "INITIALS", "owner": "SIGNER_1", "label": "Good physical condition"},
        {"page": 1, "type": "SIGNATURE", "owner": "SIGNER_1", "label": "Participant Signature"},
        {"page": 1, "type": "NAME", "owner": "SIGNER_1", "label": "Participant Print Name"},
        {"page": 1, "type": "DATE_SIGNED", "owner": "SIGNER_1", "label": "Participant Date"},
    ],
    "09_power_of_attorney.pdf": [
        {"page": 1, "type": "NAME", "owner": "SIGNER_1", "label": "Principal Name"},
        {"page": 1, "type": "NAME", "owner": "SIGNER_2", "label": "Agent Name"},
        {"page": 1, "type": "TEXT", "owner": "SIGNER_2", "label": "Agent Address"},
        {"page": 1, "type": "TEXT", "owner": "SIGNER_2", "label": "Agent Phone"},
        {"page": 1, "type": "EMAIL", "owner": "SIGNER_2", "label": "Agent Email"},
        {"page": 1, "type": "CHECKBOX", "owner": "SIGNER_1", "label": "Financial matters"},
        {"page": 1, "type": "CHECKBOX", "owner": "SIGNER_1", "label": "Real estate"},
        {"page": 1, "type": "CHECKBOX", "owner": "SIGNER_1", "label": "Legal proceedings"},
        {"page": 1, "type": "CHECKBOX", "owner": "SIGNER_1", "label": "Healthcare decisions"},
        {"page": 1, "type": "CHECKBOX", "owner": "SIGNER_1", "label": "All matters"},
        {"page": 1, "type": "DATE_SIGNED", "owner": "SENDER", "label": "Effective Date"},
        {"page": 1, "type": "SIGNATURE", "owner": "SIGNER_1", "label": "Principal Signature"},
        {"page": 1, "type": "NAME", "owner": "SIGNER_1", "label": "Principal Print Name"},
        {"page": 1, "type": "DATE_SIGNED", "owner": "SIGNER_1", "label": "Principal Date"},
        {"page": 1, "type": "SIGNATURE", "owner": "SIGNER_2", "label": "Witness 1 Signature"},
        {"page": 1, "type": "NAME", "owner": "SIGNER_2", "label": "Witness 1 Name"},
        {"page": 1, "type": "DATE_SIGNED", "owner": "SIGNER_2", "label": "Witness 1 Date"},
    ],
    "10_partnership_agreement.pdf": [
        {"page": 1, "type": "NAME", "owner": "SIGNER_1", "label": "Partner 1 Name"},
        {"page": 1, "type": "TEXT", "owner": "SIGNER_1", "label": "Partner 1 Address"},
        {"page": 1, "type": "EMAIL", "owner": "SIGNER_1", "label": "Partner 1 Email"},
        {"page": 1, "type": "TEXT", "owner": "SIGNER_1", "label": "Partner 1 Ownership"},
        {"page": 1, "type": "NAME", "owner": "SIGNER_2", "label": "Partner 2 Name"},
        {"page": 1, "type": "TEXT", "owner": "SIGNER_2", "label": "Partner 2 Address"},
        {"page": 1, "type": "EMAIL", "owner": "SIGNER_2", "label": "Partner 2 Email"},
        {"page": 1, "type": "TEXT", "owner": "SIGNER_2", "label": "Partner 2 Ownership"},
        {"page": 1, "type": "TEXT", "owner": "SENDER", "label": "Partnership Name"},
        {"page": 1, "type": "TEXT", "owner": "SENDER", "label": "Business Purpose"},
        {"page": 1, "type": "TEXT", "owner": "SENDER", "label": "Initial Capital"},
        {"page": 1, "type": "CHECKBOX", "owner": "SIGNER_1", "label": "Agree ownership"},
        {"page": 1, "type": "CHECKBOX", "owner": "SIGNER_1", "label": "Agree capital"},
        {"page": 1, "type": "CHECKBOX", "owner": "SIGNER_1", "label": "Reviewed agreement"},
        {"page": 1, "type": "SIGNATURE", "owner": "SIGNER_1", "label": "Partner 1 Signature"},
        {"page": 1, "type": "NAME", "owner": "SIGNER_1", "label": "Partner 1 Print Name"},
        {"page": 1, "type": "DATE_SIGNED", "owner": "SIGNER_1", "label": "Partner 1 Date"},
        {"page": 1, "type": "INITIALS", "owner": "SIGNER_1", "label": "Partner 1 Initials"},
        {"page": 1, "type": "SIGNATURE", "owner": "SIGNER_2", "label": "Partner 2 Signature"},
        {"page": 1, "type": "NAME", "owner": "SIGNER_2", "label": "Partner 2 Print Name"},
        {"page": 1, "type": "DATE_SIGNED", "owner": "SIGNER_2", "label": "Partner 2 Date"},
        {"page": 1, "type": "INITIALS", "owner": "SIGNER_2", "label": "Partner 2 Initials"},
    ],
}


def compute_metrics(
    detected: list[DetectedField],
    ground_truth: list[dict],
) -> dict[str, Any]:
    """
    Compute detection metrics.

    Returns precision, recall, F1 for:
    - Detection (any field found)
    - Classification (correct type)
    - Owner inference (correct owner)
    """
    # Count matches
    detection_matches = 0
    type_matches = 0
    owner_matches = 0

    detected_types = [d.field_type.value for d in detected]
    gt_types = [g["type"] for g in ground_truth]

    # Simple matching based on field types present
    # (In production, we'd use IoU for bbox matching)
    for gt in ground_truth:
        gt_type = gt["type"]
        gt_owner = gt["owner"]

        # Check if any detected field matches this type
        for d in detected:
            if d.field_type.value == gt_type:
                detection_matches += 1
                type_matches += 1
                if d.owner.value == gt_owner:
                    owner_matches += 1
                break

    # Compute metrics
    precision = detection_matches / len(detected) if detected else 0
    recall = detection_matches / len(ground_truth) if ground_truth else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0

    type_accuracy = type_matches / len(ground_truth) if ground_truth else 0
    owner_accuracy = owner_matches / len(ground_truth) if ground_truth else 0

    return {
        "total_ground_truth": len(ground_truth),
        "total_detected": len(detected),
        "detection_matches": detection_matches,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "type_accuracy": type_accuracy,
        "owner_accuracy": owner_accuracy,
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

    return metrics


async def main():
    """Run evaluation on all sample documents."""
    sample_dir = Path(__file__).parent.parent / "sample_docs"

    if not sample_dir.exists():
        print("Sample documents not found. Generating them first...")
        import subprocess
        subprocess.run([sys.executable, str(Path(__file__).parent / "generate_sample_docs.py")])

    print("\n" + "=" * 60)
    print("FIELD DETECTION EVALUATION")
    print("=" * 60 + "\n")

    all_metrics = []
    total_gt = 0
    total_detected = 0
    total_matches = 0

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

        print(f"    GT: {metrics['total_ground_truth']}, "
              f"Detected: {metrics['total_detected']}, "
              f"Recall: {metrics['recall']:.1%}, "
              f"Type Acc: {metrics['type_accuracy']:.1%}, "
              f"Owner Acc: {metrics['owner_accuracy']:.1%}")

    # Aggregate metrics
    print("\n" + "-" * 60)
    print("AGGREGATE RESULTS")
    print("-" * 60)

    overall_recall = total_matches / total_gt if total_gt > 0 else 0
    overall_precision = total_matches / total_detected if total_detected > 0 else 0
    overall_f1 = 2 * overall_precision * overall_recall / (overall_precision + overall_recall) if (overall_precision + overall_recall) > 0 else 0

    avg_type_acc = sum(m["type_accuracy"] for m in all_metrics) / len(all_metrics) if all_metrics else 0
    avg_owner_acc = sum(m["owner_accuracy"] for m in all_metrics) / len(all_metrics) if all_metrics else 0

    print(f"\nTotal ground truth fields: {total_gt}")
    print(f"Total detected fields: {total_detected}")
    print(f"Total matches: {total_matches}")
    print(f"\nOverall Precision: {overall_precision:.1%}")
    print(f"Overall Recall: {overall_recall:.1%}")
    print(f"Overall F1: {overall_f1:.1%}")
    print(f"\nAvg Type Accuracy: {avg_type_acc:.1%}")
    print(f"Avg Owner Accuracy: {avg_owner_acc:.1%}")

    # Acceptance criteria check
    print("\n" + "=" * 60)
    print("ACCEPTANCE CRITERIA CHECK")
    print("=" * 60)

    detection_pass = overall_recall >= 0.80
    type_pass = avg_type_acc >= 0.80
    owner_pass = avg_owner_acc >= 0.70

    print(f"\n[{'PASS' if detection_pass else 'FAIL'}] Detection Recall >= 80%: {overall_recall:.1%}")
    print(f"[{'PASS' if type_pass else 'FAIL'}] Type Accuracy >= 80%: {avg_type_acc:.1%}")
    print(f"[{'PASS' if owner_pass else 'FAIL'}] Owner Accuracy >= 70%: {avg_owner_acc:.1%}")

    all_pass = detection_pass and type_pass and owner_pass
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
                "owner_accuracy": avg_owner_acc,
            },
            "acceptance_criteria": {
                "detection_recall_pass": detection_pass,
                "type_accuracy_pass": type_pass,
                "owner_accuracy_pass": owner_pass,
                "all_pass": all_pass,
            },
        }, f, indent=2)

    print(f"\nResults saved to: {results_path}")

    return all_pass


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)
