# Normal campaign integration provenance

This integration imports the reviewed final content as a single squash-import commit whose parent is current GitHub `master`. The unrelated review-snapshot history and original development history are not attached, rewritten, or discarded.

- GitHub `master` base: `55c0f3db217b30dac0646d75f905617a13b3b067`; it is an ancestor of the reviewed source base, with no independent master-only changes at integration start.
- Accepted review snapshot: `c1e902e4cc5532da201f187ec8d57804f12bbe9b`.
- Original reviewed source revisions: base `6bf609890563aa93835266213632b81f4c0b3723`; final `f20073b4ece3c6a0a1ad895aca1f49f33ff2aff2`; follow-up evidence/reconstruction commits `ae7afde76c8c26681c70360567aff950e8f18ebe` and `61c48d45727e2bdb5fb6a3fa1e5b92ee353c9595`.
- Reviewed generated catalog restored from the committed `f20073b4` tree: `src/generated/production_source_visual.json`, 114,194,902 bytes, SHA-256 `c130dcda94090cf147e41995f5500f9222c793aabf466e68ac3a0084fa6ee22e`. It is represented by one Git LFS pointer; the narrow LFS rule applies only to this path.
- Comparison against the accepted review-tip tree found all 4,152 retained paths identical in blob ID and mode (including executable mode). The only tree additions are this note, the one-path `.gitattributes` rule, and the catalog LFS pointer.
- Verifier status remains `SOURCE_RECONSTRUCTED_OFFLINE`, not full campaign-equivalence certification. Historical campaign receipts remain bound to their recorded ROM/MSU hashes. Runtime review repairs were accepted; this import does not establish new campaign acceptance, manual combat/visual acceptance, or a newly validated release ROM.
- No campaign run, ROM build, Mesen session, or catalog regeneration was performed for integration.
