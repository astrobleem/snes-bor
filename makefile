PYTHON ?= python3
POPPY ?= poppy
TAD_COMPILER ?=
TAD_ARGS = $(if $(TAD_COMPILER),--compiler "$(TAD_COMPILER)",)

all: build/bor.sfc

tad-check:
	$(PYTHON) soundwork/tad/rebuild.py --check $(TAD_ARGS)

src/main.bin: src/main.pasm soundwork/tad/build/audio-data.bin soundwork/tad/build/tad_blob_syms.pasm
	$(POPPY) src/main.pasm -s src/main.sym

build/bor.sfc: tad-check src/main.bin build_rom.py
	$(PYTHON) build_rom.py

clean:
	rm -rf build distribution src/main.bin src/main.pansy src/main.sym

.PHONY: all clean tad-check
