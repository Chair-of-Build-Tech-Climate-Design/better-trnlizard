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
  A window across the split line and a surface in a serial active layer circuit stay errors.
- **Existing definitions:** nothing.
- **Results:** those surfaces now exchange heat with the neighbour. New surface numbers depend on the geometry.
