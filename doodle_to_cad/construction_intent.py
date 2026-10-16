"""A drawing-grounded construction plan, saved before executable recipe generation."""
PROMPT_VERSION='construction-intent-9'
PROMPT='''Read the drawing and its declared view controls. Produce a construction plan, not executable code.
Return JSON with: view_frame, features, connections, edit_rules, unresolved, and optional clarification.
view_frame: string explaining the labelled views and world axes (X width, Y depth, Z height).
features: list of objects with exactly id, shape, section, axis_or_plane, dimensions, placement, evidence.
All feature fields are strings except dimensions, which is a list of strings containing only drawing dimensions or explicitly marked assumptions.
placement gives start/end coordinates or centre and direction in the world frame, with the arithmetic needed to locate the feature.
evidence quotes or describes the visible marks that support the feature. Never claim an inferred hidden detail is observed.
connections, edit_rules and unresolved: lists of strings.

Resolve view labels BEFORE placing geometry. Front uses XZ; top uses XY; right uses YZ. If a path is shown in a top view, its entire centreline is in XY and its section thickness is along Z. A vertical line on that sheet is along Y, not Z. A circular end section applies to every segment, including straight segments whose side outlines look rectangular.
For a curved path, state each straight segment's axis, each bend's plane, and how their endpoints meet. An XY arc goes from +X counterclockwise. Do not place a horizontal bend on unrelated vertical legs. Raise the section centre above the bed by its radius; do not rotate the part merely to lift it.
For edge treatments, distinguish flat bevels from circular rounds. State which edges change and which remain sharp. The entire outer envelope and protected dimensions must remain fixed when only an edge radius changes.
Dimensions and geometric arithmetic must be consistent across views. For each editable parameter, state the dependent placements that must move with it. If the drawing does not establish a construction value, record the uncertainty rather than inventing certainty.
For an opening whose through-hole versus recess meaning is genuinely missing from the drawing AND user notes, add clarification: {"feature_id":"an existing feature id","feature_label":"short location and description","reason":"what the drawing does not establish","kind":"opening_extent"}. Keep this decision in unresolved until answered. Ask only about one opening at a time. Do not ask when a section/side view, a THROUGH label, or the user answer establishes the meaning. Do not ask to repair a modeling failure or to handle an unsupported operation.
User answers in clarification_answers are authoritative design intent for the named feature. Preserve feature IDs when replanning. For recess, depth_mm is supplied by the user. Do not ask the same question again. Put other missing construction decisions in unresolved for the recipe planner. It must disclose a permitted assumption or retain the unresolved value so recipe validation stops the build. Default policy: visible proportions and a missing uniform body thickness may use an explicit, editable assumption when no fit, mating interface, cavity floor or required connection depends on the missing value. Label that value ASSUMED in dimensions and expose it for editing. Do not also put an accepted assumption in unresolved. unresolved contains ONLY decisions that prevent a supported construction, such as conflicting views, unknown opening extent, or a missing fit-critical dimension. Never silently choose through-hole versus recess or recess depth. An opening answer takes priority over all earlier assumptions.
For a flat part shown in TOP with a constant outline through its thickness, plan a closed XY profile and Z extrusion. Include visible notches, line/arc boundaries and through-opening loops. This first profile operation supports XY only. Preserve the outline when thickness changes. Other planes and spline profiles are unsupported.
For an XY bend with a rectangular end section, preserve that section along the path. The supported rectangular sweep is one circular bend of 1–180 degrees with optional tangent straight ends. Its section stays upright along Z. State centreline radius separately from inner/outer radii, both straight lengths, section width and Z height. Straight centreline endpoints meet the centreline radius, not the outer radius. A counterclockwise arc has tangent directions +Y/-X/-Y/+X at angles 0/90/180/270 degrees. Clockwise traversal has opposite tangent directions and a negative angular sweep. Both traversal orders are supported. Verify both joins against the chosen direction. Do not replace a rectangular section with a round pipe. Preserve the XY path when section height changes. Other path planes, sharp joins, multiple bends and splines are unsupported.
Keep the plan concise. Do not use benchmark references or assume a part template.'''


def validate_plan(plan):
    if not isinstance(plan,dict) or set(plan)-{'clarification'}!={'view_frame','features','connections','edit_rules','unresolved'}:
        raise ValueError('Expected construction plan fields')
    def text(v):
        if not isinstance(v,str) or not 1<=len(v)<=2500:raise ValueError('Expected bounded construction-plan text')
    text(plan['view_frame'])
    if not isinstance(plan['features'],list) or not 1<=len(plan['features'])<=128:raise ValueError('Expected 1–128 planned features')
    ids=set()
    for f in plan['features']:
        if not isinstance(f,dict) or set(f)!={'id','shape','section','axis_or_plane','dimensions','placement','evidence'}:raise ValueError('Invalid planned feature fields')
        for key,value in f.items():
            if key=='dimensions' and isinstance(value,list):
                if not 1<=len(value)<=32:raise ValueError('Expected 1–32 dimension statements')
                for item in value:text(item)
            else:text(value)
        if f['id'] in ids:raise ValueError('Duplicate planned feature ID')
        ids.add(f['id'])
    for key in ['connections','edit_rules','unresolved']:
        if not isinstance(plan[key],list) or len(plan[key])>128:raise ValueError('Expected bounded construction-plan list')
        for value in plan[key]:text(value)
    question=plan.get('clarification')
    if question is not None:
        if not isinstance(question,dict) or set(question)!={'feature_id','feature_label','reason','kind'}:
            raise ValueError('Invalid clarification fields')
        for value in question.values():text(value)
        if question['kind']!='opening_extent' or question['feature_id'] not in ids:
            raise ValueError('Unsupported clarification or unknown feature')
    return plan
