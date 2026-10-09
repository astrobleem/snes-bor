# Admitted source audio through native BRR and live SPC

The actual source sound selector and retained admission now feed the PCM8 worker, packed predictive BRR encoder and unchanged production SPC transport in one private ROM. All 30 verified PCM assets and the compact lookup tables coexist in ROM. The proof exercises pain and klunk at their pinned channel-dependent initial phases, with no phase override.

The synchronous join produces 33,088 exact stereo PCM bytes and 4,653 exact BRR bytes across 47 jobs. It retains exact ending activity, phase, source identity and play identity. Its peak job cost is 257,214 master clocks. Bank 0 remains identical. See the [join receipt](receipts/byor-motu-sound-admission-brr-native.json).

The live proof starts after two native jobs, uses one transport prefill chunk, then observes 45 later jobs while the production SPC consumes the mixture. All 33 packets, including final padding, match; all 517 DSP blocks occur exactly once with matching headers and fingerprints. Channel state and the completed native PCM/BRR gate also match. Native buffer clearing supplies final-packet padding. See the [live receipt](receipts/byor-motu-source-admission-live-spc-native.json).

Both native workers share IRAM at $3500 through bounded code DMA. The live gather is 459 bytes; the patched live encoder is 667 bytes. Its pacing and row synchronization execute in the private fixture bank. The private audio wait hook changes only three operand bytes in existing bank-0 code; it adds no bank-0 code. These are isolated measurements, not a gameplay scheduling budget.

Earlier failed harness attempts remain classified FAIL. The final proof does not bind a source frame's sound ticket or acknowledgement, establish reusable production memory ownership, combine live graphics with audio, or prove MOTU gameplay. Dynamic sound replacement and long streams still require production ownership and a bounded output ring. The previously declared mono/11025/PCM8 and predictive-BRR audio adaptation remains explicit. No color reduction or PCM media copies occurred.
