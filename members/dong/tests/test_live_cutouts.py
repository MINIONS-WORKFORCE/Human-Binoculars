from app.api_models import FramesQuery
from app.services import live_cutouts


def test_live_cutouts_keep_completed_visit_when_another_times_out(monkeypatch, tmp_path):
    rows = [
        {
            "access_url": f"https://irsa.ipac.caltech.edu/{obs_id}.fits",
            "obs_id": obs_id,
            "energy_bandpassname": "SPHEREx-D6",
            "t_min": mjd,
        }
        for obs_id, mjd in [("available", 61000), ("slow", 61100)]
    ]
    monkeypatch.setattr(live_cutouts.irsa, "find_images", lambda *args, **kwargs: rows)

    def download(url, ra, dec, size, path, **kwargs):
        if url.endswith("/slow.fits"):
            raise live_cutouts.irsa.UpstreamTimeout("deadline reached")
        path.write_bytes(b"test cutout")

    monkeypatch.setattr(live_cutouts.irsa, "download_cutout", download)
    cutouts = live_cutouts.load_cutouts(FramesQuery(ra=133, dec=-7, detector=6), tmp_path)
    assert [cutout.obs_id for cutout in cutouts] == ["available"]
