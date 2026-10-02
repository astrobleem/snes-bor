import sys
sys.path.insert(0, 'tools/bor_converter')
from convert_character import convert_character

pak = 'Beats of Rage Original [v.3.0 Build 4086].pak'
for ent, out in [('RALF', 'ralf'), ('JOE', 'joe'), ('JHUN', 'jhun'), ('YASHIRO', 'yashiro')]:
    entry = r'DATA\CHARS\%s\%s.TXT' % (ent, ent)
    results, moveset_path = convert_character(pak, entry, 'out/' + out)
    print(out, moveset_path)
