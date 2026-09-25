from doodle_to_cad.model_client import CompatibleModelClient, extract_json
from doodle_to_cad.pipeline import Pipeline
from doodle_to_cad.config import Settings
from doodle_to_cad.geometry import analyze_image, label_view_geometry
from doodle_to_cad.evaluation import _render_internal_profile_count, assign_view_groups, evaluate_candidate
from doodle_to_cad.design_plan import normalize_design_plan
from doodle_to_cad.preflight import preflight_scad
import cv2
import numpy as np
import asyncio


def test_model_choice_prefers_vision():
    assert CompatibleModelClient._choose(["text-model", "Qwen3-VL-30B"]) == "Qwen3-VL-30B"


def test_model_choice_uses_first_fallback():
    assert CompatibleModelClient._choose(["local-model", "other"]) == "local-model"


def test_extract_fenced_json():
    assert extract_json("```json\n{\"object\":\"chair\"}\n```")["object"] == "chair"


def test_clean_scad():
    assert Pipeline._clean_scad("```scad\nmodule part(){ cube(10); }\npart();\n```").startswith("module part")


def test_thinking_setting_is_boolean():
    # The checked-in/default value can be overridden by the user's .env.
    assert isinstance(Settings().enable_thinking, bool)


def test_sheet_groups_views_but_keeps_nested_cutouts_inside_parent():
    image = np.full((500, 500, 3), 255, np.uint8)
    cv2.rectangle(image, (100, 40), (400, 130), (0, 0, 0), 5)
    cv2.rectangle(image, (80, 280), (420, 460), (0, 0, 0), 5)
    cv2.circle(image, (180, 360), 30, (0, 0, 0), 5)
    cv2.circle(image, (320, 360), 30, (0, 0, 0), 5)
    _, encoded = cv2.imencode(".png", image)
    evidence, _ = analyze_image(encoded.tobytes())
    assert evidence["view_group_count"] == 2
    assert evidence["closed_internal_profile_count"] >= 2
    assert len(evidence["view_geometry"]) == 2
    primary=max(evidence["view_geometry"],key=lambda view:len(view["internal_profiles"]))
    assert len(primary["internal_profiles"]) >= 2
    assert all(0 <= value <= 1 for profile in primary["internal_profiles"] for value in profile["center_view_normalized"])


def test_evaluator_rejects_missing_required_cutouts(tmp_path):
    evaluation = evaluate_candidate(stl=None, health=None, scad="cube([120,80,2]);",
        views={}, source=b"", evidence={}, target_dimension="120", strict=True,
        spec={"features":[{"type":"through_cutout"}]})
    assert not evaluation["accepted"]
    assert not evaluation["mandatory_gates"]["compiled"]


def test_evaluator_scores_valid_scaled_featured_mesh():
    health={"watertight":True,"components":1,"triangles":100,"extents_mm":[120,80,2],"volume_mm3":1000}
    evaluation=evaluate_candidate(stl=object(),health=health,scad="difference(){cube(1);cylinder(2);}",
        views={},source=b"",evidence={},target_dimension="120",strict=True,spec={"features":[{"type":"hole"}]})
    assert evaluation["valid_mesh"]
    assert evaluation["score"] >= 70


def test_dimension_is_a_mandatory_gate_even_with_healthy_mesh():
    health={"watertight":True,"components":1,"triangles":100,"extents_mm":[72,65,15],"volume_mm3":1000}
    evaluation=evaluate_candidate(stl=object(),health=health,scad="cube(1);",views={},source=b"",evidence={},
        target_dimension="120",strict=True,spec={})
    assert not evaluation["accepted"]
    assert not evaluation["mandatory_gates"]["dimensions"]


def test_view_registration_obeys_third_and_first_angle():
    evidence={"view_groups":[
        {"center_normalized":[.5,.2],"relative_size":.1},
        {"center_normalized":[.5,.7],"relative_size":.4}]}
    assert assign_view_groups(evidence,"front","third-angle")["top"]["center_normalized"]==[.5,.2]
    assert assign_view_groups(evidence,"front","first-angle")["bottom"]["center_normalized"]==[.5,.2]


def test_view_registration_obeys_horizontal_projection_standard():
    evidence={"view_groups":[{"center_normalized":[.3,.5],"relative_size":.4},{"center_normalized":[.8,.5],"relative_size":.1}]}
    assert assign_view_groups(evidence,"front","third-angle")["right"]["center_normalized"]==[.8,.5]
    assert assign_view_groups(evidence,"front","first-angle")["left"]["center_normalized"]==[.8,.5]


def _g(cx,cy,w=0.3,h=0.3,size=None):
    return {"center_normalized":[cx,cy],"bbox_normalized":[cx-w/2,cy-h/2,w,h],
            "relative_size":size if size is not None else round(w*h,4)}


def test_equal_area_stack_assigns_lower_group_to_front():
    # Cube-like sheet: front and top have identical area. The LOWER group is the
    # front view in third-angle; naive largest-first-wins picks the topmost.
    evidence={"view_groups":[_g(.5,.2,0.3,0.3),_g(.5,.7,0.3,0.3)]}
    result=assign_view_groups(evidence,"front","third-angle")
    assert result["front"]["center_normalized"]==[.5,.7]
    assert result["top"]["center_normalized"]==[.5,.2]


def test_side_larger_right_view_does_not_hijack_front():
    # Right view's bbox is slightly larger (stray stroke). The left group stays
    # 'front'; the larger right neighbour must not be relabeled and push the real
    # front into a phantom 'left' slot.
    evidence={"view_groups":[_g(.28,.55,0.3,0.3,0.100),_g(.72,.55,0.33,0.33,0.120)]}
    result=assign_view_groups(evidence,"front","third-angle")
    assert result["front"]["center_normalized"]==[.28,.55]
    assert result["right"]["center_normalized"]==[.72,.55]
    assert "left" not in result


def test_title_block_cannot_steal_the_top_slot():
    # Title scribble above the real top view: the aligned, nearer group wins the
    # 'top' slot and the real top view is not silently dropped by arrival order.
    evidence={"view_groups":[_g(.5,.10,0.2,0.02,0.01),_g(.5,.25,0.3,0.06,0.05),_g(.5,.65,0.4,0.35,0.15)]}
    result=assign_view_groups(evidence,"front","third-angle")
    assert result["front"]["center_normalized"]==[.5,.65]
    assert result["top"]["center_normalized"]==[.5,.25]


def test_three_view_l_layout_third_angle():
    evidence={"view_groups":[_g(.25,.20,0.24,0.05,0.03),_g(.25,.75,0.24,0.30,0.12),_g(.75,.75,0.05,0.30,0.03)]}
    result=assign_view_groups(evidence,"front","third-angle")
    assert result["front"]["center_normalized"]==[.25,.75]
    assert result["top"]["center_normalized"]==[.25,.20]
    assert result["right"]["center_normalized"]==[.75,.75]


def test_first_angle_l_layout_mirror():
    evidence={"view_groups":[_g(.25,.20,0.24,0.05,0.03),_g(.25,.75,0.24,0.30,0.12),_g(.75,.75,0.05,0.30,0.03)]}
    result=assign_view_groups(evidence,"front","first-angle")
    assert result["front"]["center_normalized"]==[.25,.75]
    assert result["bottom"]["center_normalized"]==[.25,.20]
    assert result["left"]["center_normalized"]==[.75,.75]


def test_registered_view_crops_are_labeled_and_saved(tmp_path):
    image=np.full((300,300,3),255,np.uint8)
    cv2.rectangle(image,(80,20),(220,60),(0,0,0),4)
    cv2.rectangle(image,(70,130),(230,260),(0,0,0),4)
    ok,encoded=cv2.imencode(".png",image);assert ok
    evidence={"view_groups":[
        {"bbox_normalized":[.26,.06,.48,.15],"center_normalized":[.5,.135],"relative_size":.08},
        {"bbox_normalized":[.23,.43,.54,.44],"center_normalized":[.5,.65],"relative_size":.35},
    ]}
    crops=Pipeline._registered_view_crops(encoded.tobytes(),evidence,{"primary_view":"front","projection_standard":"third-angle"},tmp_path)
    assert set(crops)=={"front","top"}
    assert (tmp_path/"registered-front.png").exists()
    assert (tmp_path/"registered-top.png").exists()


def test_design_plan_normalizes_frame_and_cut_operations():
    plan=normalize_design_plan({"parts":[{"primitive":"extruded plate"}],"features":[{"type":"through_cutout","owning_part":"panel","geometry":"slot"}]})
    assert plan["family"]=="extrude"
    assert plan["coordinate_frame"]["front"]=={"plane":"XZ","view_axis":"Y"}
    assert any(op["operation"]=="through_cut" for op in plan["operations"])


def test_design_plan_augments_incomplete_model_plan_with_feature_operations():
    spec={"construction_plan":{"family":"extrude","operations":[{"id":"body","operation":"extrude"}]},
          "features":[{"id":"top_slot","type":"through_hole"},{"id":"lower_slots","type":"slot"}]}
    plan=normalize_design_plan(spec)
    assert {op["id"] for op in plan["operations"]} >= {"body","top_slot","lower_slots"}


def test_view_geometry_has_explicit_cad_coordinate_mapping():
    evidence={"view_geometry":[{"view_id":"view_1"}],"view_groups":[{"view_id":"view_1"}]}
    result=label_view_geometry(evidence,{"front":evidence["view_groups"][0]})
    view=result["view_geometry"][0]
    assert view["direction"]=="front"
    assert view["cad_mapping"]=={"plane":"XZ","view_axis":"Y","u_maps_to":"+X","v_maps_to":"-Z"}


def test_top_view_contract_maps_down_to_minus_y():
    # Third-angle drafting convention + measured OpenSCAD top-camera behaviour:
    # on the sheet the top view's DOWN direction is the FRONT of the part (-Y);
    # +Y (back) points toward the top of the sheet. Verified by
    # experiments/coord_contract_probe*.py (notch at +Y renders on the TOP edge).
    evidence={"view_geometry":[{"view_id":"view_1"}],"view_groups":[{"view_id":"view_1"}]}
    result=label_view_geometry(evidence,{"top":evidence["view_groups"][0]})
    view=result["view_geometry"][0]
    assert view["cad_mapping"]["v_maps_to"]=="-Y"
    evidence2={"view_geometry":[{"view_id":"view_1"}],"view_groups":[{"view_id":"view_1"}]}
    result2=label_view_geometry(evidence2,{"bottom":evidence2["view_groups"][0]})
    assert result2["view_geometry"][0]["cad_mapping"]["v_maps_to"]=="+Y"


def test_preflight_rejects_geometry_function_and_csg_assignment():
    report=preflight_scad("function body(){ cube(1); }\nthing = cube(2);",{})
    assert not report["passed"]
    assert len(report["errors"])==2


def test_preflight_requires_difference_for_subtractive_intent():
    report=preflight_scad("module body(){ cube(10); } body();",{"features":[{"type":"through_cutout"}]})
    assert not report["passed"]


def test_preflight_rejects_observed_nonexistent_modules():
    for source in ("box([10,10,10]);", "revolve(){ polygon([[0,0],[1,0],[1,1]]); }"):
        report=preflight_scad(source,{})
        assert not report["passed"]


def test_preflight_rejects_geometry_assignment_for_extrusions():
    report=preflight_scad("outer_solid = rotate_extrude() polygon([[0,0],[1,0],[1,1]]);",{})
    assert not report["passed"]


def test_clean_scad_accepts_canonical_rotational_solid():
    source="rotate_extrude(){ polygon([[0,0],[10,0],[10,20],[0,20]]); }"
    assert Pipeline._clean_scad(source).startswith("rotate_extrude")


def test_loose_string_parts_and_features_from_model_are_supported():
    spec={"parts":["L-bracket"],"features":["L-shaped outer profile","Three rectangular through-holes"]}
    plan=normalize_design_plan(spec)
    assert plan["family"]=="ambiguous"
    assert any(op["operation"]=="through_cut" for op in plan["operations"])
    report=preflight_scad("module part(){ difference(){ cube(10); cube(2); } } part();",spec)
    assert report["passed"]
    assert report["expected_subtractive_feature_groups"]==1


def test_json_call_repairs_and_preserves_raw_response(tmp_path):
    class FakeClient:
        def __init__(self): self.calls=0
        async def chat(self,*args,**kwargs):
            self.calls+=1
            if self.calls == 2:
                assert kwargs.get("enable_thinking") is False
            return '{"object":"part" "features":[]}' if self.calls==1 else '{"object":"part","features":[]}'
    pipeline=Pipeline(Settings(),FakeClient())
    result=asyncio.run(pipeline._json_call([],tmp_path,"test"))
    assert result["object"]=="part"
    assert (tmp_path/"test.raw.txt").exists()
    assert (tmp_path/"test.parse-error.txt").exists()
    assert (tmp_path/"test.repaired.txt").exists()


def test_json_call_retries_without_thinking_when_reasoning_has_no_answer(tmp_path):
    class FakeClient:
        def __init__(self): self.calls=0
        async def chat(self,*args,**kwargs):
            self.calls+=1
            if self.calls == 1:
                raise RuntimeError("Model returned no final content (finish_reason=length)")
            if self.calls >= 2:
                assert kwargs["enable_thinking"] is False
            return '{"object":"recovered","features":[]}'
    pipeline=Pipeline(Settings(),FakeClient())
    result=asyncio.run(pipeline._json_call([],tmp_path,"interpretation"))
    assert result["object"]=="recovered"
    assert (tmp_path/"interpretation.thinking-failure.json").exists()
    assert (tmp_path/"interpretation.fallback.raw.txt").exists()
    second=asyncio.run(pipeline._json_call([],tmp_path,"supervisor"))
    assert second["object"]=="recovered"


def test_scad_call_uses_artifact_reasoning_policy_and_preserves_output(tmp_path):
    class FakeClient:
        async def chat(self, *args, **kwargs):
            assert kwargs["enable_thinking"] is False
            assert kwargs["max_tokens"] == Settings().code_max_tokens
            return "```scad\nmodule part(){ cube(10); }\npart();\n```"
    result=asyncio.run(Pipeline(Settings(),FakeClient())._scad_call([],tmp_path,"generation"))
    assert result.startswith("module part")
    assert (tmp_path/"generation.raw.scad.txt").exists()


def test_rendered_internal_profiles_are_mandatory(tmp_path):
    source=np.full((300,300,3),255,np.uint8);cv2.rectangle(source,(30,30),(270,270),(0,0,0),5)
    cv2.circle(source,(100,130),30,(0,0,0),5);cv2.circle(source,(200,130),30,(0,0,0),5)
    ok,encoded=cv2.imencode(".png",source);assert ok
    render=np.full((300,300,3),(245,245,220),np.uint8);cv2.rectangle(render,(30,30),(270,270),(20,170,190),-1)
    render_path=tmp_path/"front.png";cv2.imwrite(str(render_path),render)
    health={"watertight":True,"components":1,"triangles":100,"extents_mm":[120,100,10],"volume_mm3":1000}
    evidence={"view_groups":[{"bbox_normalized":[0,0,1,1],"center_normalized":[.5,.5],"relative_size":1}],"closed_internal_profile_count":2}
    evaluation=evaluate_candidate(stl=object(),health=health,scad="difference(){cube(1);}",views={"front":render_path},
        source=encoded.tobytes(),evidence=evidence,target_dimension="120",strict=True,spec={})
    assert not evaluation["mandatory_gates"]["features"]
    assert not evaluation["accepted"]


def test_shaded_rendered_openings_are_counted_from_boundaries():
    image=np.full((400,700,3),(245,245,220),np.uint8)
    cv2.rectangle(image,(100,80),(600,330),(30,190,210),-1)
    for x in (160,310,460):
        cv2.rectangle(image,(x,160),(x+80,250),(55,110,75),-1)
    assert _render_internal_profile_count(image)==3


def test_evaluator_rejects_axis_collapsed_repair():
    health={"watertight":True,"components":1,"triangles":16,"extents_mm":[96,5,5],"volume_mm3":2300}
    evaluation=evaluate_candidate(stl=object(),health=health,scad="cube(1);",views={},source=b"",
        evidence={},target_dimension="120",strict=True,
        spec={"dimensions":{"max_width":120,"estimated_depth":10,"estimated_height":60}})
    assert not evaluation["mandatory_gates"]["shape_sanity"]
    assert any("implausible axis dimensions" in failure for failure in evaluation["failures"])


def _png_bytes():
    image=np.full((100,100,3),255,np.uint8);cv2.rectangle(image,(20,20),(80,80),(0,0,0),3)
    ok,encoded=cv2.imencode(".png",image);assert ok
    return encoded.tobytes()


def test_generate_endpoint_is_async_job_with_polling(monkeypatch):
    from fastapi.testclient import TestClient
    import doodle_to_cad.app as api

    client_app = TestClient(api.app)
    submitted = {}

    async def fake_generate(self, image, mime, notes, dimension, extra=None, controls=None,
                            run_id=None, on_stage=None):
        submitted["run_id"] = run_id
        if on_stage: on_stage("interpreting")
        return {"id": run_id, "success": True, "evaluation": {"score": 99},
                "attempts": [], "spec": {}, "model": "fake", "duration_seconds": 0.1,
                "files": {"scad": f"/results/{run_id}/model.scad", "stl": None,
                          "attempts": None, "overlay": None, "views": {}}}

    monkeypatch.setattr(api.Pipeline, "generate", fake_generate)
    response = client_app.post("/api/generate",
        files={"image": ("primary.png", _png_bytes(), "image/png")},
        data={"notes": "test", "dimension": "120", "view_directions": "[]"})
    assert response.status_code == 200
    job_id = response.json()["job_id"]
    assert job_id == submitted["run_id"]
    # The response must arrive immediately and the job must be pollable.
    status = client_app.get(f"/api/generate/{job_id}")
    assert status.status_code == 200
    payload = status.json()
    assert payload["status"] == "done"
    assert payload["result"]["success"] is True
    assert client_app.get("/api/generate/ffffffffffff").status_code == 404


def test_generate_endpoint_reports_job_failure(monkeypatch):
    from fastapi.testclient import TestClient
    import doodle_to_cad.app as api

    client_app = TestClient(api.app)

    async def failing_generate(self, image, mime, notes, dimension, extra=None, controls=None,
                               run_id=None, on_stage=None):
        raise RuntimeError("model exploded")

    monkeypatch.setattr(api.Pipeline, "generate", failing_generate)
    response = client_app.post("/api/generate",
        files={"image": ("primary.png", _png_bytes(), "image/png")},
        data={"notes": "", "dimension": "", "view_directions": "[]"})
    assert response.status_code == 200
    payload = client_app.get(f"/api/generate/{response.json()['job_id']}").json()
    assert payload["status"] == "error"
    assert "model exploded" in payload["error"]["message"]


def test_generate_endpoint_rejects_bad_view_directions():
    from fastapi.testclient import TestClient
    import doodle_to_cad.app as api

    client_app = TestClient(api.app)
    response = client_app.post("/api/generate",
        files={"image": ("primary.png", _png_bytes(), "image/png")},
        data={"view_directions": "not-json"})
    assert response.status_code == 422

# ---- parametric edit surface (params.py) ----
from doodle_to_cad.params import extract_params, rewrite_params

SAMPLE_SCAD = '''
// plate params
plate_width = 80;   // mm overall width
plate_thickness = 6.5;
hole_diameter = 8;  // through hole
hole_count = 4;     // number of holes
module body() {
  local_offset = 3;
  cube([plate_width, plate_thickness, local_offset]);
}
body();
'''

def test_extract_params_only_top_level_numeric():
    names = [p.name for p in extract_params(SAMPLE_SCAD)]
    assert names == ["plate_width", "plate_thickness", "hole_diameter", "hole_count"]

def test_extract_params_classifies_units_and_bounds():
    params = {p.name: p for p in extract_params(SAMPLE_SCAD)}
    assert params["hole_count"].unit == "count" and params["hole_count"].step == 1
    assert params["plate_width"].low < 80 < params["plate_width"].high
    assert params["hole_diameter"].unit == "radius/diameter"
    assert params["plate_width"].description == "mm overall width"

def test_rewrite_params_edits_only_top_level_assignment():
    text, applied = rewrite_params(SAMPLE_SCAD, {"plate_width": 99.5, "ghost": 1})
    assert applied == ["plate_width"]
    assert "plate_width = 99.5;" in text
    assert "cube([plate_width" in text          # usages untouched
    assert "local_offset = 3;" in text          # module-local assignment untouched

def test_rewrite_params_rejects_bad_names_and_values():
    text, applied = rewrite_params(SAMPLE_SCAD, {"drop table": 5, "plate_width": None})
    assert applied == []
    assert text == SAMPLE_SCAD


# ---- intent refinement (refine.py) ----
from doodle_to_cad.refine import classify_profile, refine_view, refine_evidence

def _prof(pid, poly, cx, cy, w, h):
    return {"profile_id": pid, "polygon_view_normalized": poly,
            "center_view_normalized": [cx, cy], "bbox_view_normalized": [cx-w/2, cy-h/2, w, h]}

def _circle_poly(cx, cy, r, n=24, wobble=0.0):
    import math as _m
    pts = []
    for i in range(n):
        t = i/n*2*_m.pi
        rr = r*(1+wobble*_m.sin(3*t))
        pts.append([cx+rr*_m.cos(t), cy+rr*_m.sin(t)])
    return pts

def _rect_poly(cx, cy, w, h):
    return [[cx-w/2,cy-h/2],[cx+w/2,cy-h/2],[cx+w/2,cy+h/2],[cx-w/2,cy+h/2]]

def test_classify_wobbly_circle_and_rect():
    shape, conf = classify_profile(_prof("c", _circle_poly(.5,.5,.08,24,.10), .5,.5,.16,.16))
    assert shape == "circle" and conf >= .5
    shape, conf = classify_profile(_prof("r", _rect_poly(.5,.5,.18,.10), .5,.5,.18,.10))
    assert shape == "rectangle"

def test_refine_view_aligns_row_and_unifies_sizes():
    # Three hand-drawn circles: centres y=0.498/0.502/0.500, sizes .079/.081/.080
    profiles = [
        _prof("a", _circle_poly(.20,.498,.040,24), .20,.498,.079,.079),
        _prof("b", _circle_poly(.40,.502,.041,24), .40,.502,.081,.083),
        _prof("c", _circle_poly(.60,.500,.040,24), .60,.500,.080,.080),
    ]
    out = refine_view({"view_id": "v1", "internal_profiles": profiles})
    centres = {p["profile_id"]: p["center_view_normalized"] for p in out["profiles"]}
    assert len({c[1] for c in centres.values()}) == 1          # one canonical row
    sizes = [p["size_view_normalized"] for p in out["profiles"]]
    assert len({s[1] for s in sizes}) == 1                      # one canonical size
    assert all("center_v" in p["snapped"] or abs(p["center_view_normalized"][1]-.5)<1e-9 for p in out["profiles"])

def test_refine_evidence_mode_off():
    ev = {"view_geometry": [{"view_id": "v", "internal_profiles": []}]}
    assert refine_evidence(ev, "as_drawn") is None
    assert refine_evidence(ev, "regularize")["refine_mode"] == "regularize"


def test_preflight_ignores_comment_prose():
    # reg1/103 incident: "// Origin: Bottom-Left-Front corner of the bounding
    # box (0,0,0,)" tripped the box() ban and killed a compilable model.
    scad = ('// Origin: corner of the bounding box (0,0,0) and revolve()\n'
            'cube([10,10,10]);\n')
    result = preflight_scad(scad, {})
    assert result["passed"], result["errors"]
    assert not any("box()" in e for e in result["errors"])


def test_refine_reports_linear_slot_row():
    # 003-style: seven slots in one aligned row -> loop hint, not hand placement
    from doodle_to_cad.refine import refine_view
    import math as _m
    slots = []
    for i in range(7):
        cx = 0.30 + i * 0.08
        poly = _rect_poly(cx, 0.55, 0.03, 0.28)
        slots.append(_prof(f"s{i}", poly, cx, 0.55, 0.03, 0.28))
    out = refine_view({"view_id": "v", "internal_profiles": slots})
    assert out["grid"]["type"] == "linear_v-row"
    assert out["grid"]["count"] == 7
    assert abs(out["grid"]["pitch_mm_of_view"] - 0.08) < 1e-6


def test_refine_row_hint_survives_secondary_rows():
    # 003 grille topology: 7-slot row AND a 2-item headlight row in the same
    # view. The 7-row hint must still fire (reg5 lost it because rows==1 was
    # required, and the generator then dropped the 2 headlights).
    from doodle_to_cad.refine import refine_view
    profiles = []
    for i in range(7):
        cx = 0.30 + i * 0.08
        profiles.append(_prof(f"s{i}", _rect_poly(cx, 0.55, 0.03, 0.28), cx, 0.55, 0.03, 0.28))
    for pid, cx in (("h0", 0.15), ("h1", 0.85)):
        profiles.append(_prof(pid, _circle_poly(cx, 0.35, 0.09, 24), cx, 0.35, 0.18, 0.18))
    out = refine_view({"view_id": "v", "internal_profiles": profiles})
    assert out["grid"]["type"] == "linear_v-row" and out["grid"]["count"] == 7
    assert out["grid"]["profile_ids"] == [f"s{i}" for i in range(7)]

def test_normalize_dimensions_coerces_list_form():
    # Live crash (run e5e3df5ad4c1): LLM returned dimensions as a list of
    # records; dict() raised "dictionary update sequence element #0 has
    # length 5; 2 is required" and the whole generation 500'd.
    from doodle_to_cad.sizes import normalize_dimensions
    out = normalize_dimensions([
        {"feature_id": "feat_1", "dimension_type": "max_width", "value": 120, "unit": "mm"},
        {"feature_id": "feat_2", "dimension_type": "max_thickness", "value": "4.5"},
        "junk", {"no_kind": True},
    ])
    assert out == {"max_width": 120.0, "max_thickness": 4.5}
    assert normalize_dimensions({"max_width": 5}) == {"max_width": 5}
    assert normalize_dimensions(None) == {}
