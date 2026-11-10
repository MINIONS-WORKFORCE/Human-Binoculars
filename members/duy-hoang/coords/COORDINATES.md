# Coordinate input: rules and examples

How the viewer turns what a user types into a sky position.
Code: [`parse.js`](parse.js) (coordinates), [`resolve.js`](resolve.js) (names), [`targets.js`](targets.js) (the 5 challenge targets).

## Quick start

```js
import { locate } from "./coords/resolve.js";

await locate("08h55m10.831s-7d14m42.53s");
// { raDeg: 133.795129, decDeg: -7.245147, source: "input", name: null, objectType: null, epoch: null }

await locate("Barnard's Star");
// { raDeg: 269.452077, decDeg: 4.693365, source: "local", name: "Barnard's Star", epoch: 2000, ... }

await locate("M31");
// { raDeg: 10.684708, decDeg: 41.26875, source: "mast", name: "MESSIER 031", epoch: 2000, ... }
```

`locate` is the only function the UI needs. It throws a `CoordError`; show `error.message` to the user and branch on `error.code`.

### Output

| Field        | Meaning                                                                    |
| ------------ | -------------------------------------------------------------------------- |
| `raDeg`      | Right Ascension in degrees, `0 <= raDeg < 360`                             |
| `decDeg`     | Declination in degrees, `-90 <= decDeg <= 90`                              |
| `source`     | `"input"` (typed coordinates), `"local"` (targets.js) or `"mast"` (online) |
| `name`       | Canonical object name, `null` for typed coordinates                        |
| `objectType` | Short description or SIMBAD/NED type, may be `null`                        |
| `epoch`      | Year the position is valid for (`2000` for names), `null` when unknown     |

Values are never rounded; round only when displaying.

## How the input is classified

1. Trim, collapse spaces, and turn the Unicode minus `−` and dashes `–` `—` into `-` (text copied from Wikipedia uses them).
2. If the text **starts with a digit, sign or dot** and contains only digits, `+ - . ,`, spaces and the letters `h m s d`, it is **coordinates**. A bad value is then reported as a coordinate error, never looked up as a name.
3. Anything else is a **name**.

| Input                     | Read as     | Why                               |
| ------------------------- | ----------- | --------------------------------- |
| `133.795 -7.245`          | coordinates |                                   |
| `25h00m00s +10d00m00s`    | coordinates | then fails with `RA_OUT_OF_RANGE` |
| `M31`                     | name        | starts with a letter              |
| `R Dra`                   | name        | contains `R`, `r`, `a`            |
| `2MASS J22041052-5646577` | name        | contains `M A S J`                |

## Form 1: decimal degrees

`<RA degrees> <Dec degrees>`, separated by spaces or a comma. **RA is in degrees here**, not hours.

| Input             | raDeg   | decDeg |
| ----------------- | ------- | ------ |
| `133.795 -7.245`  | 133.795 | -7.245 |
| `133.795, -7.245` | 133.795 | -7.245 |
| `133.795,-7.245`  | 133.795 | -7.245 |
| `269.452 +4.693`  | 269.452 | 4.693  |
| `.5 -.25`         | 0.5     | -0.25  |

Limits: `0 <= RA < 360`, `-90 <= Dec <= 90`.

## Form 2: h/m/s and d/m/s

`<H>h<M>m<S>s <sign><D>d<M>m<S>s`. **RA is in hours** (1h = 15°), Dec in degrees. Spaces between parts, a comma between RA and Dec, and upper case letters are all fine. The space between RA and Dec can be left out when Dec has a sign, as in the challenge text.

```
RA  = (H + M/60 + S/3600) * 15
Dec = sign * (D + M/60 + S/3600)      no sign means +
```

| Input                            | raDeg      | decDeg    | Note                         |
| -------------------------------- | ---------- | --------- | ---------------------------- |
| `08h55m10.831s-7d14m42.53s`      | 133.795129 | -7.245147 | WISE 0855, challenge text    |
| `08h55m10.831s -7d14m42.53s`     | 133.795129 | -7.245147 |                              |
| `8h 55m 10.831s, -7d 14m 42.53s` | 133.795129 | -7.245147 |                              |
| `17h57m48.5s +4d41m36.2s`        | 269.452083 | 4.693389  |                              |
| `12h30m49.42s 12d23m28.0s`       | 187.705917 | 12.391111 | no sign = positive           |
| `00h00m00s -0d30m00s`            | 0          | -0.5      | sign kept when degrees are 0 |
| `23h59m59.999s +90d00m00s`       | 359.999996 | 90        |                              |

All three parts (h, m, s / d, m, s) are required. Limits: hours < 24, degrees <= 90, minutes and seconds < 60, and at ±90° the minutes and seconds must be 0.

Reference values were computed with astropy (`Angle("08h55m10.831s").to(u.deg)`); the tests check them to 1e-6°.

## Form 3: colons or spaces

The numbers of Form 2 without the letters, separated by colons or single spaces, as SIMBAD prints them: `<H>:<M>:<S> <sign><D>:<M>:<S>` or `<H> <M> <S> <sign><D> <M> <S>`. Same units, rules and limits as Form 2. RA and Dec are separated by spaces or a comma, and the sign stays attached to the degrees.

| Input                       | raDeg      | decDeg    | Note                         |
| --------------------------- | ---------- | --------- | ---------------------------- |
| `08:55:10.831 -07:14:42.53` | 133.795129 | -7.245147 | WISE 0855                    |
| `08 55 10.831 -07 14 42.53` | 133.795129 | -7.245147 | WISE 0855, as SIMBAD prints  |
| `17:57:48.5 +04:41:36.2`    | 269.452083 | 4.693389  |                              |
| `12:30:49.42 12:23:28.0`    | 187.705917 | 12.391111 | no sign = positive           |
| `00:00:00 -00:30:00`        | 0          | -0.5      | sign kept when degrees are 0 |

All three numbers are required on each side: `08:55 -07:14` is `UNSUPPORTED_FORMAT`.

## Errors

| Input                             | `error.code`                           |
| --------------------------------- | -------------------------------------- |
| (empty)                           | `EMPTY`                                |
| `24h00m00s +00d00m00s`            | `RA_OUT_OF_RANGE`                      |
| `360 0`, `-1 0`                   | `RA_OUT_OF_RANGE`                      |
| `0 91`, `00h00m00s +90d00m01s`    | `DEC_OUT_OF_RANGE`                     |
| `00h61m00s +00d00m00s`            | `MINUTES_OUT_OF_RANGE`                 |
| `00h00m60s +00d00m00s`            | `SECONDS_OUT_OF_RANGE`                 |
| `08h55m10.831s -7.245`            | `UNSUPPORTED_FORMAT` (forms mixed)     |
| `08:55 -07:14`                    | `UNSUPPORTED_FORMAT` (seconds missing) |
| `133.795`                         | `UNSUPPORTED_FORMAT` (Dec missing)     |
| `nonexistent zzz`                 | `NAME_NOT_FOUND`                       |
| name lookup offline or HTTP error | `RESOLVER_UNAVAILABLE`                 |

## Names

Lookup order:

1. **`targets.js`**, the 5 challenge targets. Works offline and avoids the traps below. Matching ignores case, apostrophes and extra spaces.
2. **MAST Name Lookup** (`https://mast.stsci.edu/api/v0/invoke`, service `Mast.Name.Lookup`), which asks SIMBAD and NED. We use it because CDS/Sesame was unreachable from our network on 4–5/11.

| Target         | Accepted names                                                                 | raDeg      | decDeg     |
| -------------- | ------------------------------------------------------------------------------ | ---------- | ---------- |
| Barnard's Star | Barnard's Star, Barnards Star, Barnard Star, Barnard, GJ 699                   | 269.452077 | 4.693365   |
| Epsilon Indi B | Epsilon Indi B, eps Ind B, eps Indi B, GJ 845 B, Gl 845 B                      | 331.044147 | -56.782844 |
| WISE 0855-0714 | WISE 0855-0714, WISE 0855, WISE J085510.83-071442.5, WISEA J085510.74-071442.5 | 133.818908 | -7.247048  |
| RW Aurigae     | RW Aurigae, RW Aur                                                             | 76.956526  | 30.401438  |
| R Draconis     | R Draconis, R Dra                                                              | 248.167611 | 66.754979  |

### Traps found while testing (why the local table exists)

- **`eps Ind B`** online resolves to the **planet `eps Ind b`**, which sits at the host star, about 0.11° from the brown dwarf pair. Use `GJ 845 B` when asking an online service.
- **`Barnard`** online resolves to **NGC 6822 (Barnard's Galaxy)**.
- **WISE 0855**: the challenge gives `08h55m10.831s -7d14m42.53s` (133.7951, -7.2451) while SIMBAD gives 133.8189, -7.2470. Both are right for different years: the object moves about 8″ per year.

### Epoch and proper motion

Name lookups return the **J2000 position** (`epoch: 2000`). Nearby stars have moved since then; Barnard's Star by about 4.5′ by 2026, enough to fall outside a small cutout. Moving the position to the SPHEREx observation date is done downstream (Nguyên, proper-motion propagation); this module does not do it.

## Not supported yet

- Symbols: `8h55m10.8s −7°14′42.5″`
- Partial forms: `08h55m`, `-7d14m`
- Galactic coordinates (l, b)
- Proper motion (see above)

## In the browser

MAST sends no CORS headers, so a page cannot call it directly. The demo ([`../coord-demo`](../coord-demo)) proxies `/mast/*` to `https://mast.stsci.edu/*` through the Vite dev server, and `resolve.js` uses `/mast/api/v0/invoke` by default. From Node, pass `{ endpoint: MAST_URL }`. In production the backend must provide the same proxy.

## Run

```bash
npm test                                   # Vitest, includes coords/*.test.js
npx vite members/duy-hoang/coord-demo      # demo page at http://localhost:5173
```
