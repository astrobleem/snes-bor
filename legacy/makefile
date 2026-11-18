POPPY = /home/chad/poppy/src/Poppy.CLI/bin/Release/net10.0/poppy.dll
DOTNET = DOTNET_ROOT=/home/chad/.dotnet10 PATH="/home/chad/.dotnet10:$$PATH"
TAD_COMPILER = /home/chad/terrific-audio-driver/target/release/tad-compiler

all: build/bor.sfc

soundwork/tad/build/audio-data.bin:
	mkdir -p soundwork/tad/build
	$(TAD_COMPILER) ca65-export --lorom --segment AUDIO0 \
		--output-asm soundwork/tad/build/audio-data.s \
		--output-bin soundwork/tad/build/audio-data.bin \
		--output-inc soundwork/tad/build/audio-enums.inc \
		/home/chad/supermn-snes/soundwork/tad/mml_drafts/02_coin.terrificaudio

soundwork/tad/build/tad_blob_syms.pasm: soundwork/tad/build/audio-data.s soundwork/tad/build/audio-data.bin
	python3 soundwork/tad/tools/gen_blob_syms.py

src/main.bin: src/main.pasm soundwork/tad/build/audio-data.bin soundwork/tad/build/tad_blob_syms.pasm
	$(DOTNET) dotnet $(POPPY) src/main.pasm

build/bor.sfc: src/main.bin build_rom.py
	mkdir -p build distribution
	python3 build_rom.py

clean:
	rm -rf build distribution soundwork/tad/build src/main.bin src/main.pansy

.PHONY: all clean
