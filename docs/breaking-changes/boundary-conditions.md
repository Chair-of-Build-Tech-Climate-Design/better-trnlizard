# Boundary conditions

[Back to the index](README.md)

<a id="bc-01"></a>
## BC-01: `AUTOMATIC` equals an empty category

`AUTOMATIC` is a TRNLizard keyword. The TRNBuild manual knows only `EXTERNAL`, `INTERNAL`, `ADJACENT` and `BOUNDARY`
(`05-MultizoneBuilding.pdf`, pages 91 and 135).

- **Before:** adjacent if a partner was found, otherwise `EXTERNAL` for every surface. A floor on the ground could silently get outside air.
- **Now:** the same rule as an empty category. Adjacent where another room faces the surface; otherwise `EXTERNAL` for walls and roofs, and an
  error for floors. The keyword stays because an empty setting keeps the value of the surface, so it is the way to go back to this rule.
- **Existing definitions:** a floor that really has outside air below gets the category `EXTERNAL`. Any other floor gets `BOUNDARY` with its
  temperature. The error names the surface.

<a id="bc-02"></a>
## BC-02: Unmatched `ADJACENT` is an error

- **Before:** a message, then `BOUNDARY` with the air temperature of the room itself, and the model was still written.
- **Now:** an error, and nothing is written. `PrintSingleSimFiles` keeps the old mirror, because the neighbours are missing on purpose there.
- **Existing definitions:** fix the partner surface, or set `BOUNDARY` explicitly if the mirror is what you want.

<a id="bc-03"></a>
## BC-03: Empty settings no longer mean a mirrored `BOUNDARY`

- **Before:** `Lizard_Surface` without `Settings` used `BOUNDARY`, `TAIR_@ANAME`, `IFL_L` and `FRONT`.
- **Now:** nothing is set. `compileModel` decides the category after adjacency: see BC-01.
- **Existing definitions:** connect `Settings` with `BOUNDARY` and `TAIR_@ANAME` to the surfaces that relied on the default.
- **Results:** a wall without `Settings` and without a partner becomes `EXTERNAL`, so it can change results without an error once it has a
  construction. See also [CON-01](constructions.md#con-01).
