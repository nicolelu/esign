"""Audit service for tamper-evident event logging."""

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AuditEvent, AuditEventType


class AuditService:
    """Service for managing audit events."""

    async def log_event(
        self,
        db: AsyncSession,
        envelope_id: str,
        event_type: AuditEventType,
        actor_id: str | None = None,
        actor_email: str | None = None,
        actor_role: str | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
        data: dict[str, Any] | None = None,
    ) -> AuditEvent:
        """
        Log an audit event with tamper-evident hashing.

        Each event includes a hash of the previous event to create
        a chain that can detect tampering.
        """
        timestamp = datetime.now(timezone.utc)

        # Get the previous event's hash for chaining
        previous_event = await self._get_last_event(db, envelope_id)
        previous_hash = previous_event.event_hash if previous_event else None

        # Create the event
        event = AuditEvent(
            envelope_id=envelope_id,
            event_type=event_type,
            timestamp=timestamp,
            actor_id=actor_id,
            actor_email=actor_email,
            actor_role=actor_role,
            ip_address=ip_address,
            user_agent=user_agent,
            data=data,
            previous_event_hash=previous_hash,
        )

        # Compute hash of this event
        event.event_hash = self._compute_event_hash(event)

        db.add(event)
        await db.commit()
        await db.refresh(event)

        return event

    async def _get_last_event(
        self,
        db: AsyncSession,
        envelope_id: str,
    ) -> AuditEvent | None:
        """Get the most recent event for an envelope."""
        result = await db.execute(
            select(AuditEvent)
            .where(AuditEvent.envelope_id == envelope_id)
            .order_by(AuditEvent.timestamp.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    def _compute_event_hash(self, event: AuditEvent) -> str:
        """Compute SHA-256 hash of event data for tamper detection."""
        # Create a deterministic string representation
        hash_data = {
            "envelope_id": event.envelope_id,
            "event_type": event.event_type.value,
            "timestamp": event.timestamp.isoformat(),
            "actor_id": event.actor_id,
            "actor_email": event.actor_email,
            "actor_role": event.actor_role,
            "ip_address": event.ip_address,
            "data": event.data,
            "previous_event_hash": event.previous_event_hash,
        }

        hash_string = json.dumps(hash_data, sort_keys=True, default=str)
        return hashlib.sha256(hash_string.encode()).hexdigest()

    async def get_audit_trail(
        self,
        db: AsyncSession,
        envelope_id: str,
    ) -> list[AuditEvent]:
        """Get all audit events for an envelope in chronological order."""
        result = await db.execute(
            select(AuditEvent)
            .where(AuditEvent.envelope_id == envelope_id)
            .order_by(AuditEvent.timestamp.asc())
        )
        return list(result.scalars().all())

    async def verify_audit_trail(
        self,
        db: AsyncSession,
        envelope_id: str,
    ) -> tuple[bool, list[str]]:
        """
        Verify the integrity of the audit trail.

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        events = await self.get_audit_trail(db, envelope_id)
        errors = []

        for i, event in enumerate(events):
            # Verify hash chain
            if i == 0:
                if event.previous_event_hash is not None:
                    errors.append(
                        f"Event {event.id}: First event should have no previous hash"
                    )
            else:
                expected_previous_hash = events[i - 1].event_hash
                if event.previous_event_hash != expected_previous_hash:
                    errors.append(
                        f"Event {event.id}: Previous hash mismatch "
                        f"(expected {expected_previous_hash}, "
                        f"got {event.previous_event_hash})"
                    )

            # Verify event hash
            computed_hash = self._compute_event_hash(event)
            if event.event_hash != computed_hash:
                errors.append(
                    f"Event {event.id}: Hash mismatch "
                    f"(expected {computed_hash}, got {event.event_hash})"
                )

        return len(errors) == 0, errors


# Singleton instance
audit_service = AuditService()
