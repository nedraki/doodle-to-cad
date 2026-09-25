from __future__ import annotations
from pathlib import Path
from typing import Any
import cv2
import numpy as np

BUILD_CUBE_MM=256.0  # BambuLab X1C/P1S build volume

def _decode(data: bytes) -> np.ndarray | None:
    return cv2.imdecode(np.frombuffer(data,np.uint8),cv2.IMREAD_COLOR) if data else None

def _render_internal_profile_count(image:np.ndarray)->int:
    """Count closed boundaries inside the dominant rendered silhouette.

    OpenSCAD colors visible inner walls, so an opening is not necessarily the
    background color. Edge hierarchy is more stable than color segmentation.
    """
    gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY)
    edges=cv2.Canny(gray,30,90)
    contours,hierarchy=cv2.findContours(edges,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
    if not contours or hierarchy is None:return 0
    hierarchy=hierarchy[0];areas=[cv2.contourArea(c) for c in contours]
    outer=max(range(len(contours)),key=lambda i:areas[i])
    container=outer
    children=[i for i,item in enumerate(hierarchy) if int(item[3])==outer]
    near_duplicate=[i for i in children if areas[i]>=areas[outer]*.8]
    if near_duplicate:container=max(near_duplicate,key=lambda i:areas[i])
    ih,iw=image.shape[:2];minimum=image.size/3*.001
    candidates=[]
    for i,item in enumerate(hierarchy):
        if int(item[3])!=container or areas[i]<minimum:continue
        x,y,w,h=cv2.boundingRect(contours[i])
        if w>=iw*.02 and h>=ih*.02 and w<iw*.8 and h<ih*.8:
            candidates.append(i)
    return len(candidates)

def _normalized_profile(image:np.ndarray,*,render:bool)->tuple[np.ndarray,int]:
    if render:
        border=np.concatenate((image[0],image[-1],image[:,0],image[:,-1])); bg=np.median(border,axis=0)
        ink=(np.linalg.norm(image.astype(float)-bg,axis=2)>18).astype(np.uint8)*255
    else: ink=cv2.threshold(cv2.cvtColor(image,cv2.COLOR_BGR2GRAY),190,255,cv2.THRESH_BINARY_INV)[1]
    ink=cv2.morphologyEx(ink,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
    contours,hierarchy=cv2.findContours(ink,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
    if not contours or hierarchy is None:return np.zeros((96,96),np.uint8),0
    hierarchy=hierarchy[0];depths=[]
    for i in range(len(contours)):
        depth=0;parent=int(hierarchy[i][3])
        while parent>=0:depth+=1;parent=int(hierarchy[parent][3])
        depths.append(depth)
    outer=max(range(len(contours)),key=lambda i:cv2.contourArea(contours[i]));profile=np.zeros_like(ink)
    cv2.drawContours(profile,contours,outer,255,cv2.FILLED)
    hole_depth=1 if render else 2
    holes=[i for i,d in enumerate(depths) if d==hole_depth and cv2.contourArea(contours[i])>ink.size*.0005]
    for i in holes:cv2.drawContours(profile,contours,i,0,cv2.FILLED)
    points=cv2.findNonZero(profile)
    if points is None:return np.zeros((96,96),np.uint8),len(holes)
    x,y,w,h=cv2.boundingRect(points);crop=profile[y:y+h,x:x+w];scale=min(88/max(w,1),88/max(h,1))
    resized=cv2.resize(crop,(max(1,round(w*scale)),max(1,round(h*scale))),interpolation=cv2.INTER_NEAREST)
    target=np.zeros((96,96),np.uint8);oy,ox=(96-resized.shape[0])//2,(96-resized.shape[1])//2
    target[oy:oy+resized.shape[0],ox:ox+resized.shape[1]]=resized
    return target,_render_internal_profile_count(image) if render else len(holes)

def _normalized_edges(image:np.ndarray,*,render:bool)->np.ndarray:
    if render:
        profile,_=_normalized_profile(image,render=True);return cv2.Canny(profile,50,150)
    ink=cv2.threshold(cv2.cvtColor(image,cv2.COLOR_BGR2GRAY),190,255,cv2.THRESH_BINARY_INV)[1]
    points=cv2.findNonZero(ink)
    if points is None:return np.zeros((96,96),np.uint8)
    x,y,w,h=cv2.boundingRect(points);crop=ink[y:y+h,x:x+w];scale=min(88/max(w,1),88/max(h,1))
    resized=cv2.resize(crop,(max(1,round(w*scale)),max(1,round(h*scale))),interpolation=cv2.INTER_NEAREST)
    target=np.zeros((96,96),np.uint8);oy,ox=(96-resized.shape[0])//2,(96-resized.shape[1])//2
    target[oy:oy+resized.shape[0],ox:ox+resized.shape[1]]=resized
    return target

def _edge_similarity(a:np.ndarray,b:np.ndarray,tolerance:int=5)->float:
    if not np.any(a) or not np.any(b):return 0.0
    da=cv2.distanceTransform(cv2.bitwise_not(a),cv2.DIST_L2,3);db=cv2.distanceTransform(cv2.bitwise_not(b),cv2.DIST_L2,3)
    a_to_b=float(np.mean(db[a>0]<=tolerance));b_to_a=float(np.mean(da[b>0]<=tolerance))
    return 2*a_to_b*b_to_a/max(a_to_b+b_to_a,1e-9)

def assign_view_groups(evidence:dict[str,Any],primary_view:str="front",projection_standard:str="third-angle")->dict[str,dict[str,Any]]:
    groups=evidence.get("view_groups") or []
    if not groups:return {}
    first=projection_standard=="first-angle"
    ALIGN_TOL=0.10  # normalized sheet units; third-angle views align with the front view
    def cx_of(g):return g["center_normalized"][0]
    def cy_of(g):return g["center_normalized"][1]
    def bw_of(g):
        bbox=g.get("bbox_normalized")
        return bbox[2] if bbox else (g.get("relative_size") or 0.09)**0.5
    def bh_of(g):
        bbox=g.get("bbox_normalized")
        return bbox[3] if bbox else (g.get("relative_size") or 0.09)**0.5
    def links(g):
        # Projection links = drafting alignment with another group: vertical
        # (shared x-centre, one above the other) or horizontal (shared y-centre,
        # side by side). The front view is the layout HUB: in a 3-view sheet it
        # is the only group with both a vertical and a horizontal partner.
        v=h=0
        for other in groups:
            if other is g:continue
            dx,dy=cx_of(other)-cx_of(g),cy_of(other)-cy_of(g)
            if abs(dx)<=ALIGN_TOL and abs(dy)>0.05:v+=1
            if abs(dy)<=ALIGN_TOL and abs(dx)>0.15:h+=1
        return v,h
    def primary_key(g):
        v,h=links(g)
        # Axis-specific tie-breaks between equal-structure groups:
        # - horizontal pairs: the side view (right in third-angle, left view in
        #   first-angle) is drawn RIGHT of the front view in both standards,
        #   so the front is the LEFT group.
        # - vertical-only pairs: the LOWER group is the front. Third-angle draws
        #   the top view above the front; first-angle sheets that fit two groups
        #   on the sheet also put the front lower (its bottom view above it).
        #   Area is NOT a usable signal here: a flat part's footprint view is
        #   legitimately larger than its thin front edge (calibration cases
        #   008/013 and hybrid 102 all prove it). Area breaks true ties only.
        horizontal_pref = cx_of(g)<0.5
        vertical_pref = cy_of(g)
        return (v+h, v>0 and h>0, horizontal_pref if h else False,
                vertical_pref if (v and not h) else False, g.get("relative_size",0))
    primary=max(groups,key=primary_key)
    px,py=primary["center_normalized"]
    result:dict[str,dict[str,Any]]={primary_view:primary}
    claims:dict[str,tuple[dict[str,Any],float]]={}
    def claim(group,direction)->float:
        # Strength of this group's claim on a slot: CLOSENESS to the front view in
        # the dominant axis, boosted by drafting alignment (top/bottom share width
        # & x-centre; left/right share height & y-centre). Proximity is what keeps
        # a far-away title block from stealing the 'top' slot from the real,
        # directly-above aligned view.
        gx,gy=group["center_normalized"];dx,dy=gx-px,gy-py
        if abs(dy)>=abs(dx):
            dominant,other_axis=abs(dy),abs(dx)
            aligned=abs(bw_of(group)-bw_of(primary))<=max(0.18,0.35*bw_of(primary)) and abs(dx)<=ALIGN_TOL
        else:
            dominant,other_axis=abs(dx),abs(dy)
            aligned=abs(bh_of(group)-bh_of(primary))<=max(0.18,0.35*bh_of(primary)) and abs(dy)<=ALIGN_TOL
        return (1.0-dominant)*(1.35 if aligned else 1.0)-other_axis
    for group in groups:
        if group is primary:continue
        gx,gy=group["center_normalized"];dx,dy=gx-px,gy-py
        if abs(dy)>=abs(dx):direction=("bottom" if first else "top") if dy<0 else ("top" if first else "bottom")
        else:direction=("right" if first else "left") if dx<0 else ("left" if first else "right")
        strength=claim(group,direction)
        if direction not in claims or strength>claims[direction][1]:
            claims[direction]=(group,strength)  # strongest claimant wins the slot
    for direction,(group,_strength) in claims.items():
        result.setdefault(direction,group)
    return result

def _crop_internal_profile_count(image:np.ndarray)->int:
    """Closed boundaries enclosed within the dominant silhouette of ONE crop.

    Mirrors _normalized_profile's hole logic (depth-2 rings for source ink) so
    the features gate compares like with like: profiles demanded by THIS view
    against profiles rendered in THIS view.
    """
    ink=cv2.threshold(cv2.cvtColor(image,cv2.COLOR_BGR2GRAY),190,255,cv2.THRESH_BINARY_INV)[1]
    ink=cv2.morphologyEx(ink,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
    contours,hierarchy=cv2.findContours(ink,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
    if not contours or hierarchy is None:return 0
    hierarchy=hierarchy[0];depths=[]
    for i in range(len(contours)):
        depth=0;parent=int(hierarchy[i][3])
        while parent>=0:depth+=1;parent=int(hierarchy[parent][3])
        depths.append(depth)
    return sum(1 for i,d in enumerate(depths) if d==2 and cv2.contourArea(contours[i])>ink.size*.0005)

def _profile_centroids(image:np.ndarray,*,render:bool)->list[tuple[float,float]]:
    """Centers of enclosed openings normalized (0..1) inside the outer silhouette.

    Source ink: enclosed background rings at hierarchy depth 2 (wobbly doodle
    strokes self-intersect, so sliver regions from stroke pinches are rejected
    via a fill-ratio guard). Renders: OpenSCAD shades visible interior walls,
    so openings are detected from edge hierarchy (like _render_internal_profile_count).
    Returns sheet-like (u right, v down) coordinates so positions can be
    compared between a doodle crop and the matching CAD projection.
    """
    if render:
        gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY) if image.ndim==3 else image
        ih,iw=image.shape[:2]
        border=np.concatenate((gray[0],gray[-1],gray[:,0],gray[:,-1]))
        bg=float(np.median(border))
        ink=(np.abs(gray.astype(float)-bg)>18).astype(np.uint8)*255
        ink=cv2.morphologyEx(ink,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
        contours,_=cv2.findContours(ink,cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        if not contours:return []
        outer=max(contours,key=cv2.contourArea)
        x,y,w,h=cv2.boundingRect(outer)
        if w<8 or h<8:return []
        sil=np.zeros_like(ink);cv2.drawContours(sil,[outer],-1,255,cv2.FILLED)
        # openings = background-colored regions enclosed by the body (through
        # holes show background through the part; walls are shaded ink)
        enclosed=cv2.bitwise_and(sil,cv2.bitwise_not(ink))
        count,labels,stats,cents=cv2.connectedComponentsWithStats(enclosed,8)
        centroids=[]
        for i in range(1,count):
            area=stats[i,cv2.CC_STAT_AREA]
            if area<ink.size*.0005:continue
            bw,bh=stats[i,cv2.CC_STAT_WIDTH],stats[i,cv2.CC_STAT_HEIGHT]
            if bw>=w*.95 and bh>=h*.95:continue
            if area/max(bw*bh,1)<0.4:continue      # ignore wisps/slivers
            cu,cv_=cents[i]
            centroids.append(((cu-x)/w,(cv_-y)/h))
        # Windows that look into a shaded interior (not through to background)
        # are not background-coloured; recover them from the edge hierarchy.
        edges=cv2.Canny(gray,30,90)
        econtours,eh=cv2.findContours(edges,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
        if econtours and eh is not None:
            eh=eh[0];eareas=[cv2.contourArea(c) for c in econtours]
            eouter=int(np.argmax(eareas))
            container=eouter
            echildren=[i for i,item in enumerate(eh) if int(item[3])==eouter]
            near=[i for i in echildren if eareas[i]>=eareas[eouter]*.8]
            if near:container=max(near,key=lambda i:eareas[i])
            for i,item in enumerate(eh):
                if int(item[3])!=container or eareas[i]<image.size/3*.001:continue
                bx,by,bw,bh=cv2.boundingRect(econtours[i])
                if bw<iw*.02 or bh<ih*.02 or bw>=iw*.8 or bh>=ih*.8:continue
                if eareas[i]/max(bw*bh,1)<0.5:continue
                moments=cv2.moments(econtours[i],binaryImage=False)
                if moments["m00"]==0:continue
                mx,my=moments["m10"]/moments["m00"],moments["m01"]/moments["m00"]
                centroid=((mx-x)/w,(my-y)/h)
                if not any(abs(centroid[0]-px)<.04 and abs(centroid[1]-py)<.04 for px,py in centroids):
                    centroids.append(centroid)
        return centroids
    ink=cv2.threshold(cv2.cvtColor(image,cv2.COLOR_BGR2GRAY),190,255,cv2.THRESH_BINARY_INV)[1]
    ink=cv2.morphologyEx(ink,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
    contours,hierarchy=cv2.findContours(ink,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
    if not contours or hierarchy is None:return []
    hierarchy=hierarchy[0];depths=[]
    for i in range(len(contours)):
        depth=0;parent=int(hierarchy[i][3])
        while parent>=0:depth+=1;parent=int(hierarchy[parent][3])
        depths.append(depth)
    areas=[cv2.contourArea(c) for c in contours]
    outer=int(np.argmax(areas))
    x,y,w,h=cv2.boundingRect(contours[outer])
    if w<8 or h<8:return []
    minimum=ink.size*.0005
    centroids=[]
    for i,d in enumerate(depths):
        if d!=2 or areas[i]<minimum:continue
        bx,by,bw,bh=cv2.boundingRect(contours[i])
        if areas[i]/max(bw*bh,1)<0.5:continue                # stroke-pinch sliver
        if bw>=w*.95 and bh>=h*.95:continue                   # not a feature
        moments=cv2.moments(contours[i],binaryImage=False)
        if moments["m00"]==0:continue
        mx,my=moments["m10"]/moments["m00"],moments["m01"]/moments["m00"]
        centroids.append(((mx-x)/w,(my-y)/h))
    return centroids

def _position_fidelity(source_centroids:list[tuple[float,float]],render_centroids:list[tuple[float,float]],tolerance:float=.16)->tuple[float,list[tuple[float,float]]]:
    """Fraction of doodle openings with a rendered opening at the same relative spot.

    IoU on bounding-box-normalized masks is blind to mirrored/relocated features;
    this pins each demanded feature to a location. Greedy nearest matching, one
    rendered hole satisfies at most one demanded hole.
    Returns (fidelity, unmatched_source_centroids) so the supervisor can be told
    exactly WHICH openings are missing, not just how many.
    """
    if not source_centroids:return 1.0,[]
    if not render_centroids:return 0.0,list(source_centroids)
    used=set();matched=0;missing:list[tuple[float,float]]=[]
    for sx,sy in sorted(source_centroids,key=lambda p:(p[1],p[0])):
        best=None;best_d=tolerance*tolerance
        for j,(rx,ry) in enumerate(render_centroids):
            if j in used:continue
            d=(sx-rx)**2+(sy-ry)**2
            if d<=best_d:best,best_d=j,d
        if best is not None:
            used.add(best);matched+=1
        else:
            missing.append((sx,sy))
    return matched/len(source_centroids),missing

def projection_scores(source:bytes,evidence:dict[str,Any],views:dict[str,Path],primary_view:str="front",projection_standard:str="third-angle")->tuple[dict[str,float],dict[str,dict[str,int]]]:
    image=_decode(source);assigned=assign_view_groups(evidence,primary_view,projection_standard)
    if image is None:return {},{}
    h,w=image.shape[:2];scores={};topology={}
    for direction,group in assigned.items():
        path=views.get(direction)
        if not path or not path.exists():continue
        x,y,gw,gh=group["bbox_normalized"];x0,y0,x1,y1=max(0,int(x*w)),max(0,int(y*h)),min(w,int((x+gw)*w)),min(h,int((y+gh)*h))
        crop=image[y0:y1,x0:x1];original,source_holes=_normalized_profile(crop,render=False);rendered_image=_decode(path.read_bytes())
        if rendered_image is None:continue
        rendered,render_holes=_normalized_profile(rendered_image,render=True)
        union=np.count_nonzero(cv2.bitwise_or(original,rendered));intersection=np.count_nonzero(cv2.bitwise_and(original,rendered))
        iou=intersection/union if union else 0
        edge_score=_edge_similarity(_normalized_edges(crop,render=False),_normalized_edges(rendered_image,render=True))
        scores[direction]=round(max(iou,edge_score),3)
        crop_profiles=_crop_internal_profile_count(crop)
        source_centroids=_profile_centroids(crop,render=False)
        render_centroids=_profile_centroids(rendered_image,render=True)
        fidelity,missing_centroids=_position_fidelity(source_centroids,render_centroids) if source_centroids else (None,[])
        topology[direction]={"source_internal_profiles":source_holes,"rendered_internal_profiles":render_holes,
                             "crop_internal_profiles":crop_profiles,
                             "source_aspect":round((x1-x0)/max(y1-y0,1),3),
                             "rendered_aspect":round(_render_aspect(rendered_image),3),
                             "source_opening_centroids":[[round(a,3),round(b,3)] for a,b in source_centroids],
                             "rendered_opening_centroids":[[round(a,3),round(b,3)] for a,b in render_centroids],
                             **({"missing_opening_centroids":[[round(a,3),round(b,3)] for a,b in missing_centroids]} if missing_centroids else {}),
                             **({"feature_position_fidelity":round(fidelity,3)} if fidelity is not None else {})}
        if fidelity is not None:
            scores[direction]=round(min(scores[direction],0.35+0.65*fidelity),3)
    return scores,topology

def _render_aspect(image:np.ndarray)->float:
    gray=cv2.cvtColor(image,cv2.COLOR_BGR2GRAY) if image.ndim==3 else image
    border=np.concatenate((gray[0],gray[-1],gray[:,0],gray[:,-1]))
    bg=float(np.median(border))
    mask=(np.abs(gray.astype(float)-bg)>18).astype(np.uint8)*255
    points=cv2.findNonZero(mask)
    if points is None:return 0.0
    x,y,w,h=cv2.boundingRect(points);return w/max(h,1)

def evaluate_candidate(*,stl:Path|None,health:dict[str,Any]|None,scad:str,views:dict[str,Path],source:bytes,evidence:dict[str,Any],spec:dict[str,Any],target_dimension:str,strict:bool,primary_view:str="front",projection_standard:str="third-angle",dimension_tolerance:float=.05)->dict[str,Any]:
    failures=[];gates={"compiled":bool(stl and health),"topology":False,"dimensions":True,"shape_sanity":True,"features":True,"projections":True,"build_envelope":True};topology_score=0.0
    if health:
        gates["topology"]=bool(health["watertight"] and (health["components"]==1 or not strict));topology_score=(22 if health["watertight"] else 0)+(18 if health["components"]==1 else 0)+(5 if health["triangles"]>=12 else 0)
        # BambuLab-class FDM build volume (X1C/P1S: 256 mm cube). A part that
        # cannot fit is unprintable regardless of how well it matches the doodle.
        max_extent=max(health.get("extents_mm") or [0])
        if max_extent>BUILD_CUBE_MM:
            gates["build_envelope"]=False
            failures.append(f"part does not fit the 256 mm build cube: largest extent {max_extent:g} mm")
    if not gates["compiled"]:failures.append("OpenSCAD did not produce a valid STL")
    if health and not health["watertight"]:failures.append("mesh is not watertight")
    if health and strict and health["components"]!=1:failures.append(f"mesh has {health['components']} disconnected components")
    dimension_score=20.0
    try:
        target=float(target_dimension);actual=max(health["extents_mm"]) if health else 0;error=abs(actual-target)/max(target,1)
        dimension_score=max(0,20*(1-min(error,1)));gates["dimensions"]=error<=dimension_tolerance
        if not gates["dimensions"]:failures.append(f"maximum dimension is {actual:g} mm; target is {target:g} mm (tolerance {dimension_tolerance:.0%})")
    except(TypeError,ValueError):pass
    dimensions=spec.get("dimensions") if isinstance(spec,dict) else None
    if health and isinstance(dimensions,dict):
        aliases=(("max_width","width","estimated_width"),("max_depth","depth","estimated_depth"),("max_height","height","estimated_height"))
        mismatches=[]
        for axis,(actual,keys) in enumerate(zip(health["extents_mm"],aliases)):
            expected=next((dimensions.get(key) for key in keys if dimensions.get(key) not in (None,"")),None)
            try: expected=float(expected)
            except (TypeError,ValueError): continue
            ratio=float(actual)/expected if expected>0 else 1
            # Window must catch axis COLLAPSE (flat-slab repairs) without
            # punishing good meshes over noisy LLM size estimates: reg4/101's
            # mesh matched GT exactly (Y=60) yet spec estimated 30 (ratio 2.0).
            if ratio < .22 or ratio > 2.6:mismatches.append(f"{'XYZ'[axis]}={actual:g} mm vs expected {expected:g} mm")
        if mismatches:
            gates["shape_sanity"]=False
            failures.append("degenerate or implausible axis dimensions: "+", ".join(mismatches))
    projections,profile_topology=projection_scores(source,evidence,views,primary_view,projection_standard)
    sheet_expected=evidence.get("closed_internal_profile_count",0)
    # Fair requirement = profiles the drawing demands of the SINGLE best-scored
    # registered view (crop-local count), not the whole-sheet total which mixes
    # every view's features and is unreachable by any one projection.
    if profile_topology:
        expected,best_direction=max(((t.get("crop_internal_profiles",0),d) for d,t in profile_topology.items()),key=lambda item:(item[0],projections.get(item[1],0)))
    else:
        expected,best_direction=sheet_expected,primary_view
    observed=max((t.get("rendered_internal_profiles",0) for t in profile_topology.values()),default=0)
    if expected:
        gates["features"]=observed>=expected
        if not gates["features"]:
            hint=""
            best_info=profile_topology.get(best_direction) or {}
            missing=best_info.get("missing_opening_centroids") or []
            if missing:
                pts="; ".join(f"(u={a},v={b})" for a,b in missing[:6])
                hint=f" Missing at these view-local centres — add cutters there: {pts}."
            failures.append(f"required internal profiles are missing: {best_direction} view demands {expected}, best rendered view has {observed}.{hint}")
    feature_score=20 if not expected else 20*min(observed/expected,1)
    if projections:
        gates["projections"]=all(v>=.45 for v in projections.values())
        if not gates["projections"]:
            weak=", ".join(f"{name} similarity {value:.2f}" for name,value in sorted(projections.items()) if value<.45)
            failures.append(f"CAD projections poorly match the drawing: {weak} (need >= 0.45). Check which side/thickness the failing view shows: mirror depth, wall position and bar proportions to match that view exactly.")
        misplaced=[d for d,t in profile_topology.items() if t.get("feature_position_fidelity") is not None and t["feature_position_fidelity"]<.5]
        if misplaced:
            gates["features"]=False
            failures.append("features exist but sit at the wrong positions in "+", ".join(misplaced)+
                            " view(s): match each opening's location (u,v within the outer profile) to the drawing; "+
                            "check the cad_mapping signs (front: u->+X v->-Z; top: u->+X v->-Y i.e. sheet-down is the FRONT of the part)")
    visual_score=15*(sum(projections.values())/len(projections)) if projections else 0;total=round(topology_score+dimension_score+feature_score+visual_score,1)
    return {"score":total,"valid_mesh":gates["topology"],"accepted":all(gates.values()),"mandatory_gates":gates,"scores":{"topology":round(topology_score,1),"dimensions":round(dimension_score,1),"features":round(feature_score,1),"projections":round(visual_score,1)},"projection_similarity":projections,"profile_topology":profile_topology,"failures":failures}
