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

<a id="res-04"></a>
## RES-04: several `MiscGain` in one regime

Only regimes with several `Lizard_Misc_Gains` in `MiscGain` and `HamtGain` together. One gain of each kind writes the same b18 and deck, except for
[RES-05](#res-05).

- **Before:** all gains were written as `GAIN HUMID_<zone>` with one power variable, the sum of their powers, and one regime line per schedule. The
  expected gain is `P1*S1 + P2*S2`; if TRNBuild accepted the double name, the gain was `(P1+P2)*(S1+S2)`. Not run in TRNBuild.
- **Now:** each further gain has its own name, power variable and equation (`HUMID2_<zone>`, `Q_ADDON_KJ2_<zone>`), so it keeps its own power, schedule,
  convective part, humidity and `HeatingBy`.
- **Results:** the old form ran each power also under the schedule of the other gain, so the gain was too high whenever a schedule was active. It gets
  lower now, and with it the radiative part that reaches Type 395 walls through `QABSI`.
- **Existing definitions:** nothing has to change. Old and new runs of these regimes are not comparable.

The inputs for people, equipment and light take several gains as well, see [COM-04](components.md#com-04). A template of your own needs `@ngainpower`, `@moregainpower` and `@sched_co2`
as in `Lizard_DCK_Template`. Without them, a further gain stops the TRNSYS run at its undefined power variable.

<a id="res-05"></a>
## RES-05: threshold of the equipment reduction

- **Before:** `OnTairoutside24hBelow` of `Lizard_Equipment_Gains` had no effect. The reduction started at the threshold of the people gain, or at 12 °C
  without one.
- **Now:** the equipment gain uses its own threshold, 12 °C when the input is not connected.
- **Results:** change when `ReductionPercentage` of the equipment gain is not 0 and its threshold differs from the one that applied so far. The deck text of
  `Q_comp_kJ` can also differ when the reduction is 0, without an effect on results.
- **Existing definitions:** nothing has to change. To keep the old behaviour, connect the threshold of the people gain to the equipment gain as well.

<a id="res-06"></a>
## RES-06: The second active layer circuit on adjacent surfaces

- **Before:** only circuit 1 went from the FRONT to the BACK, so the BACK of a surface on circuit 2 had no `INTEMP`, `MFLOW` or `NLOOP`.
- **Now:** both circuits go to the BACK.
