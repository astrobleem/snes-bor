# Model transition resets the independent active palette

The native colour services now optionally reset the independent active palette owner/map before the real model-transition acknowledgement. Service 6 proceeds to service 7; service 3 continues through the existing synchronized animation owner. The generic palette service retains its existing emitted path when the current-palette capability is absent.

The reset accepts a legitimate transitional BODY owner and active row belonging to the old model, checks the actual transition slot, old/new models, side/core addresses and service, validates the old active index against its owner's palette count, and normalizes the restore index against the new model. A second reset before acknowledgement accepts the already published new owner. Invalid leases and identities reject before palette/entity publication. The synchronized animation failure retains the earlier source-ordered palette publication.

The isolated native proof passed 399 service-6 cases and 451 service-3 cases, including two observed reset calls for every accepted publication. The final legacy birth/select/read/restore regression passed all 1,046 cases. Observers compare actor, BODY, palette, hit and complete CHR staging bytes and CPU context; bank 0 remains unchanged. The [receipt](receipts/byor-motu-model-current-palette-reset.json) records hashes and retained traces.

This phase-8 join does not bind the full model transition, nested callback control preservation, production memory ownership or CGRAM presentation. The BODY restore index still has the documented closed uint16 producer domain. MOTU gameplay and Demo completion remain unproven. No color reduction was applied; no PCM copies were made.
