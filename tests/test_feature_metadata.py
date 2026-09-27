import json

from doodle_to_cad.params import extract_params, rewrite_params, validate_updates


def model(features=None):
    metadata = {"version": 1, "parameters": {
        "width": {"label": "Opening width", "description": "Widens the upper opening", "unit": "mm", "feature": "opening"},
        "missing": {"label": "Absent", "description": "Absent", "unit": "mm"}},
        "features": features if features is not None else {"opening": {"kind": "region", "label": "Upper opening",
            "min": [0, 0, 0], "max": [{"parameter": "width", "scale": 0.5, "offset": 1}, 5, 10]}}}
    return '/* doodle-meta ' + json.dumps(metadata) + ' */\nwidth = 20;\neps = 0.01;\ncube([width, 5, 10]);'


def test_metadata_allowlist_and_edit_alignment():
    params = extract_params(model())
    assert [p.name for p in params] == ['width']
    assert params[0].label == 'Opening width'
    assert params[0].feature['max'] == [11, 5, 10]
    edited, _ = rewrite_params(model(), {'width': 30})
    assert extract_params(edited)[0].feature['max'] == [16, 5, 10]
    import pytest
    with pytest.raises(ValueError):
        validate_updates(model(), {'eps': 0.02})


def test_missing_or_unsupported_metadata_never_guesses_features():
    assert extract_params('width = 20;')[0].feature is None
    assert extract_params('/* doodle-meta bad JSON */\nwidth = 20;')[0].feature is None
    for feature in ({'kind': 'region', 'label': 'Bad', 'min': [0, 0, 0], 'max': ['width/2', 2, 3]},
                    {'kind': 'dimension', 'label': 'Bad', 'axis': 'w'},
                    {'kind': 'region', 'label': 'Bad', 'min': [0, 0, 0], 'max': [{'parameter': 'missing'}, 2, 3]}):
        assert extract_params(model({'opening': feature}))[0].feature is None


def test_explicit_dimension_contract():
    feature = {'kind': 'dimension', 'label': 'Overall width', 'axis': 'x'}
    assert extract_params(model({'opening': feature}))[0].feature == feature
