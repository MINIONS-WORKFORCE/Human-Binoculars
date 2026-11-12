"""Issue 36: exercise real public functions against the current backend schema."""

import csv
import importlib.util
import json

import pytest
from astropy.io import fits
from test_science import ROOT, image

from shared.science import APERTURE_ARCSEC, astrometry, photometry
from shared.science_api import photometry_payload
from shared.science_contract import normalized_target


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


models = load_module("issue36_models", ROOT / "members/dong/app/api_models.py")
runner = load_module("issue36_runner", ROOT / "members/nguyen/issue36.py")


def target():
    return {
        "id": "r-dra",
        "name": "Synthetic R Dra",
        "ra_deg": 269.4485,
        "dec_deg": 4.7394,
        "epoch_jyear": 2000,
        "pmra": 0,
        "pmdec": 0,
    }


def entry(tmp_path, k=0):
    item, _ = image(tmp_path, k)
    item.update(survey=1, data_kind="mock")
    return item


def test_public_functions_match_active_backend(tmp_path):
    items = [entry(tmp_path, k) for k in range(3)]
    photo = photometry(items, target(), APERTURE_ARCSEC)
    astro = astrometry(items, target())
    models.Photometry.model_validate(photo)
    models.Astrometry.model_validate(astro)
    assert photo["target"]["target_key"] == "rdra"
    assert "warnings" not in photo and "data_kind" not in photo
    assert all(p["measured_px"] is None for p in astro["points"])
    assert "warnings" in photometry(items, target(), diagnostics=True)


def test_empty_inputs_are_schema_valid_without_network():
    models.Photometry.model_validate(photometry([], target()))
    models.Astrometry.model_validate(astrometry([], target()))
    assert photometry([], target())["points"] == []
    assert astrometry([], target())["fit"] is None


@pytest.mark.parametrize("survey", [None, "synthetic", True])
def test_missing_visit_index_is_not_fabricated(tmp_path, survey):
    item = entry(tmp_path)
    item["survey"] = survey
    with pytest.raises(TypeError, match="integer survey"):
        photometry([item], target())
    assert photometry([item], target(), diagnostics=True)["points"]


def test_missing_wavelength_is_not_fabricated(tmp_path):
    item = entry(tmp_path)
    item["wavelength_um"] = None
    with pytest.raises(ValueError, match="wavelength_um"):
        photometry([item], target())


def test_saturation_csv_and_stale_api_removal(tmp_path):
    item = entry(tmp_path)
    with fits.open(item["path"], mode="update", memmap=False) as hdus:
        hdus["FLAGS"].data[32, 32] = 1 << 1
    result = photometry([item], target(), diagnostics=True)
    out = tmp_path / "export"
    report = runner.export_result(result, out)
    assert report["n_valid_target_fluxes"] == 0
    with (out / "points.csv").open(encoding="utf8", newline="") as stream:
        rows = list(csv.DictReader(stream))
    assert rows[0]["flux_mjy"] == ""
    assert json.loads(rows[0]["warnings"]) == ["SATURATED"]
    assert rows[0]["aperture_is"] == "radius"
    result["points"][0]["survey"] = None
    report = runner.export_result(result, out)
    assert report["api_payload_status"] == "not_exportable"
    assert not (out / "api_payload.json").exists()


def test_current_team_target_schema_and_epoch_are_preserved():
    table = json.loads((ROOT / "shared/targets.json").read_text(encoding="utf8"))
    barnard = normalized_target(next(t for t in table["targets"] if t["id"] == "barnard"))
    assert barnard["epoch_jyear"] == 2000
    assert barnard["pmdec"] > 10000
    models.Astrometry.model_validate(astrometry([], barnard))


def test_equal_mjd_retains_correct_frame_identity(tmp_path):
    items = [entry(tmp_path, k) for k in range(2)]
    for k, item in enumerate(items):
        item["mjd"] = 60000
        with fits.open(item["path"], mode="update", memmap=False) as hdus:
            hdus["IMAGE"].header["OBSID"] = f"equal-mjd-{k}"
    result = astrometry(items, target())
    assert [p["frame_id"] for p in result["points"]] == ["equal-mjd-0", "equal-mjd-1"]


def test_export_of_empty_result_has_header(tmp_path):
    runner.export_result(photometry([], target(), diagnostics=True), tmp_path)
    assert (tmp_path / "points.csv").read_text().startswith("data_kind,frame_id,mjd,warnings")


def test_no_fabricated_gaia_id_for_synthetic_control(tmp_path):
    diagnostic = photometry(
        [entry(tmp_path)], target(), reference_stars=[target()], diagnostics=True
    )
    assert diagnostic["reference_star"] is not None
    assert photometry_payload(diagnostic)["reference_star"] is None


def test_issue36_evidence_matches_backend_and_keeps_mock_label():
    base = ROOT / "members/nguyen/evidence/issue36"
    for relative, model in [
        ("mock/rdra", models.Photometry),
        ("mock/barnard", models.Astrometry),
        ("observational/barnard", models.Astrometry),
    ]:
        model.model_validate(json.loads((base / relative / "api_payload.json").read_text()))
        diagnostic = json.loads((base / relative / "diagnostics.json").read_text())
        assert diagnostic["data_kind"] == relative.split("/")[0]
    summary = json.loads((base / "observational/rdra/summary.json").read_text())
    assert summary["n_rows"] == 32 and summary["n_valid_target_fluxes"] == 0
    assert summary["api_payload_status"] == "not_exportable"


def test_barnard_mock_public_fit_has_gaia_direction():
    base = ROOT / "members/nguyen/evidence/issue36/mock/barnard"
    payload = json.loads((base / "api_payload.json").read_text())
    assert payload["fit"]["pmdec"] * payload["catalog_pm"]["pmdec"] > 0
    assert payload["fit"]["pmdec"] == pytest.approx(payload["catalog_pm"]["pmdec"], abs=5)
