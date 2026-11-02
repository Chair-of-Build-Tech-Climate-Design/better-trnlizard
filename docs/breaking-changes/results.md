# Results

[Back to the index](README.md)

These need no change to a definition. Results of old and new runs are not directly comparable.

<a id="res-01"></a>
## RES-01: `HBACK` of mirror `BOUNDARY` walls

- **Before:** the library default `HBACK` 64 kJ/(h m2 K), an exterior value, on walls facing an unmodelled neighbour.
- **Now:** a derived wall type `<name>_MIRROR` with `HBACK` 29.51, the convective film plus longwave. An explicit value is kept, and exterior walls
  keep their type.

<a id="res-02"></a>
## RES-02: HAMT coupling of Type 395

Only surfaces with Type 395.

- **Side 1:** coupled through the star node of Type 56, so that the zone and the wall exchange the same energy.
- **Side 2 of `EXTCALBND`:** an implicit combined film, without a loop through TRNSYS.
- **Side 2 of `EXTCALEXT`:** exterior solar gain from a Type 15 tilted surface (it was zero before), and longwave from the surface temperature of
  the previous time step.

<a id="res-03"></a>
## RES-03: HAMT pseudo-wall types

- **Before:** all HAMT surfaces shared `HIGH_COND`, with the films of the construction handled last.
- **Now:** one wall type `<construction>_HAMT` per construction, with its own films.
