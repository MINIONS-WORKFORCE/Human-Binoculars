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


def test_preview_samples_twelve_exposures_across_time(monkeypatch, tmp_path):
    rows = [dict(access_url=f"https://irsa.ipac.caltech.edu/{i}.fits",
                 obs_id=str(i), energy_bandpassname="SPHEREx-D6", t_min=61000+i/100)
            for i in range(30)]
    monkeypatch.setattr(live_cutouts.irsa, "find_images", lambda *a, **k: rows)
    monkeypatch.setattr(live_cutouts.irsa, "download_cutout",
                        lambda url, ra, dec, size, path, **k: path.write_bytes(b"fits"))
    result = live_cutouts.load_cutouts(FramesQuery(ra=133, dec=-7), tmp_path)
    assert len(result) == 12
    assert result[0].obs_id == "0"
    assert result[-1].obs_id == "29"
    assert len({item.obs_id for item in result}) == 12
