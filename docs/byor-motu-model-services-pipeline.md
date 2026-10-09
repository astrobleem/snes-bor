# Joined source weapon-model transition

The paired source bundle compiles all sixteen model core rows, mutable animation
and weapon caches, script/program descriptors, factors, lifecycle, attack policy,
timing and chain fields, offscreen/death fields, palette vectors and scalar
requirements. Image identities have a separate source namespace with asset
hashes. Sound identities reuse the existing frame/model/engine namespace.
Presentation and audio providers remain explicit requirements; deriving these
identities does not register the foreign profile.

The native proof derives requests from authored weapon-frame events. It calls
the real weapon selector and transition Begin, then services 1, 2, 3, 5, 6 and
7 entirely in native code. The observer writes no acknowledgements. Initial
snapshot service uses checked animation-only B5SC admission: no onmodelcopy
callback exists, so no snapshot is required. Its real Ack performs cached-model
and animation inheritance, actual entity-model copying, and weapon metadata
installation. The actual copier is privately hooked to capture the immutable
RUN tuple after successful copying. Service 2 installs alpha/style under the
actual canvas-generation check. Services 3 and 6 publish palette identity;
service 3 completes synchronized animation and restores the original type.
Service 5 copies scripts and independent factors, and service 7 completes the
closed absent-callback operation. The native timing-table loader also runs.

All 52 cases pass: 24 transitions across the two authored requests, three
physical slots, valid/out-of-range maps, authored frames and a frame-clamp
boundary; 28 stale descriptor, instance, token, variable or original-type guards.
The trace reaches `1,2,3,5,6,7,0` and done state 2 for every valid case. Stale
snapshot requests fault at service 1 before actor/cache mutation. The comparison
checks source cache inheritance, animation handles/delays, restored player type,
HP/MP clamps, exact RUN handle, lifecycle and attack/offscreen/death copies,
independent factors, palette identity, retained initialized named variables,
foreign actor rows and CPU context. The final callback service's emitted
assembly remains unchanged. Native bank 0 is byte-identical to the baseline.

The installed source pool, metadata leases, input requests and retired canvas
are fixture inputs. Authored event arguments are proven through the native
model service pipeline; actual update_frame weapon-event emission remains open.
Unsynchronized initialization requires its existing nested frame owner and is
outside this synchronized capability. This proof does not certify physical
presentation, audible playback, combat, a production MOTU boot or Demo completion.

The bounded receipt is `receipts/byor-motu-model-services-pipeline-native.json`.
Reproduce with `m4_model_services_pipeline_native.py`; its receipt contains exact
arguments and source-table/asset hashes. No production assembly, new mutable
arena storage, color reduction or PCM copies are added. No TMNT work is begun.
