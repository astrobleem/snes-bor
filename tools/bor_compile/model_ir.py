"""Lossless model front end and explicit target-capability checks.

Parsing does not allocate actors, quantize pixels or guess an OpenBOR dialect.
The historical-bor profile implements only the pinned BOR.C interpretation;
other dialects retain raw directives and require explicit semantic bindings.
"""
from __future__ import annotations

import copy
import io
from dataclasses import asdict, dataclass, field
from fractions import Fraction

from PIL import Image
from compiler import Source, Directive, digest, key
from stage_environment_abi import MAP_MAX

DIRECT = 'DIRECTLY_LOWERABLE'
ADAPTER = 'LOWERABLE_WITH_ADAPTER'
UNSUPPORTED = 'UNSUPPORTED_RUNTIME_FEATURE'
MISSING = 'MISSING_ASSET'
UNKNOWN = 'UNKNOWN_SOURCE_SEMANTIC'

# Recognition never implies that a byte encoding or runtime driver exists.
MODEL_CAPABILITIES = {
    **{n:ADAPTER for n in 'name type subtype health score speed shadow icon diesound remap anim loop delay offset bbox attack move range sound load secret atchain frame'.split()},
    **{n:UNSUPPORTED for n in 'blast burn throwframe shootframe jumpframe'.split()},
}
KNOWN_ROLES = set('idle walk pain fall rise attack1 attack2 attack3 attack4 upper slide special freespecial jump jumpattack jumpattack2 land get grab grabattack grabattack2 throw backwalk waiting riseattack'.split())

# Engine semantics, not actor binding: original BOR.C compares the spawned
# model name after checking score and health. Stage display aliases do not
# affect this rule. Other dialects are unbound.
PICKUP_EFFECT_PROFILE = {'historical-bor': {'time': 'reset_timer'}}


def pickup_effect(dialect, model_name, health=0, score=0):
    if dialect not in PICKUP_EFFECT_PROFILE: return UNKNOWN
    if int(score): return 'score'
    if int(health): return 'health'
    return PICKUP_EFFECT_PROFILE[dialect].get(model_name.casefold(), 'extra_life')


@dataclass
class AttackIR:
    kind: str
    raw: list[str]
    box: list[int]
    force: int
    drop: int


@dataclass
class FrameIR:
    line: int
    source_path: str
    asset_sha256: str | None
    dimensions: list[int] | None
    state: dict


@dataclass
class AnimationIR:
    role: str
    directives: list[Directive] = field(default_factory=list)
    frames: list[FrameIR] = field(default_factory=list)
    properties: dict = field(default_factory=dict)


@dataclass
class ModelIR:
    project_id: str
    declaration: str
    source_path: str
    source_sha256: str
    dialect: str
    identity: tuple[str,str]
    directives: list[Directive]
    stats: dict = field(default_factory=dict)
    remaps: list[dict] = field(default_factory=list)
    assets: list[dict] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    animations: list[AnimationIR] = field(default_factory=list)
    diagnostics: list[dict] = field(default_factory=list)


def issue(ir, directive, category, reason, role=None):
    return dict(project_id=ir.project_id,model=ir.declaration,source_file=ir.source_path,
                line=directive.line,directive=directive.name,value=directive.values,
                animation_role=role,category=category,reason=reason)


def image_asset(source, path):
    resolved=source.image_path(path)
    raw=source.read(resolved)
    with Image.open(io.BytesIO(raw)) as im:
        return dict(source_path=resolved,sha256=digest(raw),dimensions=list(im.size),mode=im.mode,source_bytes=len(raw))


def parse_model(source: Source, path, declaration, project_id, dialect='unspecified'):
    path=source.resolve(path)
    ir=ModelIR(project_id,declaration,path,digest(source.read(path)),dialect,
               (project_id,key(path)),list(source.lines(path)))
    anim=None
    delay=0
    state={}
    for d in ir.directives:
        n,v=d.name,d.values
        role=anim.role if anim else None
        if n not in MODEL_CAPABILITIES:
            ir.diagnostics.append(issue(ir,d,UNKNOWN,'directive retained without an established dialect meaning',role))
        try:
            if n=='anim':
                if len(v)!=1: raise ValueError('anim requires one role')
                if any(a.role==v[0].lower() for a in ir.animations): raise ValueError('duplicate animation role')
                anim=AnimationIR(v[0].lower());ir.animations.append(anim)
                # BOR.C resets geometry/move/force here, but delay carries!
                state=dict(delay=delay,offset=[0,0],bbox=[0,0,0,0],attack=None,move=0)
                if anim.role not in KNOWN_ROLES:
                    ir.diagnostics.append(issue(ir,d,UNKNOWN,'unbound animation role',anim.role))
            elif n=='frame':
                if not anim or len(v)!=1: raise ValueError('frame requires an animation and one image')
                asset=image_asset(source,v[0]);ir.assets.append(asset)
                anim.frames.append(FrameIR(d.line,asset['source_path'],asset['sha256'],asset['dimensions'],copy.deepcopy(state)))
            elif n=='remap':
                if len(v)!=2: raise ValueError('remap requires two indexed images')
                assets=[image_asset(source,p) for p in v]
                ir.assets.extend(assets);ir.remaps.append(dict(line=d.line,source_paths=v,assets=assets))
                if assets[0]['dimensions']!=assets[1]['dimensions']:
                    ir.diagnostics.append(issue(ir,d,UNSUPPORTED,'remap image geometry differs'))
            elif n=='load':
                if len(v)!=1: raise ValueError('load requires one model reference')
                ir.dependencies.append(v[0])
            elif n in ('icon','diesound','sound'):
                if len(v)!=1: raise ValueError('asset requires one path')
                if n=='icon': ir.assets.append(image_asset(source,v[0]))
                else:
                    p=source.resolve(v[0]);ir.assets.append(dict(source_path=p,sha256=digest(source.read(p)),source_bytes=len(source.read(p))))
                if n=='sound' and anim: anim.properties.setdefault(n,[]).append(v)
                else: ir.stats[n]=v[0]
            elif n in ('attack','blast','burn'):
                if not anim: raise ValueError('attack outside animation')
                if not 1<=len(v)<=6: raise ValueError('unsupported attack arity')
                a=[int(x) for x in v]+[0]*6
                state['attack']=asdict(AttackIR(n,v,a[:4],a[4],a[5] if n=='attack' else 1))
            elif n in ('delay','offset','bbox','move'):
                if not anim: raise ValueError('frame state outside animation')
                arity={'delay':1,'offset':2,'bbox':4,'move':1}[n]
                if len(v)!=arity: raise ValueError('unsupported frame-state arity')
                nums=[int(x) for x in v]
                state[n]=nums[0] if arity==1 else nums
                if n=='delay': delay=state[n]
            elif anim:
                anim.properties.setdefault(n,[]).append(v)
            else:
                ir.stats[n]=v[0] if len(v)==1 else v
                if n in ('health','score','speed'):
                    if len(v)!=1: raise ValueError('stat requires one integer')
                    int(v[0])
        except (ValueError,IndexError,OSError) as error:
            category=MISSING if 'missing source asset' in str(error) or isinstance(error,OSError) else UNKNOWN
            ir.diagnostics.append(issue(ir,d,category,str(error),role))
        if anim: anim.directives.append(d)
    return ir


def source_behavior(ir):
    """Semantic description only; raw source remains independently available."""
    if ir.dialect!='historical-bor':
        return dict(status=UNKNOWN,reason='engine defaults/behavior not established for this dialect')
    t=ir.stats.get('type','none');raw=ir.stats.get('speed')
    try:
        speed=Fraction(1) if raw is None else min(Fraction(30),max(Fraction(1,2),Fraction(int(raw),10)))
        health=int(ir.stats.get('health',0));score=int(ir.stats.get('score',0))
    except (ValueError,TypeError):
        return dict(status=UNKNOWN,reason='malformed scalar stat retained in source IR')
    roles={a.role for a in ir.animations}
    behavior=dict(type=t,source_speed=str(speed),default_health=ir.stats.get('health','0'),
                  source_speed_rule='default 1; authored integer /10 clamped to [0.5,30]')
    if t=='none' and 'walk' in roles:
        behavior.update(driver='noncombat_horizontal_drift',random_speed_add='[0,3)',
                        heading='toward viewport from authored spawn x',despawn_bounds=[-80,400],collision='no smartspawn damage callback')
    elif t=='enemy':
        behavior['driver']='biker' if ir.stats.get('subtype')=='biker' else 'enemy_drop_then_ai'
    elif t=='item':
        behavior.update(driver='pickup',effect_rule='score, then health, then engine-defined model-name effect',
                        default_effect=pickup_effect(ir.dialect,str(ir.stats.get('name',ir.declaration)),health,score),
                        alias_may_change_effect=False)
    else: behavior['driver']=t
    return behavior


def validate_model_ir(ir):
    diagnostics=list(ir.diagnostics)
    if ir.stats.get('type','none') not in ('none','player','enemy','item','obstacle','steamer'):
        diagnostics.append(issue(ir,Directive(0,'type',[str(ir.stats.get('type'))]),UNKNOWN,'unbound model type'))
    if 'subtype' in ir.stats and ir.stats['subtype']!='biker':
        diagnostics.append(issue(ir,Directive(0,'subtype',[str(ir.stats['subtype'])]),UNKNOWN,'unbound model subtype'))
    for d in ir.directives:
        if MODEL_CAPABILITIES.get(d.name)==UNSUPPORTED:
            diagnostics.append(issue(ir,d,UNSUPPORTED,'no certified target event/attack-type lowering'))
    if len(ir.remaps)>MAP_MAX:
        diagnostics.append(issue(ir,Directive(0,'remap',[str(len(ir.remaps))]),UNSUPPORTED,
                                 f'ENVIRONMENT_MAP_CAPACITY_EXCEEDED: byte selector supports at most {MAP_MAX} alternate palettes'))
    behavior=source_behavior(ir)
    if behavior.get('driver')=='noncombat_horizontal_drift':
        diagnostics.append(issue(ir,Directive(0,'type',['none']),UNSUPPORTED,
                                 'experimental live drift uses byte RNG/fixed-point/OOP cadence; source rand32/randf float and scheduler equivalence remain unsupported','walk'))
    if behavior.get('default_effect')=='reset_timer':
        diagnostics.append(issue(ir,Directive(0,'type',['item']),UNSUPPORTED,
                                 'target lacks source timeleft countdown/timeout and delayed pickup lifecycle required by timer reset'))
    if behavior.get('status')==UNKNOWN and ir.dialect=='historical-bor':
        diagnostics.append(issue(ir,Directive(0,'stats',[]),UNKNOWN,behavior['reason']))
    for a in ir.animations:
        if any(f.state.get('attack',{}).get('force',0) for f in a.frames if f.state.get('attack')) and a.role in ('fall','pain','idle','walk','rise'):
            diagnostics.append(issue(ir,Directive(0,'attack',[]),UNSUPPORTED,
                                     'frame descriptors dispatch attacks on this role in isolated runtime; source behavior-owned activation, damage callbacks and target-filter lifecycle remain unsupported by fixed-slot production',a.role))
        if len(a.frames)>255:
            diagnostics.append(issue(ir,Directive(0,'frame',[str(len(a.frames))]),UNSUPPORTED,'runtime frame count is u8',a.role))
    if ir.dialect!='historical-bor':
        diagnostics.append(issue(ir,Directive(0,'dialect',[ir.dialect]),UNKNOWN,'behavior/defaults require dialect validation'))
    return dict(status='BLOCKED' if diagnostics else 'LOWERABLE_WITH_ADAPTER',
                classifications=sorted({d['category'] for d in diagnostics} or {ADAPTER}),
                diagnostics=diagnostics,behavior=behavior,
                needs_encoding=True,certified=False)
