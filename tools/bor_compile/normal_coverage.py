"""Fail-closed Normal source inventory, never a native/runtime certificate.

Default CLI success means the structural inventory and in-memory lowering
completed, including explicitly reported compatibility gaps. --require-native
fails until separate native evidence exists; this tool accepts no PASS override.
No emulator, asset generation, build, or shared-file writes. JSON goes to stdout.
"""
from __future__ import annotations

import argparse
import ast
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import sys

from compiler import ROOT, Source, key, model_catalog, project, scene, stage

PAK = ROOT / 'Beats of Rage Original [v.3.0 Build 4086].pak'
CAMPAIGN = 'BOR_NORMAL_1A_INTERNAL'


class CoverageError(ValueError):
    pass


def rule(lowering, consumer, adapter, limitation=''):
    return dict(lowering=lowering.split(), consumer=consumer.split(),
                compatibility_adapter=adapter, native_limitation=limitation)


QUEUE = 'tools/bor_compile/environment_semantics.py#lower_map_queue tools/bg_converter/build_spawn_table.py#convert_events'
SPAWN = 'src/core/spawn.pasm#Spawn_Play'
LINK = 'tools/bor_compile/production_campaign.py#link_campaigns build_rom.py#write_campaign_include'
RESOLVE = 'src/core/campaign.pasm#Game_Campaign_ResolveNext'
MEDIA = 'tools/bor_compile/production_campaign.py#complete_presentation tools/bg_converter/convert_bg.py#convert_streaming'

# Independent of compiler.CAPABILITIES: adding a parser keyword cannot silently
# promote it here. Each rule names executable lowering and consumer definitions.
# Definition presence is traceability, NOT call-path, assembled-ROM or live proof.
RULES = {
    ('project', 'set'): rule(LINK, RESOLVE + ' src/core/set_select.pasm#BorSetSelect_Play src/core/campaign.pasm#BorSet_BeginSelectedRun', 'Source set identity -> legacy campaign ABI 3; CHARSELECT difficulty input validates selectable gates, new-run reset resolves the selected first typed entry.'),
    ('project', 'file'): rule(LINK, RESOLVE + ' src/core/game_state.pasm#Stage_Load', 'Source order -> typed entry -> physical catalog; legacy ID pins.'),
    ('project', 'scene'): rule(LINK, 'src/core/campaign.pasm#Game_Campaign_DispatchResolved src/core/scene_video.pasm#SceneVideo_Request', 'Registered scene IDs; compatibility scene continuation returns to typed dispatcher.'),
    ('project', 'next'): rule(LINK, 'src/core/campaign.pasm#Game_Campaign_HasNextFlag src/core/ending.pasm#StageComplete_Dispatch', 'Source next_after -> NextFlags; no next means direct dispatch, not a completion bonus.'),
    ('stage', 'background'): rule(MEDIA, 'src/core/game_state.pasm#Stage_Load', 'Content-hashed accepted flattened BG1 media, 320 -> 256 horizontal scaling; not independent source layers.'),
    ('stage', 'panel'): rule(MEDIA, 'src/core/game_state.pasm#Stage_Load', 'Ordered source panels flattened into accepted streamed BG1 tiles; quantized palette/tile budget.'),
    ('stage', 'order'): rule(MEDIA, 'src/core/game_state.pasm#Stage_Load', 'Concatenated authored order determines panel composition and width; logical campaign order remains independent.'),
    ('stage', 'frontpanel'): rule('tools/bor_compile/production_campaign.py#complete_presentation tools/bor_compile/stage_frontpanel.py#sequence_directives tools/bor_compile/stage_frontpanel.py#materialize_normal tools/bor_compile/stage_frontpanel.py#lower_bg2 tools/bor_compile/stage_frontpanel_bg2.py#materialize_normal tools/bor_compile/stage_frontpanel_bg2.py#motion_tables tools/bor_compile/stage_frontpanel_bg2.py#encode_clean_background tools/bor_compile/stage_frontpanel_bg2.py#validate_bg2 build_rom.py#prepare_stage_environment_assets tools/bg_converter/convert_frontpanel.py#composite_frontpanel_sequence', 'src/core/stage_frontpanel_bg2.pasm#StageFp_BG2ColdInit src/core/stage_frontpanel_bg2.pasm#StageFp_BG2SceneReset src/core/stage_frontpanel_bg2.pasm#StageFp_BG2BootDispatch src/core/stage_frontpanel_bg2.pasm#StageFp_BG2PlayDispatch src/core/stage_frontpanel_bg2.pasm#StageFp_BG2CommitDispatch src/core/stage_frontpanel_bg2.pasm#StageFp_BG2OamAttr', 'Normal ordered full-height BG2 4bpp foreground, clean BG1 materialization, bounded column cache and 7/5 camera adapter; Easy legacy path retained.', 'Compiler and main/NMI hooks are checked statically. Native scrolling, layer priority, resource contention, transitions and pixel acceptance remain PENDING_NATIVE.'),
    ('stage', 'direction'): rule('tools/bg_converter/build_spawn_table.py#convert_events build_rom.py#write_stage_scroll_include', 'src/core/spawn.pasm#Spawn_Play__compare_trigger src/core/game_state.pasm#Game_State_Play__stage_check_edge', 'Explicit right/left/down camera and queue transforms at 4/5 scale; native float fractions are lost.'),
    ('stage', 'music'): rule('tools/audio/generate_audio_music_ids.py#main', 'src/core/audio_music.pasm#Music_SelectStageTrack', 'Source asset -> stage-indexed MSU PCM track; stage loop is explicit 1.'),
    ('stage', 'bossmusic'): rule('tools/audio/generate_audio_music_ids.py#main', 'src/core/audio_music.pasm#Music_SelectBossTrack', 'Authored boss track -> stage boss table; triggered by identified boss activation.'),
    ('stage', 'hole'): rule(QUEUE, 'src/core/spawn.pasm#Spawn_Play__do_hole src/core/spawn.pasm#Spawn_CheckHole', 'Three fixed hole prefix records, 4/5-scaled coordinates, compatibility hole consumer.', 'Fixed hazard capacity and integer geometry are not general native hole behavior.'),
    ('stage', 'blocked'): rule('tools/bor_compile/stage_bounds.py#from_ir tools/bor_compile/stage_bounds.py#emit_pasm', 'src/core/stage_bounds.pasm#StageBounds_Clamp src/core/stage_bounds_host.pasm#StageBoundsHost_Clamp', 'S8 Normal ACCEPTED_COMPAT inverse-scale depth-dependent clamp.', 'Native movement/lifecycle fidelity needs host integration and live evidence; metadata alone is insufficient.'),
    ('stage', 'endhole'): rule('tools/bor_compile/stage_bounds.py#from_ir tools/bor_compile/stage_bounds.py#emit_pasm', 'src/core/stage_bounds.pasm#StageBounds_CheckEndHole src/core/stage_bounds_host.pasm#StageBoundsHost_Physics', 'S8 integer-coordinate pit adapter with separate gravity/lifecycle host.', 'Pit damage, retirement, actor reuse and player lives need native runtime evidence.'),
    ('stage', 'water'): rule('tools/bor_compile/stage_water.py#bind tools/bor_compile/stage_water.py#composite tools/bor_compile/stage_water.py#emit_tables', 'src/core/stage_water.pasm#StageWater_Begin src/core/stage_water.pasm#StageWater_Nmi', 'S8_FLATTENED_BG1_BOUNDED_RASTER_V1, amplitudes 2/15, host-double LUT and 60Hz presentation clock.', 'Bounded flattened raster adaptation is not native texture/parallax or hardware visual acceptance.'),
    ('stage', 'rock'): rule('tools/bor_compile/stage_water.py#bind tools/bor_compile/stage_water.py#phases', 'src/core/stage_water.pasm#StageWater_Begin src/core/stage_water.pasm#StageWater_ApplyOamY', 'Shared bounded BG1/OAM rocking adapter, source-phase lookup at declared 60Hz.', 'Source layer motion and hardware presentation remain unverified.'),
    ('stage', 'mirror'): rule('build_rom.py#write_stage_scroll_include', 'src/core/jump.pasm#Character_MirrorEmit', 'Stage_Mirror table -> reflected 64px compatibility metasprite OAM copy.', 'Fixed metasprite reflection does not establish arbitrary native actor reflection fidelity.'),
    ('queue', 'spawn'): rule('tools/bor_compile/production_campaign.py#compile_queues ' + QUEUE, SPAWN + ' src/core/spawn.pasm#Spawn_DoRosterReassign', 'Ten-byte ACCEPTED_COMPAT queue; actual model/type and set-scoped roster binding; selected source_defaults for new actors.', 'Roster identity is not native AI/action implementation; legacy borrowed-slot cases remain explicit below.'),
    ('queue', 'at'): rule(QUEUE, 'src/core/spawn.pasm#Spawn_Play__compare_trigger', 'round(source at * 4/5) u16 trigger; authored record order preserved.'),
    ('queue', 'wait'): rule(QUEUE, 'src/core/spawn.pasm#Spawn_Play__do_wait', 'Kind 2 global queue/camera wait, release when real enemies are gone; fixed six-actor pool.'),
    ('queue', 'group'): rule(QUEUE, 'src/core/spawn.pasm#Spawn_Play__do_group', 'Kind 3 byte min/max; shared queue gate and six-actor capacity, not source-unbounded population.'),
    ('queue', 'coords'): rule(QUEUE + ' tools/bor_compile/generate_environment.py#generate', SPAWN + ' src/core/stage_environment.pasm#StageEnv_ApplySpawnBase', 'XY round 4/5; Y clamp 0..255, signed X packed u16; nonzero Z only via type-driven steamer signed Q16.16 base side table.', 'Source coordinate fractions, offscreen depth and independent enemy-drop drivers are not preserved by the ten-byte queue.'),
    ('queue', 'health'): rule(QUEUE, SPAWN, 'Explicit health scaled by 64/100 and clamped 1..64; prop runtime HP remains compatibility-owned.', 'Authored absolute/native HP and damage semantics are not proven by the compatibility HUD byte.'),
    ('queue', 'alias'): rule('tools/bor_compile/generate_environment.py#generate tools/bor_compile/environment_semantics.py#display_name', 'src/core/stage_environment.pasm#StageEnv_ApplySpawnAlias src/core/hud_opponent.pasm#HudOpponent_Play', 'Separate physical-stage/queue alias ID and 20-byte display name; never actor/roster identity.', 'Generated alias table and opponent-target lifecycle still need assembled/current native runtime proof.'),
    ('queue', 'map'): rule(QUEUE + ' tools/stage_environment_abi.py#encode_map', 'src/core/stage_environment.pasm#StageEnv_ApplySpawnMap', 'Historical BOR map 0..7 split across facing/kind bits, absent per-model remaps fall back to base.', 'Palette selector transport alone does not prove correct visible CGRAM.'),
    ('queue', 'flip'): rule(QUEUE, SPAWN, 'Source flip 0/1 inverted to facing_left bit; extended map high bit shares byte 5.'),
    ('queue', 'boss'): rule(QUEUE, SPAWN + ' src/core/audio_music.pasm#Music_SelectBossTrack', 'Boss/identified-boss record kind controls boss state/music; source model remains independently bound.'),
    ('queue', 'item'): rule(QUEUE, 'src/core/spawn.pasm#Spawn_RevealPendingItems', 'Contained item slot/effect on obstacles via bytes 8 and 6, distinct from own object slot byte 9.', 'Enemy-held drops are not represented by this obstacle-only compatibility encoder.'),
    ('queue', '2pitem'): rule(QUEUE, 'src/core/spawn.pasm#Spawn_RevealPendingItems__filter_2p', 'Prop byte7 bit7 carries live-two-player reveal filter; item identity/effect remain separate.', 'Non-prop held drops and full source two-player semantics require separate native coverage.'),
    ('scene', 'music'): rule('tools/audio/generate_audio_music_ids.py#main tools/scene_video/scene_sequences.py#render', 'src/core/audio_music.pasm#Music_SelectSceneTrack src/core/scene_video.pasm#SceneVideo_ResolveSequence', 'Explicit source music and repeat -> sequence metadata/MSU PCM; no stage-music inference.'),
    ('scene', 'animation'): rule('tools/scene_video/convert_rugal.py#build_payload tools/scene_video/convert_ending.py#build_payloads tools/scene_video/scene_sequences.py#render', 'src/core/scene_video.pasm#SceneVideo_FrameTestHandler', 'Explicit bound clips, source delays, 256x192 converted frames; 126 Rugal and 1997 Ending source frames.', 'Scaled/quantized scene encoding is an adaptation; playback, skip cleanup and exactly-once completion are NOT_RUN.'),
}


def locate(reference, root=ROOT):
    """Find an executable definition, never a name mentioned only in comments."""
    relative, symbol = reference.split('#', 1)
    path = Path(root) / relative
    if not path.is_file():
        return dict(reference=reference, found=False)
    text = path.read_text(encoding='utf-8')
    line = None
    if path.suffix == '.py':
        line = next((n.lineno for n in ast.walk(ast.parse(text))
                     if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name == symbol), None)
    else:
        line = next((i for i, s in enumerate(text.splitlines(), 1)
                     if re.match(r'^\s*' + re.escape(symbol) + r':\s*(?:;.*)?$', s)), None)
    return dict(reference=reference, found=line is not None, line=line,
                file_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                evidence_kind='definition_only_not_runtime')


def audit_directives(domain, path, directives, ordinal=None):
    result = []
    queue_index = 0
    for d in directives:
        actual_domain = 'queue' if domain == 'stage' and ('queue', d.name) in RULES else domain
        identity = actual_domain, d.name
        if identity not in RULES:
            raise CoverageError(f'UNMAPPED_DIRECTIVE: {path}:{d.line}: {domain}.{d.name} {d.values}')
        result.append(dict(domain=actual_domain, directive=d.name, source_path=path,
                           line=d.line, values=list(d.values), entry_ordinal=ordinal))
        if actual_domain == 'queue':
            result[-1]['queue_index'] = queue_index
            if d.name == 'at':
                queue_index += 1
    return result


def selection_evidence(root=ROOT):
    """Reviewed selector semantics and cross-file hooks, without native claims."""
    paths = ('src/core/set_select.pasm', 'src/core/charselect.pasm',
             'src/core/campaign.pasm', 'src/core/ending.pasm', 'src/main.pasm')
    texts = {}
    for path in paths:
        file = Path(root) / path
        texts[path] = '\n'.join(s.split(';', 1)[0].strip() for s in file.read_text().splitlines()) if file.exists() else ''
    selector, charselect, campaign, ending, main = (texts[p] for p in paths)
    checks = {
        'difficulty_prompt_hooks': all('jsl BorSetSelect_' + n in charselect for n in ('Begin', 'Play', 'Finish')),
        'either_pad_navigation': all(s in selector for s in ('lda.l Input_trigger', 'ora.l Input2_trigger', 'bit #$0500', 'sta.l BorSet_Selected')),
        'confirmation_gate': bool(re.search(r'jsl BorSet_IsSelectable\s+bcc BorSetSelect_Play__draw', selector)),
        'selected_run_gate_and_map': bool(re.search(r'BorSet_BeginSelectedRun:\s+sep #\$20\s+\.a8\s+lda.l BorSet_Selected\s+jsl BorSet_IsSelectable\s+bcc BorSet_BeginSelectedRun__no\s+lda.l BorSet_CampaignMap,x\s+sta.l Game_CampaignId', campaign)),
        'first_typed_entry': bool(re.search(r'lda #\$FF\s+sta.l Game_CampaignOrdinal[\s\S]*?jsl Game_Campaign_ResolveNext', campaign)),
        'reset_selected_entry': 'jsl BorSet_BeginSelectedRun' in ending and 'jsl BorSet_BeginEasyRun' not in ending
            and bool(re.search(r'lda.l Game_Campaign_ResolvedValue\s+and #\$00FF\s+sta.l Game_StageIndex', ending))
            and 'jsl Game_Campaign_DispatchResolved' in ending,
        'bank17_include': bool(re.search(r'\.bank 17\s+\.org \$8000\s+\.include "core/set_select.pasm"', main)),
    }
    refs = ['src/core/set_select.pasm#BorSetSelect_Begin', 'src/core/set_select.pasm#BorSetSelect_Play',
            'src/core/set_select.pasm#BorSetSelect_Finish', 'src/core/campaign.pasm#BorSet_IsSelectable',
            'src/core/campaign.pasm#BorSet_BeginSelectedRun', 'src/core/ending.pasm#Game_State_NewGameReset']
    evidence = [locate(ref, root) for ref in refs]
    complete = all(checks.values()) and all(e['found'] for e in evidence)
    return dict(implementation_status='STATIC_IMPLEMENTED' if complete else 'PENDING_IMPLEMENTATION',
                runtime_evidence='NOT_RUN', owner='Curie', integration_checks=checks, static_evidence=evidence,
                source_files={p: hashlib.sha256((Path(root)/p).read_bytes()).hexdigest()
                              for p in paths if (Path(root)/p).is_file()},
                requirements=['TITLE START -> CHARSELECT difficulty 1 -> RIGHT Normal -> START -> difficulty 3/character step 3 -> player START.',
                              'NewGameReset validates the selected campaign and resolves its first typed entry.'],
                verifier_contract='Input route is implemented in source; runtime observation remains required.',
                closure='Static implementation review only; no native or assembled-artifact certification.')


def frontpanel_evidence(source, configs, root=ROOT):
    """Trace real compiler/main/NMI hooks and every source sequence; never encode."""
    from stage_frontpanel import sequence_directives
    paths = ('build_rom.py', 'src/main.pasm', 'src/core/nmi.pasm',
             'src/core/stage_frontpanel_bg2.pasm', 'tools/bor_compile/stage_frontpanel_bg2.py')
    texts = {p: (Path(root)/p).read_text() if (Path(root)/p).is_file() else '' for p in paths}
    asm = {p: '\n'.join(line.split(';', 1)[0].strip() for line in text.splitlines())
           for p, text in texts.items() if p.endswith('.pasm')}
    tree = ast.parse(texts['build_rom.py'])
    prepare = next((n for n in tree.body if isinstance(n, ast.FunctionDef)
                    and n.name == 'prepare_stage_environment_assets'), ast.Module(body=[], type_ignores=[]))
    imports = {(n.module, a.name, a.asname or a.name) for n in ast.walk(prepare)
               if isinstance(n, ast.ImportFrom) for a in n.names}
    calls = {n.func.id for n in ast.walk(prepare) if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    pack = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'build_msu_assets'), prepare)
    main, nmi, runtime = (asm[p] for p in paths[1:4])
    checks = {
        'full_bg2_materialization': ('stage_frontpanel_bg2', 'materialize_normal', 'materialize_frontpanels') in imports and 'materialize_frontpanels' in calls,
        'full_bg2_motion_tables': ('stage_frontpanel_bg2', 'motion_tables', 'frontpanel_motion_tables') in imports and 'frontpanel_motion_tables' in calls,
        'packer_environment_call': any(isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == 'prepare_stage_environment_assets' for n in ast.walk(pack)),
        'runtime_and_tables_included': all('.include "'+p+'"' in main for p in ('core/stage_frontpanel.pasm', 'core/stage_frontpanel_bg2.pasm', 'core/stage_frontpanel_legacy.pasm', 'generated/stage_frontpanel_tables.pasm', 'core/nmi.pasm')),
        'main_lifecycle_and_render_hooks': all('jsl '+name in main for name in ('StageFp_BG2ColdInit', 'StageFp_BG2SceneReset', 'StageFp_BG2BootDispatch', 'StageFp_BG2PlayDispatch', 'StageFp_BG2OamAttr')),
        'nmi_commit_hook': 'jsl StageFp_BG2CommitDispatch' in nmi,
        'normal_only_binding': bool(re.search(r'lda.l Game_CampaignId\s+and #\$00FF\s+cmp #3\s+bne StageFp_BG2Binding__off', runtime)),
        'legacy_commit_fallback': 'jsl StageFp_BG2LegacyCommit' in runtime,
    }
    mapped = RULES[('stage', 'frontpanel')]
    evidence = [locate(ref, root) for ref in mapped['lowering'] + mapped['consumer']]
    sequences = []
    for cfg in configs:
        ir = stage(source, cfg['source_level'])
        layers = sequence_directives(source, ir)
        if layers:
            sequences.append(dict(source_path=ir.source_path, direction=ir.scroll, layers=layers,
                                  native_status='PENDING_NATIVE'))
    complete = all(checks.values()) and all(e['found'] for e in evidence)
    return dict(implementation_status='STATIC_IMPLEMENTED' if complete else 'PENDING_IMPLEMENTATION',
                native_status='PENDING_NATIVE', runtime_evidence='NOT_RUN',
                integration_checks=checks, static_evidence=evidence, sequences=sequences,
                stage_bindings=len(sequences), declarations=sum(len(s['layers']) for s in sequences),
                unique_source_assets=len({key(layer['source_path']) for s in sequences for layer in s['layers']}),
                closure='Source sequences and static integration only; no media freshness, assembly or native/pixel proof.')


def required_use_status(identity, held_items, features, selection=None, frontpanel=None):
    """Only exercised unsupported semantics block the selected source set."""
    relevant = []
    if identity == ('project', 'set'):
        implemented = selection is not None and selection['implementation_status'] == 'STATIC_IMPLEMENTED'
        return dict(status='STATIC_IMPLEMENTED' if implemented else 'PENDING_IMPLEMENTATION',
                    blocks_normal_implementation=not implemented,
                    reason='Difficulty selection and selected-run typed dispatch integrated; native NOT_RUN.' if implemented
                    else 'Difficulty selection or selected-run integration evidence is missing.')
    if identity in (('queue', 'item'), ('queue', '2pitem')):
        uses = [u for u in held_items if u['directive'] == identity[1]]
        unsupported = [u for u in uses if u['model_type'] != 'obstacle']
        return dict(status='PENDING_NATIVE' if unsupported else 'COMPAT_ADAPTER',
                    blocks_normal_implementation=bool(unsupported),
                    required_uses=len(uses), obstacle_uses=len(uses) - len(unsupported),
                    unsupported_uses=unsupported,
                    reason='Obstacle-contained reveal adapter covers these required uses; runtime evidence remains separate.'
                    if not unsupported else 'Required non-obstacle held item has no lowering.',
                    unexercised_capabilities=[] if unsupported else ['enemy-held drops'])
    if identity == ('stage', 'frontpanel'):
        implemented = frontpanel is not None and frontpanel['implementation_status'] == 'STATIC_IMPLEMENTED'
        return dict(status='STATIC_IMPLEMENTED' if implemented else 'PENDING_IMPLEMENTATION',
                    native_status='PENDING_NATIVE', blocks_normal_implementation=not implemented,
                    reason='Full BG2 sequence compiler and main/NMI consumers statically integrated; native PENDING_NATIVE.' if implemented
                    else 'Full BG2 compiler or main/NMI integration is missing.')
    elif identity == ('queue', 'coords'):
        relevant = [f for f in features if f['feature'] == 'signed_altitude'
                    and f['status'] == 'PENDING_NATIVE']
    return dict(status='PENDING_NATIVE' if relevant else 'COMPAT_ADAPTER',
                blocks_normal_implementation=bool(relevant), required_gaps=relevant,
                reason='Required source uses await implementation.' if relevant
                else 'Required source uses have an explicit compatibility mapping; native/runtime evidence is not established.')


def inventory(source=None, *, configs=None, campaigns=None, scenes=None, roster=None,
              media_bindings=None, root=ROOT, source_set='Normal'):
    """Inspect exact Normal IR and lower its queues in memory; no materialization."""
    source = source or Source(PAK)
    campaign = {'Normal': CAMPAIGN, 'Hard': 'BOR_HARD'}[source_set]
    if any(value is None for value in (configs, campaigns, scenes, roster, media_bindings)):
        sys.path.insert(0, str(ROOT / 'tools/audio'))
        import shipped_content as shipped
        configs = shipped.STAGE_CONFIGS if configs is None else configs
        campaigns = shipped.CAMPAIGN_CONFIGS if campaigns is None else campaigns
        scenes = shipped.SCENE_CONFIGS if scenes is None else scenes
        roster = shipped.ROSTER_CONFIGS if roster is None else roster
        media_bindings = shipped.STAGE_MEDIA_BINDINGS if media_bindings is None else media_bindings
    # Audit independently before parser acceptance. Recognition cannot grant
    # coverage, even if a future compiler adds a new capability.
    levels_path = source.resolve('DATA/LEVELS.TXT')
    selected_lines = []
    active = False
    for d in source.lines(levels_path):
        if d.name == 'set':
            active = d.values == [source_set]
        if active:
            selected_lines.append(d)
    occurrences = audit_directives('project', levels_path, selected_lines)
    ir_project = project(source)
    matches = [s for s in ir_project.sets if s.name == source_set]
    if len(matches) != 1 or len(matches[0].entries) != 16:
        raise CoverageError('NORMAL_SHAPE_DRIFT: expected one Normal set with 16 entries')
    normal = matches[0]
    authored = campaigns[campaign]['entries']
    if len(authored) != 16 or campaigns[campaign]['source_set_id'] != normal.source_id:
        raise CoverageError('CAMPAIGN_BINDING_DRIFT')
    catalog = {}
    for physical, cfg in enumerate(configs):
        identity = key(cfg['source_level'])
        if identity in catalog:
            raise CoverageError('DUPLICATE_PHYSICAL_SOURCE: ' + identity)
        catalog[identity] = physical, cfg
    scene_bindings = {key(s['source_scene']): s for s in scenes}
    models = model_catalog(source)
    model_bindings = {}
    for name, model in models.items():
        definition = key(model['source_path'])
        candidates = [(i, r) for i, r in enumerate(roster)
                      if r['family'] == 'bor-original'
                      and normal.source_id in r.get('runtime_binding_sets', (0, 1, 2))
                      and key(r['source_character']) in
                      (definition.rsplit('/', 1)[0], definition.removesuffix('.txt'))]
        if len(candidates) > 1:
            raise CoverageError('AMBIGUOUS_MODEL_BINDING: ' + name)
        if candidates:
            slot, cfg = candidates[0]
            model_bindings[name] = dict(source_definition=model['source_path'],
                                       source_type=model['entity'].get('type'), runtime_slot=slot,
                                       source_defaults=bool(cfg.get('source_defaults')),
                                       adapter='set-scoped ACCEPTED_COMPAT roster binding; not source AI evidence')
    from production_campaign import complete_presentation
    media = [(cfg, complete_presentation(source, stage(source, cfg['source_level'])))
             for cfg in media_bindings if cfg['family'] == 'bor-original']
    entries, features, selected_configs, held_items = [], [], [], []
    used_models = set()
    source_hashes = {key(levels_path): hashlib.sha256(source.read(levels_path)).hexdigest()}
    for ordinal, entry in enumerate(normal.entries):
        domain = 'stage' if entry.kind == 'STAGE' else 'scene'
        directives = list(source.lines(entry.source_path))
        occurrences += audit_directives(domain, entry.source_path, directives, ordinal)
        parsed = stage(source, entry.source_path) if domain == 'stage' else scene(source, entry.source_path)
        if parsed.diagnostics:
            raise CoverageError(f'IR_DIAGNOSTICS: {entry.source_path}: {parsed.diagnostics}')
        bound = authored[ordinal]
        if bound['kind'] != domain or bool(bound['next_after']) != entry.next_after:
            raise CoverageError(f'TYPED_ENTRY_DRIFT: {ordinal}')
        row = dict(ordinal=ordinal, kind=domain, source_path=entry.source_path,
                   next_after=entry.next_after, directive_count=len(directives))
        source_hashes[key(entry.source_path)] = hashlib.sha256(source.read(entry.source_path)).hexdigest()
        if domain == 'stage':
            physical, cfg = catalog[key(entry.source_path)]
            if key(bound['source_level']) != key(entry.source_path) or cfg.get('source_set_id') != normal.source_id:
                raise CoverageError(f'STAGE_BINDING_DRIFT: {ordinal}')
            row.update(physical_id=physical, spawn_path=cfg['spawn'], queue_records=len(parsed.queue),
                       hole_prefix=len(parsed.environment.get('hole', [])), queue_bindings=[])
            selected_configs.append(cfg)
            signature = complete_presentation(source, parsed)
            accepted_media = [binding['source_level'] for binding, expected in media
                              if expected == signature and binding['bg'] == cfg['bg']
                              and binding.get('frontpanel') == cfg.get('frontpanel')]
            if not accepted_media:
                raise CoverageError(f'EXACT_MEDIA_BINDING_MISSING: {entry.source_path}')
            row['media_binding_sources'] = accepted_media
            row['media_check'] = 'SOURCE_CONTENT_SIGNATURE_MATCH_NOT_ENCODED_ASSET_FRESHNESS'
            # Actual metadata adapters, not parser-recognition claims.
            from stage_bounds import from_ir
            from stage_water import bind as bind_water
            row['bounds_words'] = from_ir(parsed).words()
            water = bind_water(source, parsed, physical)
            row['water_adapter'] = dict(active=water.active, adaptation=water.adaptation,
                                        amplitude=water.amplitude, rocking=water.rocking)
            if cfg.get('scroll_direction', 'right') != parsed.scroll:
                raise CoverageError(f'SCROLL_BINDING_DRIFT: {ordinal}')
            if len(parsed.environment.get('hole', [])) > 3:
                raise CoverageError('HOLE_CAPACITY_UNBOUND')
            frontpanels = [d for d in directives if d.name == 'frontpanel']
            if len(frontpanels) > 1:
                features.append(dict(ordinal=ordinal, feature='multiple_frontpanels',
                                     source_path=entry.source_path, declarations=len(frontpanels),
                                     layers=[dict(line=d.line, path=d.values[0]) for d in frontpanels],
                                     status='PENDING_NATIVE',
                                     reason='Ordered full BG2 sequence lowering and main/NMI integration reviewed separately; native motion/pixel acceptance remains pending.'))
            for index, event in enumerate(parsed.queue):
                if event.kind != 'spawn':
                    continue
                model = models[event.character.casefold()]['entity']
                if event.item:
                    held_items.append(dict(ordinal=ordinal, queue_index=index,
                                           directive='2pitem' if event.if2p else 'item',
                                           model=event.character, model_type=model.get('type'), item=event.item))
                for identity in (event.character, event.item):
                    if identity:
                        used_models.add(identity.casefold())
                        if identity.casefold() not in model_bindings:
                            raise CoverageError('NORMAL_MODEL_UNBOUND: ' + identity)
                row['queue_bindings'].append(dict(queue_index=index, model=event.character,
                                                  item=event.item, source_health=event.health,
                                                  runtime_slot=model_bindings[event.character.casefold()]['runtime_slot']))
                if event.altitude not in (None, 0):
                    supported = model.get('type') == 'steamer'
                    features.append(dict(ordinal=ordinal, queue_index=index, feature='signed_altitude',
                                         value=event.altitude, model=event.character,
                                         status='COMPAT_ADAPTER' if supported else 'PENDING_NATIVE',
                                         reason='generate_environment signed steamer base; no implicit enemy-drop driver.'))
                if event.item and model.get('type') != 'obstacle':
                    features.append(dict(ordinal=ordinal, queue_index=index, feature='non_obstacle_item',
                                         model=event.character, item=event.item, status='PENDING_NATIVE',
                                         reason='convert_events encodes contained item only for obstacle type.'))
                if event.health is not None and event.health > 100:
                    features.append(dict(ordinal=ordinal, queue_index=index, feature='health_saturation',
                                         value=event.health, status='COMPAT_ADAPTER', reason='64/100 scaling saturates at HP64.'))
        else:
            binding = scene_bindings.get(key(entry.source_path))
            if binding is None or binding['scene_id'] != bound['scene_id']:
                raise CoverageError(f'SCENE_BINDING_DRIFT: {ordinal}')
            sys.path.insert(0, str(ROOT / 'tools/scene_video'))
            import convert_rugal
            import convert_ending
            expected_clips = {'RUGAL': [key(convert_rugal.SOURCE_PATH)],
                              'ENDING': [key(f'DATA/SCENES/{name}.GIF') for name in convert_ending.CLIPS]}
            if [key(a['source_path']) for a in parsed.animations] != expected_clips.get(binding['scene_id']):
                raise CoverageError(f'SCENE_CLIP_LOWERING_UNBOUND: {entry.source_path}')
            if binding['scene_id'] == 'RUGAL' and (
                    len(parsed.animations[0]['delays_ms']) != convert_rugal.SOURCE_FRAMES
                    or set(parsed.animations[0]['delays_ms']) != {convert_rugal.SOURCE_DURATION_MS}):
                raise CoverageError('RUGAL_TIMING_LOWERING_UNBOUND')
            row.update(scene_id=binding['scene_id'], runtime_id=binding['runtime_id'],
                       music=parsed.music, repeat=parsed.repeat,
                       animation_frames=sum(len(a['delays_ms']) for a in parsed.animations),
                       animations=[dict(source_path=a['source_path'], frames=len(a['delays_ms']),
                                        duration_ms=a['duration_ms']) for a in parsed.animations])
        entries.append(row)
    # Actual production queue lowering; fresh bytes are only returned in memory.
    # Reject missing/ambiguous Normal model bindings through the production path.
    from production_campaign import compile_queues
    # The production entry point opens cfg.pak itself. Refuse to inventory a
    # different source while silently lowering the configured original pak.
    production_sources = {}
    for cfg in selected_configs:
        if cfg['pak'] not in production_sources:
            production_sources[cfg['pak']] = Source(cfg['pak'])
        bound_source = production_sources[cfg['pak']]
        for path in (levels_path, 'DATA/MODELS.TXT', cfg['source_level']):
            if bound_source.read(path) != source.read(path):
                raise CoverageError('SOURCE_BINDING_MISMATCH: ' + path)
        for name in used_models:
            path = models[name]['source_path']
            if bound_source.read(path) != source.read(path):
                raise CoverageError('MODEL_SOURCE_BINDING_MISMATCH: ' + path)
    packed = compile_queues(selected_configs, roster)
    for row in entries:
        if row['kind'] == 'stage':
            blob = packed[row['spawn_path']]
            if len(blob) != 10 * (row['queue_records'] + row['hole_prefix']):
                raise CoverageError('PACKED_QUEUE_ALIGNMENT: ' + row['source_path'])
            row['packed_records'] = len(blob) // 10
            row['packed_sha256'] = hashlib.sha256(blob).hexdigest()
            for binding in row['queue_bindings']:
                offset = (binding['queue_index'] + row['hole_prefix']) * 10
                binding.update(encoded_kind=blob[offset + 6] & 7,
                               encoded_object_slot=blob[offset + 9],
                               encoded_item_slot=blob[offset + 8], encoded_hp=blob[offset + 7] & 127,
                               adapter='ten-byte queue encoding only; downstream actor driver not certified')
            # Record own-object bindings as encoded, including legacy borrowed
            # actors (zero), instead of equating roster lookup with dispatch.
            row['encoded_object_slots'] = dict(Counter(blob[i + 9] for i in range(row['hole_prefix'] * 10, len(blob), 10)
                                                       if blob[i + 6] & 7 not in (2, 3)))
    counts = Counter((d['domain'], d['directive']) for d in occurrences)
    rules = []
    missing = []
    selection = selection_evidence(root)
    frontpanel = frontpanel_evidence(source, selected_configs, root)
    for feature in features:
        if feature['feature'] == 'multiple_frontpanels':
            feature['implementation_status'] = frontpanel['implementation_status']
    for identity, count in sorted(counts.items()):
        mapped = deepcopy(RULES[identity])
        evidence = [locate(ref, root) for ref in mapped['lowering'] + mapped['consumer']]
        missing.extend(e['reference'] for e in evidence if not e['found'])
        rules.append(dict(domain=identity[0], directive=identity[1], occurrences=count,
                          **mapped, static_evidence=evidence, runtime_evidence='NOT_RUN',
                          required_source=required_use_status(identity, held_items, features, selection, frontpanel)))
    return dict(schema_version=1, source_set=source_set, source_set_id=normal.source_id,
                source_hashes=source_hashes, entries=entries, directives=rules,
                model_bindings={name: model_bindings[name] for name in sorted(used_models)},
                occurrences=occurrences, features=features, selection_coverage=selection,
                frontpanel_coverage=frontpanel,
                held_item_coverage=dict(required_uses=len(held_items),
                                        model_types=dict(Counter(u['model_type'] for u in held_items)),
                                        uses=held_items),
                structural_coverage=dict(status='INCOMPLETE' if missing else 'COMPLETE',
                                         entries=len(entries), stages=sum(e['kind'] == 'stage' for e in entries),
                                         directive_kinds=len(counts), occurrences=len(occurrences),
                                         missing_definitions=sorted(set(missing)),
                                         queue_lowering='EXECUTED_IN_MEMORY',
                                         meaning='Every occurrence inventoried and traced; compatibility gaps remain explicit.'),
                native_coverage=dict(status='NOT_ESTABLISHED',
                                     pending=[f"{r['domain']}.{r['directive']}: {r['required_source']['reason']}"
                                              for r in rules if r['required_source']['blocks_normal_implementation']
                                              or r['required_source'].get('native_status') == 'PENDING_NATIVE'],
                                     compatibility_limitations=[f"{r['domain']}.{r['directive']}: {r['native_limitation']}"
                                                                for r in rules if r['native_limitation']],
                                     pending_scope='Unsupported required source uses and explicitly pending native frontpanel acceptance; static implementation never clears native acceptance.'),
                runtime_evidence=dict(status='NOT_RUN', emulator_used=False, claims=[]),
                release_verdict='BLOCKED_UNVERIFIED',
                nonclaims=['Definition presence is not executable reachability or native implementation proof.',
                           'No assembled ROM, generated media freshness, combat, visual, audio, or completion proof.',
                           'Queue bytes and model identity are compatibility transport, not source actor semantics.'])


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pak', type=Path, default=PAK)
    parser.add_argument('--require-native', action='store_true', help='Return nonzero: native runtime evidence is not established by this inventory.')
    args = parser.parse_args(argv)
    try:
        report = inventory(Source(args.pak))
        code = int(args.require_native or report['structural_coverage']['status'] != 'COMPLETE')
    except (ValueError, KeyError, OSError) as error:
        report = dict(structural_coverage=dict(status='REJECTED'), release_verdict='BLOCKED',
                      runtime_evidence=dict(status='NOT_RUN', claims=[]), error=f'{type(error).__name__}: {error}')
        code = 1
    print(json.dumps(report, indent=2))
    return code


if __name__ == '__main__':
    raise SystemExit(main())
