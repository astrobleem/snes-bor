"""Guarded903 assembly with source/generated-loan restoration."""
import build_bor_restart_v900 as build
import edit_bor_restart_dma_mask_v903 as edit

build.edit=edit
build.RUN=build.W/'BOR-RESTART-DMA-MASK-v903-build'
if __name__=='__main__':
    edit.proof()
    build.main()
