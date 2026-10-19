"""Issue #68: never invent unconstrained dimensions — ask instead."""
import asyncio
import json
import re
from pathlib import Path

import pytest
from fastapi import HTTPException

pytest_asyncio = pytest  # repo style: sync tests driving asyncio.run

from doodle_to_cad.clarification import accept_answer, ask_clarification
from doodle_to_cad.sizes import plan_unconstrained_axes


def test_plan_unconstrained_axes_priority():
    assert plan_unconstrained_axes(None) == []
    assert plan_unconstrained_axes({"width_mm": 9, "depth_mm": None, "height_mm": 5}) == ["depth"]
    assert plan_unconstrained_axes({"width_mm": 9, "depth_mm": None, "height_mm": None}) == ["depth", "height"]
    assert plan_unconstrained_axes({"width_mm": 9, "depth_mm": 4, "height_mm": 5}) == []


def _waiting_job(**question):
    import uuid
    q = {"id": uuid.uuid4().hex, "kind": "body_dimension", "axis": "depth",
         "feature_id": "size_depth", "text": "How large should the depth be (mm)?",
         "maximum_mm": 480.0}
    q.update(question)
    job = {"job_id": "j1", "status": "waiting_for_answer", "question": q,
           "_answer_future": asyncio.get_event_loop().create_future() if False else None}
    return job


def _job_with_future(qid=None):
    import uuid
    from asyncio import Future
    q = {"id": qid or uuid.uuid4().hex, "kind": "body_dimension", "axis": "depth",
         "feature_id": "size_depth", "maximum_mm": 480.0}
    fut = Future()
    return {"job_id": "j1", "status": "waiting_for_answer", "question": q, "_answer_future": fut}, q, fut


def test_accept_answer_body_dimension_matrix():
    asyncio.run(_accept_matrix())


async def _accept_matrix():
    job, q, fut = _job_with_future()
    # valid
    out = accept_answer(job, {"question_id": q["id"], "value_mm": 4})
    assert out["status"] == "running" and fut.result()["value_mm"] == 4
    # invalid values
    for value in (0, -3, 10_000, True, "4"):   # 10_000 > maximum_mm
        job, q, fut = _job_with_future()
        with pytest.raises(HTTPException) as exc:
            accept_answer(job, {"question_id": q["id"], "value_mm": value})
        assert exc.value.status_code == 422, value
    job, q, fut = _job_with_future()
    with pytest.raises(HTTPException) as exc:
        accept_answer(job, {"question_id": q["id"]})
    assert exc.value.status_code == 422
    # wrong question id
    job, q, fut = _job_with_future()
    with pytest.raises(HTTPException) as exc:
        accept_answer(job, {"question_id": "nope", "value_mm": 4})
    assert exc.value.status_code == 409
    # extra fields rejected
    job, q, fut = _job_with_future()
    with pytest.raises(HTTPException) as exc:
        accept_answer(job, {"question_id": q["id"], "value_mm": 4, "choice": "through"})
    assert exc.value.status_code == 422


def test_ask_body_dimension_times_out_and_records(tmp_path):
    asyncio.run(_ask_timeout(tmp_path))


async def _ask_timeout(tmp_path):
    job = {"job_id": "j2", "status": "queued", "stage": "", "question": None}
    answer = await ask_clarification(job, tmp_path, {
        "kind": "body_dimension", "axis": "depth", "feature_id": "size_depth",
        "text": "How large should the depth be (mm)?", "reason": "single view"}, 480.0, [], timeout_s=0.05)
    assert answer is None
    assert job["status"] == "queued" and job.get("question") is None and "_answer_future" not in job
    record = json.loads((tmp_path / "clarifications.json").read_text())[0]
    assert record["status"] == "timeout" and record["question"]["axis"] == "depth"


def test_ask_body_dimension_answered(tmp_path):
    asyncio.run(_ask_answered(tmp_path))


async def _ask_answered(tmp_path):
    job = {"job_id": "j3", "status": "queued", "stage": "", "question": None}

    async def answer_it():
        for _ in range(50):
            await asyncio.sleep(0.01)
            if job.get("_answer_future") is not None:
                job["_answer_future"].set_result({"question_id": job["question"]["id"],
                                                   "feature_id": "size_depth",
                                                   "kind": "body_dimension", "value_mm": 4.0})
                return
        raise AssertionError("question never surfaced")

    reply = asyncio.create_task(answer_it())
    answer = await ask_clarification(job, tmp_path, {
        "kind": "body_dimension", "axis": "depth", "feature_id": "size_depth",
        "text": "How large should the depth be (mm)?", "reason": "single view"}, 480.0, [])
    await reply
    assert answer["value_mm"] == 4.0
    record = json.loads((tmp_path / "clarifications.json").read_text())[0]
    assert record["status"] == "answered"


def test_evaluation_hard_gate_on_user_stated_axis():
    from doodle_to_cad.evaluation import evaluate_candidate
    health = {"extents_mm": [100.0, 5.0, 61.4], "watertight": True, "components": 1,
              "euler_number": 2, "volume_mm3": 1000.0, "surface_area_mm2": 500.0,
              "triangles": 12, "degenerate_triangles": 0}
    spec = {"dimensions": {"max_width": 100.0, "max_depth": 4.0, "max_height": 61.4,
                           "user_supplied_axes": ["depth"]}}
    ev = evaluate_candidate(stl=None, health=health, scad="cube([1]);", views={},
                            source=b"", evidence={}, spec=spec, target_dimension="100",
                            strict=False)
    assert ev["mandatory_gates"]["dimensions"] is False
    assert any("user-stated depth" in f for f in ev["failures"])
    # same mesh WITHOUT the user-stated mark stays inside the loose window
    ev2 = evaluate_candidate(stl=None, health=health, scad="cube([1]);", views={},
                             source=b"", evidence={},
                             spec={"dimensions": {"max_width": 100.0, "max_depth": 4.0,
                                                  "max_height": 61.4}},
                             target_dimension="100", strict=False)
    assert ev2["mandatory_gates"]["dimensions"] is True


def test_pipeline_wiring_contract():
    source = Path("doodle_to_cad/pipeline.py").read_text()
    assert "ask_user=None" in source
    assert "plan_unconstrained_axes" in source
    assert '"kind": "body_dimension"' in source
    assert 'size_clarification' in source
    app_source = Path("doodle_to_cad/app.py").read_text()
    assert "ask_missing_dimensions" in app_source
    assert "ask_user=ask_user if ask_missing_dimensions else None" in app_source


def test_ui_renders_body_dimension_prompt():
    js = Path("web/app.js").read_text()
    assert "q.kind==='body_dimension'" in js
    assert "payload.value_mm" in js
    html = Path("web/index.html").read_text()
    assert 'app.js?v=20' in html
