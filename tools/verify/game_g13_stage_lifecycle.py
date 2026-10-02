#!/usr/bin/env python3
"""Compatibility entry point for source lifecycle gates.

P1-L2/L3/L4 own death, re-entry, and terminal semantics. The former
synthetic GAMEOVER continuation assertions are intentionally not retained.
"""
from game_bor_gameover import main


if __name__ == '__main__':
    main()
