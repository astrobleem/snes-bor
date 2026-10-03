#!/usr/bin/env python3
"""G3 compatibility entry point for the accepted P1-L2 death contract.

The former G3 assertions covered the pre-fidelity synthetic contract
(immediate respawn, 90-frame invulnerability, and a 300-frame continue).
Those checks are deferred to P1-L3. The source death/respawn assertions now
live in game_bor_death_respawn.py so existing G3 invocations cannot silently
run the obsolete semantics.
"""
from game_bor_death_respawn import main


if __name__ == '__main__':
    main()
