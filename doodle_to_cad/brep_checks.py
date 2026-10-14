"""BRep drawing checks and independent section measurements. No benchmark lookup."""
from pathlib import Path
import numpy as np
import networkx as nx
import trimesh
from .evaluation import projection_scores

PROJECTION_MIN = .45  # Existing evaluator threshold; fixed before these trials.
POSITION_MIN = .5


def evaluate_drawing(source, evidence, views, health, controls, maximum):
    checks=[]
    def record(name,status,detail):checks.append({'name':name,'status':status,'detail':detail})
    valid=bool(health.get('watertight') and health.get('components')==1)
    record('connected solid','passed' if valid else 'failed',
           {'watertight':health.get('watertight'),'components':health.get('components')})
    extent=max(health.get('extents_mm') or [0])
    record('requested maximum','passed' if 0<extent<=maximum+.5 else 'failed',
           {'actual_mm':extent,'limit_mm':maximum,'tolerance_mm':.5})
    scores,topology=projection_scores(source,evidence,views,controls.get('primary_view','front'),controls.get('projection_standard','third-angle'))
    for direction,score in scores.items():
        record(direction+' projection','passed' if score>=PROJECTION_MIN else 'failed',{'similarity':score,'minimum':PROJECTION_MIN})
        t=topology[direction]
        expected=t.get('crop_internal_profiles',0);actual=t.get('rendered_internal_profiles',0)
        # Openings in a different view cannot satisfy this view's requirement.
        if expected:
            record(direction+' openings','passed' if actual>=expected else 'failed',{'expected_at_least':expected,'actual':actual})
        fidelity=t.get('feature_position_fidelity')
        if fidelity is not None:
            record(direction+' opening positions','passed' if fidelity>=POSITION_MIN else 'failed',{'fidelity':fidelity,'minimum':POSITION_MIN,'missing':t.get('missing_opening_centroids',[])})
    if not scores:record('view registration','unverified','No usable drawing-to-render view pair.')
    record('dimensions and detailed features','unverified',
           'Projection checks cannot prove radii, bevel angles, hidden depth or section shape. Review measured features and view assignments.')
    failed=[c['name'] for c in checks if c['status']=='failed']
    return {'version':1,'accepted':False,'status':'failed' if failed else 'unverified',
            'build_status':'passed','geometry_status':'passed' if valid else 'failed',
            'projection_status':'failed' if any(c['status']=='failed' for c in checks if 'projection' in c['name'] or 'opening' in c['name']) else ('passed' if scores else 'unverified'),
            'checks':checks,'projection_similarity':scores,'profile_topology':topology,
            'failures':failed+['Detailed drawing features and view assignments require review.'],
            'scope':'Partial automatic checks. No drawing acceptance from solid validity alone.'}


def sample_segments(points, spacing=.1):
    points=np.asarray(points,dtype=float)
    if len(points)<2:raise ValueError('Expected a contour with at least two points')
    return np.concatenate([a+(b-a)*np.linspace(0,1,max(2,int(np.ceil(np.linalg.norm(b-a)/spacing))+1))[:,None] for a,b in zip(points[:-1],points[1:])])


def section_check(mesh, axis, position, expected_loops, tolerance_mm):
    """Compare an actual mesh section with independently declared planar contours.

    Expected coordinates are in the two remaining world axes. Caller owns the
    evidence and its tolerance. No recipe operation/parameter is used as proof.
    """
    normal=np.eye(3)[axis];origin=normal*position
    segments=trimesh.intersections.mesh_plane(mesh,normal,origin)
    if not len(segments):return {'status':'failed','reason':'Required section is absent'}
    axes=[i for i in range(3) if i!=axis]
    graph=nx.Graph()
    for segment in segments:
        graph.add_edge(*(tuple(np.round(point,6)) for point in segment))
    loops=nx.number_connected_components(graph)
    if loops!=len(expected_loops):
        return {'status':'failed','reason':'Section loop count differs','actual_loops':loops,'expected_loops':len(expected_loops)}
    actual=np.concatenate([sample_segments(segment[:,axes]) for segment in segments])
    target=np.concatenate([sample_segments(p) for p in expected_loops])
    def distance(a,b):
        return max(float(np.sqrt(((chunk[:,None,:]-b[None,:,:])**2).sum(axis=2).min(axis=1)).max())
                   for chunk in np.array_split(a,max(1,int(np.ceil(len(a)/256)))))
    error=max(distance(actual,target),distance(target,actual))
    return {'status':'passed' if error<=tolerance_mm else 'failed','symmetric_boundary_error_mm':round(float(error),5),
            'tolerance_mm':tolerance_mm,'sampling_spacing_mm':.1,'axis':int(axis),'position_mm':position,'loops':loops}
