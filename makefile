PYTHON ?= python3
DOTNET ?= C:/Users/chad/.dotnet/dotnet.exe
POPPY_DLL ?= E:/gh/poppy-astrobleem/src/Poppy.CLI/bin/Release/net10.0/poppy.dll
TAD_COMPILER ?=
TAD_ARGS = $(if $(TAD_COMPILER),--compiler "$(TAD_COMPILER)",)
AUDIO_CATALOG = tools/audio/music_catalog.json

all: build/bor.sfc

tad-check:
	$(PYTHON) soundwork/tad/rebuild.py --check $(TAD_ARGS)

audio-manifest:
	$(PYTHON) tools/audio/build_audio.py

audio-ids audio-music: audio-manifest

src/main.bin: audio-ids src/main.pasm soundwork/tad/build/audio-data.bin soundwork/tad/build/tad_blob_syms.pasm tools/audio/audio_music_ids.pasm
	$(DOTNET) $(POPPY_DLL) src/main.pasm -s src/main.sym

build/bor.sfc: tad-check audio-music src/main.bin build_rom.py
	$(PYTHON) build_rom.py

clean:
	rm -rf build distribution src/main.bin src/main.pansy src/main.sym

.PHONY: all clean tad-check audio-manifest audio-ids audio-music
