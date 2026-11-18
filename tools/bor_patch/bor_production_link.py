from bor_sa1_mapper_v1343 import Sa1ScpuMap

def mapping():return Sa1ScpuMap(banks=(0,1,2,3),bw_bank=0,rom_size=4194304,ram_size=262144)

def read(raw,at,n):
 a,b=mapping().rom_file_span(at,n)
 if b>len(raw):raise ValueError('compiled/retained input truncated')
 return raw[a:b]
