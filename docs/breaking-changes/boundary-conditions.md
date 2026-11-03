# Boundary conditions

[Back to the index](README.md)

<a id="bc-01"></a>
## BC-01: `AUTOMATIC` equals an empty category

`AUTOMATIC` is a TRNLizard keyword. The TRNBuild manual knows only `EXTERNAL`, `INTERNAL`, `ADJACENT` and `BOUNDARY`
(`05-MultizoneBuilding.pdf`, pages 91 and 135).

- **Before:** adjacent if a partner was found, otherwise `EXTERNAL` for every surface. A floor on the ground could silently get outside air.
- **Now:** the same rule as an empty category. Adjacent where another room faces the surface; otherwise what [BC-04](#bc-04) gives. The keyword
  stays because an empty setting keeps the value of the surface, so it is the way to go back to this rule. Until BC-04, an unmatched floor was an
  error here.
- **Existing definitions:** a surface that should not follow BC-04 gets its category explicitly.

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
- **Results:** a wall without `Settings` and without a partner becomes `EXTERNAL` or `GROUND` ([BC-04](#bc-04)), so it can change results without an error once it has a
  construction. See also [CON-01](constructions.md#con-01).

<a id="bc-04"></a>
## BC-04: `FallbackBoundary`, `GroundLevel` and the category `GROUND`

Only surfaces without a category (empty or `AUTOMATIC`) that found no partner. Explicit categories are not changed, and an unmatched explicit `ADJACENT`
stays an error ([BC-02](#bc-02)).

- **Before:** `EXTERNAL` for walls and roofs, an error for floors. A floor of a solid had no Category input, so it had to be drawn again as a surface.
- **Now:** `FallbackBoundary` on `Lizard_Component` decides, and it is on when not connected. All vertices at or below `GroundLevel` (default 0) give
  `GROUND`, everything else `EXTERNAL`, for walls, roofs and floors alike. A surface with a window and an `ADDWINDOW` stay `EXTERNAL`. `GROUND`, a floor with
  `EXTERNAL` and a surface below the ground that keeps `EXTERNAL` for its window give a warning. With the option off, every such surface is an error.
  `PrintSingleSimFiles` uses the same rule, so a surface that faces another room in the full model gets the fallback there too.
- **`GROUND`:** a new category of `Lizard_Surface_Settings`, the same as `BOUNDARY` with the temperature `Tsoil`. The b18 gets `BOUNDARY` and `INPUT 1*Tsoil`,
  since TRNBuild does not know `GROUND`. Another temperature next to it is an error.
- **Construction sets:** a wall against `Tsoil` uses `ExteriorWall` and a ceiling against `Tsoil` uses `Roof`, also when set as `BOUNDARY` with `Tsoil`.
  A floor keeps `GroundFloor`.
- **Existing definitions:** a floor without a partner runs now instead of stopping. Check the warning: a floor above a storey that is not modelled gets
  `EXTERNAL` or `GROUND` from its height, and needs its own category. The model has to stand at its real height, or `GroundLevel` has to say where the ground is.
  A construction set without `ExteriorWall` or `Roof` now stops a wall or ceiling against `Tsoil` that had `InteriorWall` or `InteriorCeiling`.
- **Results:** walls and roofs without a category and without a window at or below `GroundLevel` change from `EXTERNAL` to `GROUND`, for example in a model placed below Z = 0.
  Everything else that ran before keeps its boundary conditions, apart from construction sets on surfaces against `Tsoil`.
