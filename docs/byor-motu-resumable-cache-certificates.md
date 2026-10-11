# Resumable fixed-bank cache cuts

The cache-guided bank solver retains sparse LP dual certificates and evaluated
assignments. `--resume-report` requires the same source-word/geometry basis,
eligibility domains and objective. It checks dual signs, domains and
stationarity before reinstating a cut. The unbounded peak column is normalized
inward; any finite-column negative residual is charged against the constant.
Integer cut coefficients and constants are rounded outward. Saved claims or
reported residuals alone are never accepted as a certificate.

The incumbent is rechecked once on resume. Other evaluated assignments stay
excluded, preventing a resumed search from repeating them. Optional changes
to neighborhood size retain valid cache cuts because the cache model itself
has not changed. CLI output summarizes progress; complete certificates remain
in the schedule artifact.

Ten authored peak runs retain 324 certificates and 315 unique evaluated bank
assignments. The second run restores 34 certificates; the tenth restores 307.
Independent source-word and bank-eligibility replay matches every piece. The
best assignment-specific fractional clock bound improves from 359.650 to
353.923, above the demonstrated 344-clock constant-control window. The
searches do not prove a universal
raster limit and do not admit an integer or physical transfer schedule.
The compressed receipt retains the final complete schedule and cumulative
certificates, with hashes and summaries of the preceding runs. Repeated copies
of the same restored certificates are omitted.

Optional `--interval-cut-span` strengthens the bank master using each bank's
union of required identities over a scanline interval. Shared words are ORed
before counting; each bank may start with fifteen resident words. The clock
bound grants the same favorable fractional active-bank and bridge behavior as
the cache LP. Each evaluated assignment independently replays these bounds
against its LP optimum. Changing these redundant master bounds preserves the
cache basis and permits reuse of the existing dual certificates.
The tenth run installs 192 interval bounds, each replayed against the cache
LP. Its unrestricted master lower bounds are positive, ranging from 111.671
to 199.759 clocks in the retained iterations. They remain below the hardware
target; this is not a global raster rejection.

Twenty-six focused decomposition, bank-cache, interval-cache and bank-class
tests pass, including interval bounds with resumed cuts, resumed cut reuse,
changed-source rejection, malformed dual rejection and illegal assignment
rejection. The width audit has 9825 labels and zero failures. All 17 protected
file hashes match. Source RGB555 words and exact source SCREEN semantics are
preserved; no color reduction is applied. Authored native peak and production
MOTU completion remain open.
