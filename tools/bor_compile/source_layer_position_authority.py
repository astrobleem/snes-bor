"""Compile pinned draw_scrolled_bg and compare layer-repeat placements."""
import argparse,hashlib,json,os,subprocess
from pathlib import Path
from dialect_4086 import ENGINE_COMMIT
from script_nested_authority import extract
from source_layer_position_4086 import placements,legacy_layer

PREAMBLE=r'''#include <stdio.h>
typedef struct {int magic;} screen;
typedef struct {int amplitude,watermode;float wavespeed;int wavetime;} water_t;
typedef struct {int xrepeat,yrepeat,transbg,alpha,xspan,yspan;water_t water;void *table;} s_drawmethod;
typedef struct {int x,y;} xy;
typedef struct {int x,z;} xz;
typedef struct {float x,z;} fxz;
typedef struct {screen *screen,*sprite;} gfx;
typedef struct {xy size;xz spacing,offset;fxz ratio;s_drawmethod drawmethod;float bgspeedratio;int enabled,z,quake,neon;gfx gfx;} s_layer;
typedef struct {int x,z,depth;} hole;
typedef struct {int numholes,numlayersref,scrolldir;hole *holes;s_layer *layersref;void **palettes;} level_t;
level_t storage,*level=&storage;s_layer layer;screen image={1};
int viewportw=256,viewporth=224,viewportx=0,viewporty=0;
struct {int hRes,vRes;}videomodes={320,240};
float advancex,advancey,bgtravelled,timevar;
int gfx_x_offset=0,gfx_y_offset=0,holesprite,current_palette=0,pixelformat=0;
void *neontable;int case_index;
s_drawmethod plainmethod;
#define SCROLL_UP 4
#define PIXEL_x8 0
#define screen_magic 1
#define sprite_magic 2
#define HOLE_Z 0
#define screenx advancex
#define screeny advancey
void spriteq_add_sprite(int x,int y,int z,int s,s_drawmethod *m,int i){}
void spriteq_add_screen(int x,int y,int z,screen *s,s_drawmethod *m,int i){printf("L %d %d %d %d %d %d %d\n",case_index,x,y,m->xrepeat,m->yrepeat,m->xspan,m->yspan);}
void spriteq_add_frame(int x,int y,int z,screen *s,s_drawmethod *m,int i){spriteq_add_screen(x,y,z,s,m,i);}
'''


def derive(engine,folder):
    folder.mkdir(parents=True,exist_ok=True)
    raw=subprocess.check_output(['git','-C',str(engine),'show',ENGINE_COMMIT+':engine/openbor.c']);function=extract(raw.decode('latin1'),'draw_scrolled_bg')
    cases=[]
    for kind,size,ordinal,count in [('background',(800,400),0,0),('panel',(2544,245),0,0),('frontpanel',(350,245),0,5),('frontpanel',(700,245),2,5)]:
        for camera in [(0,0),(5,3),(-5,-3),(100,0),(350,8),(500,12),(1500,0),(2224,0),(2224.5,3.5),(2500,0),(4000,0),(0.5,0.5)]:
            spec=legacy_layer(kind,size,ordinal=ordinal,front_count=count);cases.append(dict(kind=kind,camera=camera,viewport=(256,224),**spec))
    statements=[]
    for index,c in enumerate(cases):
        statements.append('case_index=%d;advancex=%sf;advancey=%sf;layer.size.x=%d;layer.size.y=%d;layer.ratio.x=%sf;layer.ratio.z=%sf;layer.offset.x=%d;layer.offset.z=%d;layer.spacing.x=%d;layer.spacing.z=%d;layer.drawmethod.xrepeat=%d;layer.drawmethod.yrepeat=%d;layer.bgspeedratio=%sf;draw_scrolled_bg();'% (index,*[str(float(v))for v in c['camera']],*c['size'],*[str(float(v))for v in c['ratio']],*c['offset'],*c['spacing'],*c['repeat'],str(float(c['bgspeedratio']))))
    driver='int main(){storage.numlayersref=1;storage.layersref=&layer;layer.enabled=1;layer.gfx.screen=&image;'+''.join(statements)+'return 0;}'
    (folder/'layer_position.c').write_text(PREAMBLE+function+'\n'+driver)
    env=dict(os.environ,WATCOM='C:/WATCOM',INCLUDE='C:/WATCOM/H;C:/WATCOM/H/NT')
    build=subprocess.run(['C:/WATCOM/BINNT/wcl386.exe','-q','-za99','-bt=nt','layer_position.c','-fe=layer_position.exe'],cwd=folder,env=env,capture_output=True,text=True)
    (folder/'build.log').write_text(build.stdout+build.stderr)
    if build.returncode:raise ValueError('LAYER_POSITION_AUTHORITY_BUILD_FAILED')
    output=subprocess.check_output([str((folder/'layer_position.exe').resolve())],cwd=folder,text=True);(folder/'execution.log').write_text(output)
    results=[]
    for line in output.splitlines():
        tag,index,x,y,nx,ny,sx,sy=line.split();index,x,y,nx,ny,sx,sy=map(int,[index,x,y,nx,ny,sx,sy]);case=cases[index]
        expected=placements(**{k:case[k]for k in ['size','ratio','offset','spacing','repeat','camera','viewport','bgspeedratio']})
        observed=[(x+i*sx,y+j*sy)for j in range(ny)for i in range(nx)]
        results.append(dict(index=index,case=case,observed=observed,expected=expected,passed=observed==expected))
    report=dict(schema='BYOR_SOURCE_LAYER_POSITION_AUTHORITY_V1',status='PASS'if len(results)==len(cases)and all(r['passed']for r in results)else'FAIL',engine_commit=ENGINE_COMMIT,source_sha256=hashlib.sha256(raw).hexdigest(),function_sha256=hashlib.sha256(function.encode('latin1')).hexdigest(),cases=len(cases),results=results,live_camera_owner_bound=False,motu_gameplay_proven=False,no_color_reduction=True)
    (folder/'report.json').write_text(json.dumps(report,indent=2)+'\n');return report


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--engine',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();r=derive(a.engine,a.output.resolve());print(r['status'],r['cases']);assert r['status']=='PASS'
if __name__=='__main__':main()
