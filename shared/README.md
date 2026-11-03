# shared/

Things more than one person depends on. Changes here need a review from the owner.

| Path | Owner | First version due |
| --- | --- | --- |
| `api-contract/openapi.yaml` | Đông | 4/11 (API contract v0) |
| `targets.json` | Nguyên | 3/11 (5-target table from SIMBAD) |
| `data-layout.md` | Khôi | 4/11 (fixture pack folder structure) |

Rule: contract first, code second. Frontend codes against the mock, image processing against the fixture pack; nobody waits for the real thing.
