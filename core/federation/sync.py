"""
VeilCore Federation Sync Engine
=================================
Handles distributed state synchronization between federation sites.

Syncs:
    - IOC databases (new IOCs since last sync)
    - Blocklists (merged across all sites)
    - Threat bulletins (active bulletins)
    - Site status (organ health, threat levels)

Uses vector clocks for conflict resolution and
delta-sync to minimize bandwidth.
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from core.federation.protocol import (
    FederationEnvelope, FederationMessageType,
)
from core.federation.intel import ThreatIntelStore, IOC, ThreatBulletin

logger = logging.getLogger("veilcore.federation.sync")


@dataclass
class SyncState:
    """Tracks sync state with a remote site."""
    site_id: str
    last_sync: Optional[str] = None
    last_ioc_count: int = 0
    last_bulletin_count: int = 0
    sync_count: int = 0
    errors: int = 0
    vector_clock: dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "site_id": self.site_id, "last_sync": self.last_sync,
            "last_ioc_count": self.last_ioc_count,
            "last_bulletin_count": self.last_bulletin_count,
            "sync_count": self.sync_count, "errors": self.errors,
            "vector_clock": self.vector_clock,
        }


class SyncEngine:
    """
    Distributed sync engine for federation intel.

    Manages delta-synchronization of IOCs and bulletins between
    federation sites. Uses vector clocks to track what each
    site has already seen.

    Usage:
        engine = SyncEngine(intel_store, site_id="hospital-a")
        # Generate sync request for a remote site
        request = engine.create_sync_request("hospital-b")
        # Process incoming sync response
        engine.process_sync_response("hospital-b", response_data)
    """

    def __init__(self, intel_store: ThreatIntelStore, site_id: str):
        self._store = intel_store
        self._site_id = site_id
        self._sync_states: dict[str, SyncState] = {}
        self._local_clock: int = 0
        self._ioc_timestamps: dict[str, int] = {}  # ioc_id → local clock when added

    def create_sync_request(self, target_site: str) -> FederationEnvelope:
        """
        Create a sync request envelope to send to a remote site.
        Includes our vector clock so the remote can compute deltas.
        """
        state = self._get_state(target_site)

        envelope = FederationEnvelope(
            source_site=self._site_id,
            dest_site=target_site,
            msg_type=FederationMessageType.SYNC_REQUEST,
            payload={
                "requesting_site": self._site_id,
                "vector_clock": state.vector_clock,
                "last_sync": state.last_sync,
                "requesting_iocs_since": state.last_ioc_count,
                "requesting_bulletins_since": state.last_bulletin_count,
            },
        )
        return envelope

    def process_sync_request(self, source_site: str,
                              payload: dict[str, Any]) -> FederationEnvelope:
        """
        Process an incoming sync request and generate a response
        with our delta (new IOCs/bulletins the requester hasn't seen).
        """
        remote_clock = payload.get("vector_clock", {})
        remote_ioc_count = payload.get("requesting_iocs_since", 0)

        # Compute delta: IOCs they haven't seen
        new_iocs = []
        all_iocs = list(self._store._iocs.values())
        # Simple approach: send IOCs added after their last known count
        for ioc in all_iocs[remote_ioc_count:]:
            new_iocs.append(ioc.to_dict())

        # Active bulletins they may not have
        new_bulletins = []
        remote_bulletin_count = payload.get("requesting_bulletins_since", 0)
        all_bulletins = list(self._store._bulletins.values())
        for bulletin in all_bulletins[remote_bulletin_count:]:
            new_bulletins.append(bulletin.to_dict())

        # Current blocklist
        blocklist = self._store.get_blocklist()

        self._local_clock += 1

        response = FederationEnvelope(
            source_site=self._site_id,
            dest_site=source_site,
            msg_type=FederationMessageType.SYNC_RESPONSE,
            payload={
                "responding_site": self._site_id,
                "vector_clock": {self._site_id: self._local_clock},
                "new_iocs": new_iocs,
                "new_bulletins": new_bulletins,
                "blocklist": blocklist,
                "total_iocs": len(self._store._iocs),
                "total_bulletins": len(self._store._bulletins),
                "sync_timestamp": datetime.now(timezone.utc).isoformat(),
            },
        )
        return response

    def process_sync_response(self, source_site: str,
                               payload: dict[str, Any]) -> dict[str, int]:
        """
        Process a sync response: merge new IOCs and bulletins
        into our local intel store.
        Returns counts of items merged.
        """
        state = self._get_state(source_site)
        merged = {"iocs": 0, "bulletins": 0, "blocked_ips": 0, "blocked_domains": 0}

        # Merge IOCs
        new_iocs = payload.get("new_iocs", [])
        for ioc_data in new_iocs:
            try:
                ioc = IOC.from_dict(ioc_data)
                if not ioc.source_site:
                    ioc.source_site = source_site
                self._store.add_ioc(ioc)
                merged["iocs"] += 1
            except Exception as e:
                logger.debug(f"Failed to merge IOC: {e}")

        # Merge bulletins
        new_bulletins = payload.get("new_bulletins", [])
        for b_data in new_bulletins:
            try:
                bulletin = ThreatBulletin.from_dict(b_data)
                self._store.add_bulletin(bulletin)
                merged["bulletins"] += 1
            except Exception as e:
                logger.debug(f"Failed to merge bulletin: {e}")

        # Merge blocklist
        blocklist = payload.get("blocklist", {})
        for ip in blocklist.get("ips", []):
            if ip not in self._store._blocklist_ips:
                self._store._blocklist_ips.add(ip)
                merged["blocked_ips"] += 1
        for domain in blocklist.get("domains", []):
            if domain not in self._store._blocklist_domains:
                self._store._blocklist_domains.add(domain)
                merged["blocked_domains"] += 1

        # Update sync state
        remote_clock = payload.get("vector_clock", {})
        state.vector_clock.update(remote_clock)
        state.last_sync = datetime.now(timezone.utc).isoformat()
        state.last_ioc_count = payload.get("total_iocs", state.last_ioc_count)
        state.last_bulletin_count = payload.get("total_bulletins", state.last_bulletin_count)
        state.sync_count += 1

        # Persist
        self._store.save()

        logger.info(
            f"Sync with '{source_site}' complete | "
            f"Merged: {merged['iocs']} IOCs, {merged['bulletins']} bulletins, "
            f"{merged['blocked_ips']} IPs, {merged['blocked_domains']} domains"
        )
        return merged

    def _get_state(self, site_id: str) -> SyncState:
        """Get or create sync state for a site."""
        if site_id not in self._sync_states:
            self._sync_states[site_id] = SyncState(site_id=site_id)
        return self._sync_states[site_id]

    def get_sync_summary(self) -> dict[str, Any]:
        """Get summary of all sync states."""
        return {
            "local_site": self._site_id,
            "local_clock": self._local_clock,
            "remote_sites": {
                sid: state.to_dict() for sid, state in self._sync_states.items()
            },
            "store_summary": self._store.summary(),
        }
