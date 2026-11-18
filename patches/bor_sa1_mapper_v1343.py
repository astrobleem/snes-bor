"""Explicit opt-in SCPU SA-1 mapper for local proof models.

Grounded in local Mesen Sa1::UpdatePrgRomMappings/UpdateSaveRamMappings and
MemoryMappings::RegisterHandler. Caller MUST supply MMC and BW bank state.
Open-bus, the bank00 vector table, conversion-aware BW reads, ROM writes and unknown
windows refuse. Three native v1353 samples supply real MMC values only at
their sample points, not an attestation of continuous mapping or timing.
"""
from bor_owned_cpu_v610 import Cpu
from types import MappingProxyType


class Sa1ScpuMap:
    def __init__(self,*,banks,bw_bank,rom_size,ram_size,char_conversion=None):
        assert len(banks)==4 and all(type(v)is int and 0<=v<256 for v in banks)
        assert type(bw_bank)is int and 0<=bw_bank<32
        assert rom_size>=4096 and rom_size%4096==0
        assert ram_size>=8192 and ram_size%8192==0
        assert char_conversion is None or type(char_conversion)is bool
        # None means genuinely unknown, never an invented inactive default.
        # Conversion affects the CPU BW handler, not immutable PRG-ROM views.
        self.char_conversion=char_conversion
        self.banks=tuple(banks);self.bw_bank=bw_bank;self.rom_pages=rom_size//4096;self.ram_pages=ram_size//4096

    @classmethod
    def from_sample(cls,sample):
        """Instantiate one captured instant; confers no interval/lifetime proof."""
        state=sample['state'];prefix='cart.coprocessor.'
        return cls(banks=tuple(state[prefix+f'banks[{i}]'] for i in range(4)),
                   bw_bank=state[prefix+'cpubwbank'],rom_size=sample['rom_bytes'],
                   ram_size=sample['ram_bytes'],char_conversion=state[prefix+'charconvdmaactive'])

    def resolve(self,addr):
        assert 0<=addr<=0xffffff
        bank=addr>>16;low=addr&65535;page=low>>12;offset=low&4095
        if bank in (0x7e,0x7f):return 'wram',addr-0x7e0000
        if 0x40<=bank<=0x4f:
            return 'bwram',(((bank-0x40)*16+page)%self.ram_pages)*4096+offset
        if bank<0x40 or 0x80<=bank<0xc0:
            if low<0x2000:return 'wram',low
            if low<0x4000 and low>=0x3000:return 'iram',low&2047
            if low<0x6000:return 'io',low
            if low<0x8000:return 'bwram',((self.bw_bank*2+(page-6))%self.ram_pages)*4096+offset
            # UpdateVectorMappings wraps the whole bank00 F000 page, but
            # Sa1VectorHandler::Read delegates ordinary bytes to its ROM
            # handler. Keep the complete32-byte vector table reserved rather
            # than invent unknown native/legacy vector override state.
            if bank==0 and low>=0xffe0:raise ValueError('CPU vector table state unmodeled')
            group=0 if bank<0x20 else 1 if bank<0x40 else 2 if bank<0xa0 else 3
            control=self.banks[group]
            base=(control&7)*256 if control&128 else group*256
            page_id=base+(bank&31)*8+page-8
            return 'rom',(page_id%self.rom_pages)*4096+offset
        if bank>=0xc0:
            group=(bank-0xc0)//16;base=(self.banks[group]&7)*256
            return 'rom',((base+(bank&15)*16+page)%self.rom_pages)*4096+offset
        raise ValueError(('unqualified SCPU mapping',hex(addr)))

    def resolve_read(self,addr):
        location=self.resolve(addr)
        if location[0]=='bwram' and self.char_conversion is not False:
            raise ValueError(('BW-RAM read conversion state unknown or active',hex(addr)))
        return location

    def rom_file_span(self,addr,length):
        """Authenticate a contiguous placement span, not a free-space lease.

        Do not apply the generic LoROM file-offset formula to ROM aliases
        84..8B: that would run beyond this 4MiB image. Reject CPU-bank or file
        mirror wrapping for placement, unlike explicitly bank-wrapped DMA.
        """
        assert type(length)is int and 0<length<=65536
        assert (addr&65535)+length<=65536,'ROM placement crosses CPU bank'
        kind,start=self.resolve(addr)
        if kind!='rom':raise ValueError(('placement is not ROM',hex(addr)))
        for i in range(length):
            if self.resolve(addr+i)!=('rom',start+i):
                raise ValueError(('placement is not contiguous ROM',hex(addr+i)))
        return start,start+length


class Sa1MappedCpu(Cpu):
    def __init__(self,folder,mem=None,*,mapping):
        # Mapping registers and labels belong to this modeled CPU. Sharing
        # immutable ROM must not accidentally share mutable machine state.
        self.mapping=Sa1ScpuMap(banks=mapping.banks,bw_bank=mapping.bw_bank,
                               rom_size=mapping.rom_pages*4096,ram_size=mapping.ram_pages*4096,
                               char_conversion=mapping.char_conversion)
        super().__init__(folder,mem)
        assert isinstance(self.rom,bytes),'proof ROM must already be immutable;no hidden per-instance copy'
        assert len(self.rom)==mapping.rom_pages*4096
        self.sy=MappingProxyType(dict(self.sy))

    def phys(self,addr):
        kind,offset=self.mapping.resolve(addr)
        return {'wram':0x7e0000,'bwram':0x400000,'iram':0x003000,'io':0}.get(kind,0)+offset if kind!='rom' else addr

    def byte(self,addr):
        kind,offset=self.mapping.resolve_read(addr)
        if kind=='rom':return self.rom[offset]
        if kind=='io' and not 0x4300<=offset<0x4380:
            raise ValueError(('peripheral read not modeled;do not infer write-only MMC state',hex(offset)))
        return self.m.get(self.phys(addr),0)

    def fetch(self,n=1):
        assert 1<=n<=3
        # This opt-in class proves ROM-resident helpers only. Deliberately
        # executable worker RAM needs a separate ownership/lifetime model.
        for i in range(n):
            addr=(self.pc&0xff0000)|((self.pc+i)&65535)
            if self.mapping.resolve(addr)[0]!='rom':
                raise ValueError(('helper instruction fetch is not ROM',hex(addr)))
        value=sum(self.byte((self.pc&0xff0000)|((self.pc+i)&65535))<<(i*8) for i in range(n))
        self.pc=(self.pc&0xff0000)|((self.pc+n)&65535)
        return value

    def immutable_dma_bytes(self,addr,length):
        # DMA's source bank stays fixed while its 16-bit address increments.
        # A CPU linear read crossing a bank would hide different ROM bytes.
        assert 0<length<=65536
        values=bytearray()
        for i in range(length):
            source=(addr&0xff0000)|((addr+i)&65535)
            kind,offset=self.mapping.resolve(source)
            if kind!='rom':raise ValueError(('immutable DMA source is not ROM',hex(source)))
            values.append(self.rom[offset])
        return bytes(values)

    def write(self,addr,value,n=2):
        for i in range(n):
            kind,offset=self.mapping.resolve(addr+i)
            if kind=='rom':raise ValueError(('ROM write refused',hex(addr+i)))
            if kind=='io' and 0x2200<=offset<=0x23ff and not 0x2220<=offset<=0x2224:
                raise ValueError(('SA1 reset/interrupt/protection/conversion control not modeled',hex(offset)))
        # Only SCPU-initiated writes are modeled; SA1/HDMA need explicit actors.
        result=super().write(addr,value,n)
        for i in range(n):
            kind,offset=self.mapping.resolve(addr+i)
            v=(value>>(i*8))&255
            if kind=='io' and 0x2220<=offset<=0x2223:
                banks=list(self.mapping.banks);banks[offset-0x2220]=v;self.mapping.banks=tuple(banks)
            elif kind=='io' and offset==0x2224:self.mapping.bw_bank=v&31
        return result

    def validate_rmw_write(self,addr,n):
        # Validate ALL bytes before high-first RMW writes. In particular,
        # a word spanning ROM/WRAM must not mutate its high byte and THEN
        # discover that its low destination was ROM. No mapper/MMIO authority
        # is invented by adding one arithmetic instruction to the verifier.
        for i in range(n):
            at=(addr+i)&0xffffff
            kind,offset=self.mapping.resolve(at)
            if kind=='rom':raise ValueError(('ROM RMW write refused',hex(at)))
            if kind=='io':raise ValueError(('peripheral RMW not modeled',hex(at)))
