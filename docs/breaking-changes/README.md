# Breaking changes against the original TRNLizard

What behaves differently from the original TRNLizard (commit `c236064`) in a way that can stop an existing Grasshopper definition, change
what it writes, or change simulation results. Added features that do nothing until they are connected are not listed.

Each entry has an ID, what it did before and does now, and the smallest change to an existing definition.

## Categories

| File | Covers |
| --- | --- |
| [boundary-conditions.md](boundary-conditions.md) | categories, adjacency, what an unmatched surface becomes |
| [constructions.md](constructions.md) | where a surface gets its construction, FRONT/BACK, pairs |
| [geometry.md](geometry.md) | normals, solids, gaps, split surfaces and their numbers |
| [components.md](components.md) | inputs and outputs of components |
| [results.md](results.md) | fixes that change the written deck or b18, and so the results, with the definition unchanged |

## Index

| ID | Change | Stops the definition | Can change results | Since |
| --- | --- | --- | --- | --- |
| [BC-01](boundary-conditions.md#bc-01) | `AUTOMATIC` equals an empty category | no | yes | `923d514` |
| [BC-02](boundary-conditions.md#bc-02) | Unmatched `ADJACENT` is an error, not a mirrored `BOUNDARY` | yes | no | `a93769f` |
| [BC-03](boundary-conditions.md#bc-03) | Empty settings no longer mean `BOUNDARY` with `TAIR_@ANAME` | yes | yes | `da8d4f4` |
| [BC-04](boundary-conditions.md#bc-04) | Unmatched surfaces without a category follow `FallbackBoundary` and `GroundLevel`; new category `GROUND` | yes | yes | `d23df35` |
| [CON-01](constructions.md#con-01) | No default construction `IFL_L`; a surface without one is an error | yes | no | `da8d4f4` |
| [CON-02](constructions.md#con-02) | Different constructions on one pair are an error unless mirrored | yes | no | `a93769f` |
| [CON-03](constructions.md#con-03) | FRONT without a construction cannot follow a non-symmetric BACK | yes | no | `923d514` |
| [CON-04](constructions.md#con-04) | With no FRONT/BACK set, the side with the construction is FRONT | no | yes | `923d514` |
| [CON-05](constructions.md#con-05) | The active side of a pair is FRONT; an explicit BACK on it is an error | yes | yes | `08cc49d` |
| [CON-06](constructions.md#con-06) | An active surface needs a construction with pipes | yes | no | `b22d3fe` |
| [CON-07](constructions.md#con-07) | The set of a room goes before the default of the other room | no | yes | `61d5c77` |
| [GEO-01](geometry.md#geo-01) | Adjacent surfaces may be 0.02 m apart by default, not about 0.5 m | yes | no | `a93769f` |
| [GEO-02](geometry.md#geo-02) | Reversed normals are corrected, not reported as an error | no | yes | `a93769f` |
| [GEO-03](geometry.md#geo-03) | Partly overlapping adjacent surfaces are split, not left without a partner | no | yes | `a93769f` |
| [GEO-04](geometry.md#geo-04) | A split active surface becomes a serial circuit, also inside one | no | yes | `ee12487`, `ce5a1f4` |
| [COM-01](components.md#com-01) | `checkAdjacent` removed from the shared functions | yes | no | `a93769f` |
| [COM-02](components.md#com-02) | Log Check lost the input `start_time` | no | no | `3e05d53` |
| [COM-03](components.md#com-03) | A component in error upstream stops `Lizard_System` | yes | no | `a8af542` |
| [COM-04](components.md#com-04) | `PeopleGain`, `EquipmentGain` and `LightGain` of `Lizard_Zone_Regime` take lists | no | yes | `833515d` |
| [COM-05](components.md#com-05) | The installer of a release stays at its release instead of following `main` | no | yes | `633fd39` |
| [COM-06](components.md#com-06) | The scripts moved to `components/`, manifest format 2 | no | no | `842f56d`, `931bcb2` |
| [COM-07](components.md#com-07) | Scripts changed by hand are not overwritten unless `force` is `True` | no | yes | `00bcaef` |
| [COM-08](components.md#com-08) | A required input without data stops the component | yes | no | `37353c2` |
| [RES-01](results.md#res-01) | Mirror `BOUNDARY` walls get `HBACK` 29.51 through a `_MIRROR` wall type | no | yes | `733df04` |
| [RES-02](results.md#res-02) | HAMT coupling of Type 395 changed on both sides | no | yes | `916c405`, `d2a3ce8` |
| [RES-03](results.md#res-03) | One HAMT pseudo-wall type per construction | no | yes | `c9862bf` |
| [RES-04](results.md#res-04) | Several `MiscGain` get their own name, power and schedule | no | yes | `833515d` |
| [RES-05](results.md#res-05) | The equipment reduction uses the threshold of the equipment gain | no | yes | `833515d` |
| [RES-06](results.md#res-06) | The second active layer circuit also goes to the BACK | no | yes | `da1012e` |
| [RES-07](results.md#res-07) | `MFLOWMIN` follows `SpecMassFlow` instead of a fixed 11; the BACK takes `NLOOP` from the FRONT | no | yes | not committed yet |

## Adding an entry

1. Pick the category, or add a file and a row to the table above when none fits.
2. Take the next free ID of that category. IDs are never reused.
3. Write the entry with **Before**, **Now** and **Existing definitions**, and add **Results** when they can change.
4. Add the row to the index. Replace "not committed yet" with the commit once there is one.

## How complete this is

The entries from `a93769f` on come from reading the old and the new code. The older ones were picked from the commit messages between
`c236064` and `5ad40f3`, not from a full comparison of the code. None of them has been checked by running an old definition in Rhino.
