# TRNLizard HAMT (Type 395) — Current Implementation Map & Multi-Surface Change Plan

## 1. End-to-end deck generation flow

**Template structure** (`Lizard_DCK_Template.py`): the DCK file is one big Python `"""..."""` string split into lines. Tagged blocks delimit repeatable sections:

| Tag | Template line | Content |
|---|---|---|
| `@e1#`/`@e2#` | 496 / 890 | per-zone equation blocks (EQU 8 etc.), looped per `zone_item` in `printdck()` |
| `@e3#` | 961 | **Type 399 PCM** equations + `UNIT 200 TYPE 399` — one per `Eficalsurfaces` entry |
| `@e4#` | 1030 | Type 336 active-layer equations |
| `@e5#` | 1091 | **HAMT Type 395** equations + `UNIT 200 TYPE 395` — one per `Ecalsurfaces` entry |
| `@e7#` | 1161 | coupling / window BSDF / DHW / system definition |

**`printdck()`** (`Lizard_System.py:2710`) iterates the template lines. When it hits `@eN#` / `@eN#...` markers it enters a sub-loop over `zone` / `Airnode.Surfaces`, populates the global `variables` dict, then for every line in the block runs:

```python
for variablename in list(set(re.findall('@(\w+)',item))):
    item=re.sub('@'+variablename, str(variables[variablename]).encode('string-escape'), item)
dckout.write(item)
```

(Lines 3006-3009, the same pattern is repeated in every e-block.)

**Placeholder syntax**: `@name` is looked up in `variables['name']`. Per-surface placeholders are written `@surface` (e.g. `TSI395_S@surface` → `TSI395_S32`) because `variables['surface'] = surface.Surfnum` is set before substitution. Per-zone: `@aname`, `@zname`.

**Other writers**:
- `print_datasheet()` (2385-2407) — same regex substitution, used for report files.
- `printbui()` / b18 writer — writes the `.b18` building file; gain REGIME lines are assembled in the main surface loop (1183-1209), GAIN *schedules* via `printsingledata` (586-648).

## 2. All HAMT / Type 395-related code

### Component inputs
- `Lizard_System.py:71-76` — GH component inputs `t395_udepth`, `t395_udivnum`.

### Version
- `Lizard_System.py:140` — `version = '2.3.2 (HAMT)'`.

### b18-side (construction + boundary swap)
- **Lines 532-556**: when a surface's `Boundarycond` is `EXTCALEXT`/`EXTCALBND`, its construction is replaced with the library pseudo-wall `HIGH_COND` (Hback=99999, copies radiative props from the real wall). This is the **HAMT trigger** on the b18 side.
- **Line 967** (`Boundarycond == 'EXTCALEXT'` external wall):
  ```
  dummylines=dummylines + ' : ORI=@self.Orientation : BOUNDARY = INPUT 1*TSI395_S@self.Surfnum   : GEOSURF=@self.Geosurf'
  ```
  then `surfaces.Construction = 'HIGH_COND'` (969), restored at 1099.
- **Line 1081** (`Boundarycond == 'EXTCALBND'` boundary wall):
  ```
  dummylines=dummylines + ' : BOUNDARY=INPUT 1*TSI395_S@self.Surfnum : GEOSURF=@self.Geosurf'
  ```
  then `surfaces.Construction = 'HIGH_COND'` (1091).

### .dck-side e7 block (lines 2964-3005)
For each `zone_item`, `variables['unitno'] = 800`, then for each `wall_item in zone_item.Airnode.Ecalsurfaces`, find the matching `surface` and set:

| Variable | Line | Value |
|---|---|---|
| `surface` | 2969 | `surface.Surfnum` |
| `area` | 2970 | `surface.Area` |
| `qwg1` | 2971 | `'QABSI_S%s + QABSILW_S%s - QWG_S%s'` |
| `qwg2` | 2972→2988 | long-wave rad balance for `EXTCALEXT`, else `0` |
| `mt1`/`mt2` | 2974-2975 | moisture transfer coeffs |
| `specload` | 2976 | `"-Q_al_{Airnode}*AREA_{Airnode}/Area_al1_{Airnode}"` |
| `tbd`/`hconvo`/`rh2` | 2982-2995 | zone-dependent |
| `lu1` | 2997 | `variables['unitno']` |
| `udefdepth`/`udivnum` | 2998-2999 | `t395_udepth or 0.02`, `t395_udivnum or 100` |
| `datafile1` | 3000 | `surface.Filemat` |
| `unitno` | 3001 | incremented |
| `aname` | 3002 | `zone_item.Airnode.Name` |

Then substitute and write (3006-3009).

### e3 block — Type 399 PCM (lines 2834-2924)
Same pattern: `variables['unitno'] = 800`, loop `Eficalsurfaces`, `lu1`/`lu2` = 800/820, template `UNIT 200 TYPE 399` (template line 921).

### Template `@e5#` block (template lines 1091-1160) — the HAMT equations and unit

```
EQUATIONS 32
SIGMA               = 2.041e-007
hconv1_S@surface    = (1/ MAX(REQV_S@surface*AREA395_S@surface,0.001))
hconv2_S@surface    = @hconvo
TB1_S@surface       = TSTAR_@aname
TAIR_MOIST1_S@surface = TAIR_@aname
TB2_S@surface       = @tbd
T395_OUTPUT_1       = [200,1]
...
T395_OUTPUT_11      = [200,11]
TSI395_S@surface    = [200,1]
TSO395_S@surface    = [200,2]
qWG1_S@surface      = @qwg1
qWG1_NoRad_S@surface = 0
qWG2_S@surface      = @qwg2
RH1_S@surface       = Rh_@aname
RH2_S@surface       = @rh2
beta1_S@surface     = @mt1
beta2_S@surface     = @mt2
WGAIN_I_S@surface   = [200,8]
WGAIN_O_S@surface   = [200,9]
AREA395_S@surface   = @area
HUMGAIN395          = [200,10]          # ← NO @surface suffix!
HEATGAIN395         = WGAIN_I_S@surface # ← NO @surface suffix!
QheatKJ_S@surface   = @specload*AREA395_S@surface*3.6
UNIT 200 TYPE 395  Type395              # ← HARDCODED UNIT 200
PARAMETERS 10
...
INPUTS 14
TAir_@aname ! TB1_S@surface
...
```

### Per-surface vs global names

**Per-surface (safe for multi-surface)** — all carry `_S@surface` or `@aname` suffix:
`TSI395_S`, `TSO395_S`, `qWG1_S`, `qWG2_S`, `WGAIN_I_S`, `WGAIN_O_S`, `AREA395_S`, `QheatKJ_S`, `hconv1_S`, `hconv2_S`, `TB1_S`, `TB2_S`, `RH1_S`, `RH2_S`, `beta1_S`, `beta2_S`, `TAIR_MOIST1_S`, `A_wall_S`.

**Global (collide with ≥2 surfaces)**:
- `HUMGAIN395` (= `[200,10]` — unit output 10 of Type 395)
- `HEATGAIN395` (= `WGAIN_I_S@surface`)
- `T395_OUTPUT_1..11` (diagnostic aliases of `[200,N]`)
- The Type 395 **UNIT number itself: hardcoded `200`** in the template.
- `SIGMA` (reassigned identically each time — harmless but redundant).

## 3. How a surface is marked HAMT, and how its zone is known

- The surface's `Boundarycond` must be `'EXTCALEXT'` or `'EXTCALBND'` (set in `Lizard_Surface_Settings.py` via the GH `Category` input → `SurfaceDefinition.Boundarycond`).
- During the b18 construction pass (lines 532-556, 960-1100) this swaps the construction to `HIGH_COND` / `HIGH_RES` and rewrites the surface's `BOUNDARY=` clause to read `1*TSI395_S{Surfnum}`.
- The surface's zone/airnode is implicit: the enclosing loop is `for Airnodes in dataset: for surfaces in Airnodes.Surfaces:` (line ~866), so `Airnodes.Name`/`Airnodes.Zonename` is the owning airnode.
- `Airnodes.Ecalsurfaces` (list of Surfnums) is populated at line 1179 during the same loop. `Eficalsurfaces` = PCM (Type 399) at 1180.
- In `printdck()` the loop `for zone_item in zone: ... zone_item.Airnode.Ecalsurfaces` (2965-3005) gives direct access to both surface and `zone_item.Airnode.Name`.

## 4. Where GAINS land in the .b18 and how airnode INPUTS are assembled

- `GAIN` REGIME lines are emitted in the surface loop at **1183-1209**: `regimelines += '{0} = {1} : SCALE= {2} ...'.format(gain_item.Type, dummy+'_'+Airnodes.Name, ...)`. `gain_item.Type` is e.g. `PEOPLE`, `LIGHTS`, `EQUIPMENT`, `MISC`, `THERMAL_BRIDGE`; the resulting b18 line is e.g. `GAIN HAMT_Gain_A1 = HAMT_Gain_A1_A1 : SCALE= ...`.
- The `HAMT_Gain_A1` *schedule definition* (with `CONVECTIVE=INPUT ... HUMIDITY=INPUT ...`) is **not generated by any .py file** — grep confirms the string does not exist in the repo. It lives in the user's b18 template / `Lizard_Zone_Regime.py`-driven `library.Gain` entries. The gain object has `Convective`, `Radiative`, `Humidity` fields (`Lizard_Component.py:536-538`).
- Airnode **INPUTS** lists in the .b18 are assembled by `printsingledata` / the b18 writer around lines 2320 (`INPUTS {9}`) and 2366 (`INPUTS {2}`); the `{N}` count is the count of preceding INPUT lines. Gains are wired into the airnode because the REGIME references `GAIN name = name_Airnode`, and TRNSYS resolves `CONVECTIVE=INPUT var` / `HUMIDITY=INPUT var` against dck equation variables — i.e. `HUMGAIN395` / `HEATGAIN395` (and/or `HamtHeatGain_KJPerHr_A{Zone}` in a future version).

## 5. Concrete change plan for N simultaneous HAMT surfaces

### A. Template `Lizard_DCK_Template.py` `@e5#` block (lines 1091-1160)

1. **Replace hardcoded `UNIT 200`** with `@unit395` (or `@unitno`) everywhere:
   - `UNIT 200 TYPE 395` → `UNIT @unit395 TYPE 395`
   - All `[200,N]` → `[@unit395,N]` (outputs 1-11, plus `TSI395`, `TSO395`, `WGAIN_I`, `WGAIN_O`, `HUMGAIN`).
2. **Suffix the global equation names** with `_S@surface`:
   - `HUMGAIN395` → `HUMGAIN395_S@surface`
   - `HEATGAIN395` → `HEATGAIN395_S@surface`
   - `T395_OUTPUT_N` → `T395_OUTPUT_N_S@surface` (optional; only if kept).
3. Keep the per-zone name `Rh_@aname`, `TSTAR_@aname`, `TAIR_@aname` — already correct.

### B. `Lizard_System.py` e7 loop (lines 2964-3005)

1. **Hoist unit counter out of the per-zone reset**: today `variables['unitno'] = 800` is set *inside* `for zone_item in zone:`, so a second zone would reuse 801. Either:
   - keep per-zone numbering but offset by zone: `variables['unitno'] = 800 + (zone_item.Anr-1)*K`, or
   - pre-allocate a global `hamt_unit_counter = 200` (or any free range) before the zone loop and increment per emitted surface. Note the existing convention: Type 399 uses UNIT 200 + lu 800/820; Type 395 uses UNIT 200 + lu 800. **The Type 395 unit-number range must not overlap Type 399 or other Type 395 surfaces.** Using `variables['unit395']` distinct from `variables['unitno']` is cleaner.
2. Track a new dict/list `hamt_surfaces = [(zone_item.Airnode.Name, surface.Surfnum, variables['unit395']), ...]` at module level (or in `sc.sticky`) so later blocks (gain wiring) know which surfaces feed which airnode.

### C. Gain emission (new code, ~line 1183-1209 area or a new block in the b18 writer)

For each zone, emit an extra REGIME line per HAMT surface whose airnode == that zone:
```
GAIN HamtGain_{Airnode} = HamtHeatGain_KJPerHr_{Airnode} : SCALE= 1 ...
```
and in the .dck EQUATIONS, define per-zone sums:
```
HamtHeatGain_KJPerHr_A{Zone} = HEATGAIN395_S{s1} [+ HEATGAIN395_S{s2} ...]
HamtHumGain_A{Zone}          = HUMGAIN395_S{s1}  [+ ...]
```
per zone, summing over that zone's HAMT surfaces. Add this as a new template block (e.g. `@e8#`) that loops over zones rather than surfaces.

### D. b18 GAIN schedule template (user-side / `Lizard_Zone_Regime.py`)

The user's `HAMT_Gain_A1` gain definition must change `CONVECTIVE=INPUT HEATGAIN395` → `CONVECTIVE=INPUT HamtHeatGain_KJPerHr_A{Zone}`, `HUMIDITY=INPUT HUMGAIN395` → `HUMIDITY=INPUT HamtHumGain_A{Zone}`.

### E. Name collisions to fix

| Current name | Problem | Fix |
|---|---|---|
| `UNIT 200 TYPE 395` | second surface overwrites first | `@unit395` placeholder |
| `HUMGAIN395` | re-declared, second wins | `HUMGAIN395_S{Surfnum}` |
| `HEATGAIN395` | same | `HEATGAIN395_S{Surfnum}` |
| `T395_OUTPUT_1..11` | same | suffix or drop |
| `SIGMA` | redeclared (harmless) | emit once globally |
| `variables['unitno'] = 800` reset per zone | two zones both emit `UNIT 200`/`lu 800` | hoist / offset by zone |
| `variables['qaddon']` (line 3624-3627) | already loops **all** zones' Ecalsurfaces and sums `-QheatKJ_S{n}` globally — fine as-is since `QheatKJ_S` is per-surface | no change |

### F. Files/functions to touch (summary)

- `Lizard_DCK_Template.py` lines 1091-1160 — parameterise UNIT number, suffix `HUMGAIN395`/`HEATGAIN395`/`T395_OUTPUT_*`, optionally move `SIGMA` out.
- `Lizard_System.py` lines 2964-3005 — allocate unique `variables['unit395']` per surface (don't reset per zone); record (airnode, surfnum, unit) triple.
- `Lizard_System.py` ~line 1183-1209 or new e-block — emit per-zone `HamtHeatGain_KJPerHr_A{Zone}` / `HamtHumGain_A{Zone}` sums and add the corresponding `GAIN` REGIME line per airnode.
- `Lizard_System.py` lines 532-556, 960-1100 — no change required; per-surface `TSI395_S@self.Surfnum` and `HIGH_COND` swap already work for N surfaces.
- User b18 template / `Lizard_Zone_Regime.py` — point `CONVECTIVE=INPUT` / `HUMIDITY=INPUT` at the new per-zone variables.

## 6. UNIT_NUMBER allocation & equation ordering / Type 150 feedback

- **UNIT_NUMBER allocation**: there is no central allocator. The template hardcodes `UNIT 200` for Type 395 (and Type 399), while `variables['unitno']` (800-series) is only used as Fortran **logical-unit** handles for `ASSIGN`/`DESIGNATE` (template lines 934-935, 957-959, 1131, 1159). The 800-counter is reset per zone (lines 2836, 2928, 2966), so today's code is only safe with **one** zone carrying ecal/efical surfaces. All other units use `@zunitNN` variables assigned per zone at line 3633-3635 (`unitsperzone = 30`, `zoneunitstart`), which *is* collision-free across zones.
- **Equation ordering**: TRNSYS requires inputs to be defined before use. The `@e5#` block emits `EQUATIONS 32` first, then `UNIT 200 TYPE 395` whose `INPUTS 14` reference the just-emitted per-surface equations (`TB1_S`, `TB2_S`, `hconv1_S`, ...). This works today because the whole block is emitted inside one iteration. For N surfaces, emitting N sequential (EQUATIONS + UNIT) pairs preserves correctness as long as the unit numbers are unique.
- **Type 150 DelayedInput feedback**: no `TYPE 150` / `DelayedInput` string exists anywhere in the 37-file repo (grep confirmed). The feedback loop today is only the algebraic pair `HUMGAIN395 = [200,10]` consumed downstream by the airnode humidity/gain equations and the b18 `HUMIDITY=INPUT HUMGAIN395` gain. There is no explicit delay unit in code — if a Type 150 is added to break the algebraic loop (wall moisture gain → room humidity → wall boundary humidity), it must reference each surface's `HUMGAIN395_S{Surfnum}` individually, and its UNIT number also needs allocation from the same per-surface counter. The natural place to insert it is right after the Type 395 unit in the `@e5#` block, with a `@unit150` placeholder.
