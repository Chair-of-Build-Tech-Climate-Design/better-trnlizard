# Constructions

[Back to the index](README.md)

<a id="con-01"></a>
## CON-01: No default construction

- **Before:** `Lizard_Surface` without `Settings` used `IFL_L`.
- **Now:** the construction stays empty until a later `Lizard_Surface` or a `Lizard_Construction_Set` fills it. A surface still without one
  stops the model, and the error names the slot to fill.
- **Existing definitions:** connect `Settings` with a construction, or one `Lizard_Construction_Set` to `Lizard_Multizone`.

<a id="con-02"></a>
## CON-02: Different constructions on one pair

- **Before:** not checked.
- **Now:** an error unless both are the same or their layers are exact mirrors, such as `IFL_L` and `ICL_L` in the library.
- **Existing definitions:** give both sides the same or the mirrored construction.

<a id="con-03"></a>
## CON-03: An empty FRONT cannot follow a non-symmetric BACK

A construction lists its layers from its FRONT side, so following it from the wrong side reverses the wall.

- **Before:** not applicable: a surface always had a construction.
- **Now:** an error. A set with only `InteriorCeiling` runs into this, because the floor is the FRONT of its pair.
- **Existing definitions:** fill the slot of the FRONT side, or use a symmetric construction.

<a id="con-04"></a>
## CON-04: The side with the construction is FRONT

- **Before:** `FRONT` was the default of every surface, and the same value on both sides was reported and corrected.
- **Now:** an explicit FRONT/BACK decides first. Without one, the side with a construction is FRONT, then the floor, then the airnode that sorts
  first. That last case with a non-symmetric construction gives a warning.
- **Existing definitions:** nothing, unless a pair relied on the old default. Set FRONT/BACK where the direction matters.
- **Results:** a non-symmetric wall can change direction.

<a id="con-05"></a>
## CON-05: The active side of a pair is FRONT

The deck defines the circuit for the airnode of the FRONT, and only the FRONT passes its circuit on to the BACK.

- **Before:** an active surface could end up as BACK: by an explicit value, against a floor with a construction, or when its airnode sorted last.
  No message, and the deck referred to a circuit that was not defined.
- **Now:** after an explicit FRONT/BACK the active side comes first. An explicit value that makes it the BACK of a side without an active layer is
  an error. With an active layer on both sides, the FRONT still decides.
- **Existing definitions:** remove the explicit value or swap it.
- **Results:** a pair that only ran because the airnode of its FRONT has a circuit of its own now uses the circuit of the active surface.

<a id="con-06"></a>
## CON-06: An active surface needs a construction with pipes

- **Before:** not checked after `Lizard_Active_Layer_Surface`. A later surface component with another construction kept the active layer values on
  a wall without pipes.
- **Now:** an error. Changing only other settings after `Lizard_Active_Layer_Surface` still works. Another construction with pipes is not
  detected: the pipe values and `Nloops` stay those of the first one.
- **Existing definitions:** set the construction before `Lizard_Active_Layer_Surface`.
