"""``db_query`` probe (F-19): deliberate M2 stub.

A read-only database query probe is a real integration surface (driver per DB,
connection lifecycle, auth) that is out of scope for M2. The stub exists so the
contract is testable and the kind is dispatchable; it reports ``ok=False`` with
a clear message rather than pretending to run.
"""

from __future__ import annotations

from .base import Probe, ProbeKind, ProbeRequest, ProbeResult


class DbQueryProbe(Probe):
    """Stub — reports that DB probing is not implemented in M2."""

    kind: ProbeKind = "db_query"

    def run(self, request: ProbeRequest) -> ProbeResult:
        """Return a recorded, not-run result.

        Args:
            request: The unsupported query.

        Returns:
            A result with ``ok=False`` explaining the M2 stub status.
        """
        return ProbeResult(
            kind=self.kind,
            query=request.query,
            observed="db_query probe not implemented in M2 (stub)",
            matched=False,
            ok=False,
        )
