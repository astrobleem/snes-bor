; 365 exact immutable Kula source blocks; source catalog SHA is pinned by generator.
.bank 52
.org $8000
SourceRom_Ids:
    .incbin "bor_rom_block_ids.bin"
.bank 53
.org $8000
SourceRom_Payload35:
    .incbin "bor_rom_payload_35.bin"
.bank 54
.org $8000
SourceRom_Payload36:
    .incbin "bor_rom_payload_36.bin"
.bank 55
.org $8000
SourceRom_Payload37:
    .incbin "bor_rom_payload_37.bin"

; Direct ID -> immutable payload index+1; zero is an explicit miss.
.bank 56
.org $8000
SourceRom_Dense38:
    .incbin "bor_rom_dense_38.bin"
.bank 57
.org $8000
SourceRom_Dense39:
    .incbin "bor_rom_dense_39.bin"
