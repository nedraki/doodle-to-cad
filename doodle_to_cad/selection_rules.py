"""Bounded geometric rules; topology indices are never persistent identifiers."""

TOLERANCE = 0.001


def inside(bounds, container):
    return all(bounds[0][i] >= container[0][i]-TOLERANCE and
               bounds[1][i] <= container[1][i]+TOLERANCE for i in range(3))


def planar_axis(bounds):
    flat=[i for i in range(3) if abs(bounds[1][i]-bounds[0][i]) < TOLERANCE]
    return flat[0] if len(flat)==1 else None


def match_faces(rule, output_id, output_bounds, faces, operations, body_bounds):
    """Return transient indices plus status. Caller saves rule and expected count.

    faces are native tight bounds, in the current build only. Supported cutouts
    use an axis-aligned box cutter. An extreme face must match uniquely.
    """
    owner=rule.get('owner');kind=rule.get('kind')
    by_id={op['id']:op for op in operations}
    if kind=='extreme_face':
        if owner!=output_id:return {'status':'lost','reason':'Owning output feature changed','indices':[]}
        axis=rule.get('axis');side=rule.get('side')
        if type(axis) is not int or axis not in range(3) or side not in ('min','max'):
            raise ValueError('Unsupported extreme-face rule')
        coordinate=output_bounds[0 if side=='min' else 1][axis]
        found=[i for i,b in enumerate(faces) if planar_axis(b)==axis and abs(b[0][axis]-coordinate)<TOLERANCE]
        expected=1
    elif kind=='box_cutout':
        reachable=set()
        pending=[output_id]
        while pending:
            current=pending.pop()
            if current in reachable:continue
            reachable.add(current)
            operation=by_id.get(current,{})
            pending.extend(operation.get('depends_on',[]))
            pending.extend(operation[key] for key in ('left','right','body') if key in operation)
        if owner not in reachable:
            return {'status':'lost','reason':'Cutout no longer contributes to the displayed part','indices':[]}
        operation=by_id.get(owner)
        if not operation or operation['kind']!='difference' or operation.get('right')!=rule.get('cutter'):
            return {'status':'lost','reason':'Cutout feature was removed or replaced','indices':[]}
        cutter=by_id.get(rule['cutter'])
        if not cutter or cutter['kind']!='box':return {'status':'lost','reason':'Cutter is no longer a supported box','indices':[]}
        bounds=body_bounds[rule['cutter']]
        found=[]
        for i,b in enumerate(faces):
            axis=planar_axis(b)
            if axis is not None and inside(b,bounds) and any(abs(b[0][axis]-bounds[j][axis])<TOLERANCE for j in (0,1)):
                found.append(i)
        expected=rule.get('expected_faces',4)
        if type(expected) is not int or expected<1:raise ValueError('Invalid expected face count')
    else:raise ValueError('Unsupported face selection rule')
    if not found:return {'status':'lost','reason':'No matching face remains. Select again.','indices':[]}
    if len(found)!=expected:return {'status':'ambiguous','reason':'The target changed or split. Select again.','indices':[]}
    return {'status':'matched','indices':found}


def outer_vertical_edges(output_bounds, edges):
    """Straight vertical edges at outer XY corners; no arbitrary curved edges."""
    result=[]
    for i,(lo,hi) in enumerate(edges):
        if hi[2]-lo[2]<=TOLERANCE:continue
        if any(abs(hi[a]-lo[a])>=TOLERANCE for a in (0,1)):continue
        if all(any(abs(lo[a]-output_bounds[j][a])<TOLERANCE for j in (0,1)) for a in (0,1)):
            result.append(i)
    return result
