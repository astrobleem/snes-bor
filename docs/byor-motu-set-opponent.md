# BOR 4086 opponent assignment

The generic `set_opponent` service resolves each physical owner chain and then performs the four source assignments in order. NULL entities, NULL opponents, shared roots and aliases preserve the pinned source behavior. Dead entities with valid tokens remain valid owner nodes.

The unchanged pinned engine function passes 4,588 C cases. The native phase 8 helper passes 661 cases, observing all 128 opponent rows, unrelated actor fields, the pending world phase and CPU context. Stale generation, malformed owner pointers, cycles, missing relation markers and incorrect stored entity tokens reject before any opponent write. The source pointer resolver alone does not check the stored token; this helper does.

The initial native proof failed at the malformed entity-token case. That failure remains in `out/byor-motu-set-opponent-native`; the corrected run is `out/byor-motu-set-opponent-native-token-corrected`. The bounded [receipt](receipts/byor-motu-set-opponent-native.json) records report and observer hashes.

The caller must lease 24 serialized bytes in the foreign workspace. This isolated proof borrows the attack-chain control region; the production workspace union remains unbound. The helper does not accept damage or acknowledge the world phase. Bank 0 remains byte-identical to the repaired baseline, with two bytes free. No color reduction or PCM copying was applied. This component proof does not certify MOTU gameplay or Demo completion.
