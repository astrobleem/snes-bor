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

Three authored peak runs retain 74 certificates and 72 unique evaluated bank
assignments. The second run restores 34 certificates; the third restores 54.
Independent source-word and bank-eligibility replay matches every piece. The
best assignment-specific fractional clock bound remains 359.650, above the
demonstrated constant-control window. The searches do not prove a universal
raster limit and do not admit an integer or physical transfer schedule.

Twenty-seven focused bank/cache tests pass, including resumed cut reuse,
changed-source rejection, malformed dual rejection and illegal assignment
rejection. The width audit has 9825 labels and zero failures. All 17 protected
file hashes match. Source RGB555 words and exact source SCREEN semantics are
preserved; no color reduction is applied. Authored native peak and production
MOTU completion remain open.
