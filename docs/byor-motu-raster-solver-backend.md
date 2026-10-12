# Raster solver backend and interrupted hint repair

The offline palette solver encountered OR-Tools' native assertion
`heuristics.fixed_search != nullptr` in the split-assignment hint fixture.
The assertion reproduces with both released 9.15.6755 and unmodified upstream
commit `5fa45709e844303a41dc15c7bee0ebf049d4e844`. The
[upstream issue](https://github.com/google/or-tools/issues/5025) therefore does
not establish that this particular path is fixed.

`MinimizeL1DistanceWithHint` copies the shared stopping condition into a local
model. `LoadCpModel` can return when that condition becomes true, before search
heuristics are constructed. The repair path then calls
`ConfigureSearchHeuristics` without checking that loading was interrupted.
The retained [patch](../tools/verify/patches/ortools-cache-hint-time-limit.patch)
checks the local time limit after loading and returns before configuring search
when it has stopped. It changes neither constraints nor solution admission.
Apply this zero-context patch with `git apply --unidiff-zero`; reverse-apply
validation confirms that it matches the guarded source checkout.

The patched isolated build passes 24 focused bank/cache/interval tests and
20 repetitions of the previously crashing fixture, with zero failures or
errors. The installed core DLL is checked byte-for-byte against the wheel.
The [receipt](receipts/byor-motu-raster-solver-backend.json) pins the upstream
commit, patch hash, wheel hash, installed DLL hash, versions, build settings
and bounded verification. This is evidence for the tested repair path, not
an assertion that every solver defect is resolved.

The isolated Python 3.10 environment remains under
`out/byor-motu-ortools-main-venv`. The source build uses Visual Studio 18,
Release configuration, `CL=/MP4`, and two concurrent MSBuild projects.
Gurobi and Xpress retain their upstream supported dynamic-interface defaults;
MathOpt and PDLP are enabled because this pinned Python package generator
requires their targets. SCIP, CoinOR and the embedded HiGHS backend are disabled.
Palette MILP verification uses the separate `highspy` installation.

No production runtime assembly, source artwork or source palette is changed
by this backend repair. Hardware feasibility and MOTU completion remain open.
No color reduction is applied.
