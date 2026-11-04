# Geometry

[Back to the index](README.md)

<a id="geo-01"></a>
## GEO-01: Distance between adjacent surfaces

- **Before:** two opposite surfaces could pair when their centres were less than 0.5 m apart and their areas were equal. Models with net room
  volumes and walls up to that thickness paired without any setting.
- **Now:** the planes may be at most `GapTolerance` apart, 0.02 m by default. Further apart they stay unpaired, with a warning that gives the
  distance.
- **Existing definitions:** connect `GapTolerance` on `Lizard_Multizone` with the thickest wall, or draw the rooms on the wall centre lines.

<a id="geo-02"></a>
## GEO-02: Reversed normals

- **Before:** an error for the surface.
- **Now:** corrected by `Lizard_Thermal_Airnode` when the surfaces close a volume, with a remark and the surfaces at `OriToCheck`. The normal is
  read from the underlying surface and `OrientationIsReversed` is applied once (since `fd12ff4`), so a correct face of a solid is not flipped.
- **Existing definitions:** nothing.
- **Results:** a definition that was stopped before now runs.

<a id="geo-03"></a>
## GEO-03: Partly overlapping adjacent surfaces

- **Before:** a warning unless the two areas were equal. The model was still written: an `ADJACENT` surface fell back to a mirrored `BOUNDARY`
  and an `AUTOMATIC` one to `EXTERNAL`.
- **Now:** split along what faces them. The biggest piece keeps the surface number and the others get new numbers above the highest one.
  A window across the split line stays an error. An active surface: see [GEO-04](#geo-04).
- **Existing definitions:** nothing.
- **Results:** those surfaces now exchange heat with the neighbour. New surface numbers depend on the geometry.

<a id="geo-04"></a>
## GEO-04: A split active surface becomes a serial circuit

- **Before:** since [GEO-03](#geo-03), the pieces of an active surface all started at the supply temperature and each got the mass flow of the
  whole airnode, without a message. The flow per area was too high and the return temperature came from the last piece only. A surface in a
  serial circuit was an error.
- **Now:** the second piece takes its supply from the outlet of the first (`TOFL_S`), biggest piece first, like the surfaces of a list on
  `Lizard_Active_Layer_Surface`, with a warning. In a serial circuit, what took its supply from the surface now takes it from the last piece.
- **Existing definitions:** nothing. Split the surface yourself if the pipes do not run through the pieces in that order, or run in parallel.
- **Results:** the mass flow per area of a split active surface goes back to the set value.

<a id="geo-05"></a>
## GEO-05: A window in no wall of its airnode is an error

- **Before:** a window that lay in no wall of its airnode, for example connected to the wrong airnode, was left out of the b18 without an error.
  `Lizard_Model_Inspect` still listed it. The same happened to a window that Rhino could not cut out of its wall.
- **Now:** `compileModel` reports an error with the window, so `Lizard_Model_Inspect` shows it and `Lizard_System` stops. `Lizard_Thermal_Airnode`
  warns as well, and its message about surfaces that do not close a volume is now a warning instead of a remark.
- **Existing definitions:** connect the window to the airnode of its wall, or move it onto the wall.
- **Results:** a model that lost windows this way gets them back after the fix.
