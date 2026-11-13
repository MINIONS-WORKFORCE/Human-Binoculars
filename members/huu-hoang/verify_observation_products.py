"""Read saved products end-to-end, validate their geometry and produce a visual index."""

import json

import matplotlib.pyplot as plt
import numpy as np
from astropy.coordinates import SkyCoord
from astropy.io import fits
from astropy.visualization import AsinhStretch, ImageNormalize
from astropy.wcs import WCS
from process_target_observations import BASE, TARGETS


def main():
    fig, axes = plt.subplots(5, 3, figsize=(14, 19), constrained_layout=True)
    summary = []
    for row, target in enumerate(TARGETS):
        folder = BASE / target
        info = json.loads((folder / "target_coordinates.json").read_text())
        coord = SkyCoord(info["ra_deg"], info["dec_deg"], unit="deg")
        reports = {}
        differences = 0
        for det in (1, 3, 6):
            report = json.loads(
                (folder / "combined_frames" / f"detector_{det}_frame_report.json").read_text()
            )
            reports[det] = report
            previous = None
            previous_label = None
            for frame in report["frames"]:
                label = frame["label"]
                with fits.open(folder / "combined_frames" / f"{label}.fits") as h:
                    image = h["MEDIAN"].data.copy()
                    count = h["NVALID"].data
                    assert h["MEDIAN"].header["BUNIT"]
                    np.testing.assert_allclose(
                        WCS(h["MEDIAN"].header).world_to_pixel(coord), [29, 29], atol=1e-7
                    )
                    assert image.shape == count.shape == (59, 59)
                    assert np.array_equal(count == 0, ~np.isfinite(image))
                    assert count.min() >= 0 and count.max() <= frame["n_inputs"]
                    assert np.isfinite(image).any()
                assert (folder / "combined_frames" / f"{label}.png").is_file()
                if previous is not None:
                    name = f"{label}_minus_{previous_label}"
                    with fits.open(folder / "combined_frames" / f"{name}.fits") as h:
                        np.testing.assert_allclose(
                            h[0].data, image - previous, atol=1e-4, rtol=1e-5, equal_nan=True
                        )
                    assert (folder / "combined_frames" / f"{name}.png").is_file()
                    differences += 1
                previous, previous_label = image, label
        d3 = reports[3]
        norm = ImageNormalize(
            vmin=d3["display"]["vmin"], vmax=d3["display"]["vmax"], stretch=AsinhStretch()
        )
        for col, frame in enumerate((d3["frames"][0], d3["frames"][-1])):
            with fits.open(folder / "combined_frames" / f"{frame['label']}.fits") as h:
                axes[row, col].imshow(
                    h["MEDIAN"].data,
                    origin="lower",
                    norm=norm,
                    cmap=plt.get_cmap("gray").with_extremes(bad="#703090"),
                )
            axes[row, col].set_title(f"{target} / {frame['label']} / n={frame['n_inputs']}")
        rgb = json.loads((folder / "false_color_report.json").read_text())
        assert rgb["visits"] and all(v["valid_fraction"] > 0 for v in rgb["visits"])
        visit = rgb["visits"][-1]["visit"]
        axes[row, 2].imshow(
            plt.imread(folder / "combined_frames" / f"false_color_visit_{visit:02}.png")
        )
        axes[row, 2].axis("off")
        frames = sum(len(r["frames"]) for r in reports.values())
        entries = json.loads((folder / "observation_manifest.json").read_text())
        record = {
            "target": target,
            "cutouts": len(entries),
            "median_frames": frames,
            "difference_frames": differences,
            "rgb_frames": len(rgb["visits"]),
            "center_deg": [info["ra_deg"], info["dec_deg"]],
        }
        if target in {"barnard", "r-dra"}:
            sat = json.loads((folder / "saturation_report.json").read_text())
            assert sat["masked_flagged_pixels_check"] == "pass"
            record["overflow_nonlinear_pixels_summed_over_inputs"] = sum(
                r["affected_pixels"] for r in sat["inputs"]
            )
        summary.append(record)
    fig.suptitle(
        "Five-target sample / D3 first and last visit / false-color last visit\n"
        "Fixed J2026 TAN grids; purple=missing/masked; no detection or variability claim"
    )
    fig.savefig(BASE / "target_observations_overview.png", dpi=150)
    plt.close(fig)
    report = {
        "status": "pass",
        "targets": summary,
        "checks": [
            "Saved FITS WCS center and units",
            "NVALID consistency",
            "Saved difference sign and values",
            "PNG/RGB presence and coverage",
            "Overflow/nonlinear pixels excluded before reprojection",
        ],
        "scope": "D1,D3,D6; at most two catalog exposures per detector/visit",
    }
    (BASE / "product_verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
