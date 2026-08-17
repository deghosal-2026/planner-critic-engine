"""``deploy_status`` probe (F-19): deliberate M2 stub.

Probing a deployment orchestrator's status is environment-specific (which
orchestrator, auth, rollout model) and out of scope for M2. The stub keeps the
kind dispatchable and the contract testable; it reports ``ok=False``.
"""

from __future__ import annotations

from .base import Probe, ProbeKind, ProbeRequest, ProbeResult


class DeployStatusProbe(Probe):
    """Stub — reports that deployment probing is not implemented in M2."""

    kind: ProbeKind = "deploy_status"

    def run(self, request: ProbeRequest) -> ProbeResult:
        """Return a recorded, not-run result.

        Args:
            request: The unsupported deployment query.

        Returns:
            A result with ``ok=False`` explaining the M2 stub status.
        """
        return ProbeResult(
            kind=self.kind,
            query=request.query,
            observed="deploy_status probe not implemented in M2 (stub)",
            matched=False,
            ok=False,
        )
