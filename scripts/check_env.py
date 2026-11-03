"""Check that this machine is ready for the SPHEREx training work.

    python scripts/check_env.py            # libraries only
    python scripts/check_env.py --online   # also query IRSA SIA2 for WISE 0855

Post the last line of the output in the team chat.
"""

import argparse
import importlib
import os
import sys

REQUIRED = [
    "numpy",
    "astropy",
    "astroquery",
    "pyvo",
    "reproject",
    "photutils",
    "matplotlib",
    "fastapi",
    "diskcache",
    "PIL",
]

# WISE 0855-0714, from the plan's target table
WISE_0855 = (133.7951, -7.2451)


def check_python() -> bool:
    ok = sys.version_info >= (3, 12)
    print(f"[{'ok' if ok else 'FAIL'}] python {sys.version.split()[0]} (need 3.12+)")
    return ok


def check_imports() -> bool:
    all_ok = True
    for name in REQUIRED:
        try:
            module = importlib.import_module(name)
            print(f"[ok] {name} {getattr(module, '__version__', '')}")
        except Exception as exc:  # noqa: BLE001 - report any failure, keep checking
            print(f"[FAIL] {name}: {exc}")
            all_ok = False
    return all_ok


def check_irsa() -> bool:
    import astropy.units as u
    from astropy.coordinates import SkyCoord
    from astroquery.ipac.irsa import Irsa

    coord = SkyCoord(*WISE_0855, unit="deg")
    collections = [
        os.getenv("SPHEREX_COLLECTION", "spherex_qr3"),
        os.getenv("SPHEREX_COLLECTION_FALLBACK", "spherex_qr2"),
    ]
    found = False
    for collection in collections:
        try:
            table = Irsa.query_sia(pos=(coord, 0.01 * u.deg), collection=collection)
        except Exception as exc:  # noqa: BLE001 - report any failure, keep checking
            print(f"[FAIL] IRSA SIA2 ({collection}): {exc}")
            return False
        print(f"[info] IRSA SIA2 ({collection}): {len(table)} images cover WISE 0855")
        found = found or len(table) > 0
    print(f"[{'ok' if found else 'FAIL'}] IRSA reachable, SPHEREx images found")
    return found


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--online", action="store_true", help="also query IRSA")
    args = parser.parse_args()

    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass

    results = [check_python(), check_imports()]
    if args.online and results[-1]:
        results.append(check_irsa())

    if all(results):
        print("READY: environment OK")
        return 0
    print("NOT READY: fix the FAIL lines above (see README > Troubleshooting)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
