#!/usr/bin/env python3
"""Cross-release actual RTCW Crypt1 grate screenshots from fixed camera, original Sept clean vs LUT V05.
The old retail source remains a genuine September source postimage, proof helpers only in game/cgame.
"""
from pathlib import Path
import sys,json,math
import numpy as np
from PIL import Image,ImageDraw,ImageEnhance

VIEWS=("grate_near48_pitch28","grate_near48_pitch42","grate_near72_pitch28","grate_near72_pitch42")
CASES=("baseline","no_dynamic_shadow","no_ssgi","no_cas","no_a2c","lightmap_only","baseline_repeat")
def camera_ok(old,new):
    om=old["camera"];nm=new["camera"]
    def unpack(s):
        return tuple(float(x) for x in s.split(","))
    for view in VIEWS:
        idx=next(s["id"] for s in old["shots"] if s["view"]==view and s["variant"]=="baseline")
        a=om[str(idx)];b=nm[str(idx)]
        for name in ("eye","forward"):
            av,bv=unpack(a[name]),unpack(b[name])
            assert len(av)==len(bv)==3,(view,name,av,bv)
            delta=max(abs(x-y) for x,y in zip(av,bv))
            assert delta<0.002,(view,name,"camera differs",av,bv,delta)
    return True

def gray(im):
    a=np.asarray(im.convert("RGB"),dtype=np.float32)
    return 0.2126*a[:,:,0]+0.7152*a[:,:,1]+0.0722*a[:,:,2]

def edge_stats(a):
    g=gray(a)
    xx=np.abs(np.diff(g,axis=1))[:,1:]
    yy=np.abs(np.diff(g,axis=0))[1:,:]
    yy=yy[:xx.shape[0],:xx.shape[1]]
    return int(((xx+yy)>20).sum()),round(float((xx+yy).mean()),3)

def main(old_path,new_path,out):
    old=json.loads((old_path/"CRYPT1_GRATE_CLOSEUP_REPORT.json").read_text())
    new=json.loads((new_path/"CRYPT1_GRATE_CLOSEUP_REPORT.json").read_text())
    assert old["ready"] and old["complete"] and old["saved_shots"]==28 and old["exitcode"]==0,old
    assert new["ready"] and new["complete"] and new["saved_shots"]==28 and new["exitcode"]==0,new
    assert camera_ok(old,new)
    out.mkdir(parents=True,exist_ok=True)
    checks=[]
    for view in VIEWS:
        for case in ("baseline","no_dynamic_shadow","no_ssgi","lightmap_only"):
            fname=f"crypt1_{view}_{case}.png"
            ia=Image.open(old_path/fname).convert("RGB")
            ib=Image.open(new_path/fname).convert("RGB")
            assert ia.size==ib.size==(1280,720),(view,case,ia.size,ib.size)
            a=np.asarray(ia,dtype=np.int16)
            b=np.asarray(ib,dtype=np.int16)
            diff=np.abs(a-b)
            roi=(slice(int(a.shape[0]*.30),int(a.shape[0]*.93)),
                 slice(int(a.shape[1]*.12),int(a.shape[1]*.88)))
            mask=np.any(diff[roi]>4,axis=2)
            old_edges,oe=edge_stats(ia);new_edges,ne=edge_stats(ib)
            checks.append({"view":view,"case":case,"baseline_image_pair":fname,
                           "full_rgb_mean_abs_delta":round(float(diff.mean()),4),
                           "gate_ground_roi_mean_abs_rgb_delta":round(float(diff[roi].mean()),4),
                           "gate_ground_roi_pixels_changed_gt4_pct":round(float(mask.mean()*100),3),
                           "edge_activity_september_count":old_edges,
                           "edge_activity_october_count":new_edges,
                           "edge_activity_september_mean":oe,"edge_activity_october_mean":ne,
                           "interpretation":"descriptive pixel/edge change only, NOT proof of anti-aliasing quality"})
        # Horizontal 2x3 matrix: baseline, no dynamic, no SSGI. Original 1280x720 scaled 600x338.
        W,H=600,338
        board=Image.new("RGB",(W*3,(H+40)*2),(19,19,19))
        dr=ImageDraw.Draw(board)
        for row,(basedir,title) in enumerate(((old_path,"SEPT 18 CLEAN PRODUCTION V1 / as of SEPT 21"),
                                              (new_path,"OCT 24 FOURWEEK MASTER + LUT V05"))):
            for col,case in enumerate(("baseline","no_dynamic_shadow","no_ssgi")):
                img=Image.open(basedir/f"crypt1_{view}_{case}.png").convert("RGB")
                img.thumbnail((W,H))
                x,y=col*W,row*(H+40)
                dr.text((x+7,y+7),title+" | "+view,fill=(245,245,245))
                dr.text((x+7,y+23),case,fill=(192,206,226))
                board.paste(img,(x,y+38))
        board.save(out/(view+"_SEPT21_CLEAN_VS_V05_ORIGINAL_RGB.png"))
        # Close-up ROI crop original 2-up plus brighter copy (explicit labeled; not screenshot original).
        crop=(int(1280*.16),int(720*.32),int(1280*.84),int(720*.91))
        sep=Image.open(old_path/f"crypt1_{view}_baseline.png").convert("RGB").crop(crop)
        oct=Image.open(new_path/f"crypt1_{view}_baseline.png").convert("RGB").crop(crop)
        sepBright=ImageEnhance.Brightness(sep).enhance(2.25)
        octBright=ImageEnhance.Brightness(oct).enhance(2.25)
        w,h=sep.size
        detail=Image.new("RGB",(w*2,(h+32)*2),(18,18,18));draw=ImageDraw.Draw(detail)
        for row,(sa,sb,caption) in enumerate(((sep,oct,"original exposure"),(sepBright,octBright,"brightness x2.25 for visibility only"))):
            for col,(img,label) in enumerate(((sa,"SEP 18 CLEAN"),(sb,"OCT 24 LUT V05"))):
                xx=col*w;yy=row*(h+32);draw.text((xx+8,yy+9),f"{label} — {caption}",fill="white")
                detail.paste(img,(xx,yy+30))
        detail.save(out/(view+"_SEPT21_CLEAN_VS_V05_GATE_GROUND_DETAIL.png"))
    report={
        "historical_cutoff":"2026-09-21T23:59:59Z",
        "september_release":"Clean Production Release v1, 2026-09-18, workflow run 35361762179",
        "september_artifact_id":10555091293,
        "october_release":"FourWeek Master SourceDefaultsON + user-verified LUT V05, 2026-10-24",
        "october_camera_reference_run":40114380523,
        "camera_alignment_pass":True,
        "same_original_licensed_crypt1_bsp":True,
        "same_viewport":[1280,720],
        "software_gl_renderer":"Mesa llvmpipe on ubuntu-24.04; Windows RTX 3060 Ti NOT used",
        "limitations":"Later shader features LUT V05 and CAS did not exist in September. Full native-image baseline comparison is not identical feature parity. Lightmap-only mode is a diagnostic visual mode. Pixel differences are not direct shadow quality proof.",
        "compared_pairs":checks
    }
    (out/"SEPT21_CLEAN_VS_LUTV05_CRYPT1_CROSS_RELEASE_COMPARISON.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    (out/"COMPARISON_SCOPE.txt").write_text(
        "Sep 18 latest Clean Production before Sep 21: run 35361762179.\n"
        "Oct 24 master+V05: run 40114380523.\n"
        "Both actual retail Crypt1 map, matched camera pose from game console proof.\n"
        "Images captured with Linux software GL. Modern shading differs as expected.\n"
        "No visual defect can be declared fixed solely from changed pixel counts.\n")
    print("SEPT21_VS_LUTV05_CRYPT1_CAMERA_ALIGNED_CROSS_RELEASE_IMAGES_PASS",
          len(checks),len(VIEWS),flush=True)

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("september",type=Path)
    p.add_argument("october",type=Path)
    p.add_argument("out",type=Path)
    args=p.parse_args()
    main(args.september,args.october,args.out)
