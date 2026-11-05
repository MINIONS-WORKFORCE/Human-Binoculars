# Document-based SPHEREx survey classification

## Verified result on the actual QR2 dataset

- 1545 observation records, represented by 792 distinct exposure headers.
- All headers retrieved successfully, using official IRSA and its public AWS mirror. Only bounded header ranges were read; full spectral images were not downloaded.
- 1413 records receive document-rule-derived survey numbers; 132 remain unclassified by the conservative phase-boundary policy.
- Counts: Survey 1 = 685, Survey 2 = 624, Survey 3 = 0, Survey 4 = 104. Zero means absent from this classified subset, not absent from the archive.
- 42 cross-survey candidate displacement predictions, using median-time representatives per target/detector/release/derived survey.
- Header DATE-OBS versus metadata t_min: maximum absolute difference 0.043400 seconds; all within the 2-second validation limit.

## Sources and interpretation

1. [SPHEREx Explanatory Supplement](https://irsa.ipac.caltech.edu/data/SPHEREx/docs/SPHEREx_Expsupp_QR.pdf), **version 2.0, 2026-08-25**, downloaded and read directly. Section 1.4, pp.8–9 defines survey membership; the Image Header Description on p.14 repeats the rule. The prose names SPS_PA_ECL; the header table and actual files use SPS_EPA. The local PDF SHA256 is recorded in manifest.json. Earlier web search results indexed v1.3 and are superseded here.
2. [Mission data tools](https://spherex.caltech.edu/page/data-tools) gives 2025-05-01 as the science-survey start. This implementation uses that science start for the documented time rule.
3. [IRSA data access](https://caltech-ipac.github.io/spherex-archive-documentation/spherex-data-access/) documents on-premises and public cloud archive access.

The supplement assigns PA 0/180 degrees in the initial 0–12.5-month phase to Surveys 1/2, and PA 0/180 in the 12.5–25-month phase to Surveys 3/4. Planned boresight values are shared across six bands of a single observation, allowing one verified header per OBSID/release. Each row retains the actual header URL and SHA256.

These numbers are **derived by applying the documented rule**, not copied from an archive-issued survey-ID column. The CSV intentionally names the field derived_survey_number.

## Conservative choices made by this implementation

- Only all_sky observations with NON_SURVEY explicitly false qualify. Parse SPS_FLAGS as a list: all_sky,downlink still has all_sky membership; preserve the original flags for separate image QA.
- Read SPS_PA_ECL or SPS_EPA; reject disagreement when both exist. Require orientation within 0.1 degree of 0 or 180. That tolerance is an explicit implementation choice.
- The document specifies 12.5 months, but the material verified here does not provide an exact UTC transition instant. **May 2026 is deliberately left unclassified. This month-wide guard is our conservative choice, not an official IRSA transition calendar.** Do not round 12.5 months into an invented UTC boundary.
- Safe first-phase scope: 2025-05-01 up to 2026-05-01. Safe second-phase scope: 2026-06-01 up to 2027-05-01. Dates outside those guarded scopes need further authoritative phase information. The two sources establish the method and science start; their combination is the implementation's stated inference.
- Blank survey labels never fall back to a seven-day grouping, filename week, QR2/QR3 release or the nearest known survey.
- Comparisons follow actual observation-time order. Survey 1/2 labels do not establish chronological order because the documented phases overlap in time.

## Primary handoff files

- reports/official-survey/survey_classification.csv: all 1545 rows, PA, time, original flags, derived label/status and header provenance.
- reports/official-survey/expected_motion_between_surveys.csv: 42 predictions between representatives of different derived surveys.
- reports/official-survey/manifest.json: input SHA256 and the exact policy.
- data/nguyen/official-survey-audit/header-cache/: raw header blocks plus extraction/provenance JSON. Local/Drive only.
- audit_official_surveys.py and test_official_surveys.py: reproducible implementation and 15 tests, all passed. Ruff passed.

## Status of earlier products

The original 30 endpoint pairs remain valid temporal predictions. The 31 seven-day windows and 84 pairs remain exploratory time grouping. Neither product supplies official survey labels. Use the new document-rule-derived table for survey-based comparisons, keeping the stated unclassified subset.

The broad claim that all scan assignments must wait for Khôi is superseded: actual headers and published documentation now support the classifications above. Boundary cases remain unresolved rather than fabricated. This does not validate bandpass, source detection or image-motion measurement. The angular model still excludes annual parallax, orbital motion and perspective acceleration. No tested Barnard D2 pair has been accepted for measurement.

The source-code and figures are training material. No commit, push, PR creation or message was performed during this update.
