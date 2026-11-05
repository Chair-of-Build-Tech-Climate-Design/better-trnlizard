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

<a id="res-07"></a>
## RES-07: `MFLOWMIN` and `NLOOP` of an active surface

- **Before:** `MFLOWMIN` was always 11 kg/(h m2), whatever the layer, and TRNBuild warned when its own minimum for the surface was higher. The BACK of
  an adjacent pair always had `NLOOP` 1.
- **Now:** `MFLOWMIN` is `SpecMassFlow` of the layer, and the BACK takes both values from the FRONT. A layer without a mass flow keeps 11. The warning
  now means that the set flow is really too low: raise it or split the surface.

<a id="res-08"></a>
## RES-08: `Schedule` of `Lizard_Stack_Ventilation_2`

- **Before:** ignored. The second stack ventilation could run in every hour outside the schedule of the first one, weekends included.
- **Now:** it runs in its own schedule, outside the schedule of the first one. An empty input keeps the old behaviour, and the input is no longer required.
- **Existing definitions:** check this input. A schedule that was connected without any effect now switches the windows, and one equal to that of
  `Lizard_Stack_Ventilation_1` switches the second ventilation off.

<a id="res-09"></a>
## RES-09: Weekly schedules follow the real weekdays of the simulation year

- **Before:** the Monday of a weekly schedule was always the first day of the simulation year. With a year that starts on a Thursday, the weekend of
  the schedules fell on Tuesday and Wednesday.
- **Now:** `Lizard_System` has the input `SimulationYear`. Not connected, it takes the year of an EPW weather file whose records all lie in one year.
  The b18 lists the days of each weekly schedule from the weekday of 1 January on, so Monday to Sunday of the schedule are the real ones. The deck has
  the new equations `FIRSTWEEKDAY` and `WEEKDAY` (1 = Monday ... 7 = Sunday). A typical year, another weather format, or no year keeps the old behaviour.
- **Existing definitions:** nothing has to change. A leap year gives a warning: the simulation has no 29 February, so the weekdays after 28 February are one day off.
- **Results:** with a single-year EPW, everything that follows a weekly schedule moves to the real weekdays, so results can change. Connect a year whose 1 January is a Monday, for example 2024, for the old order.

<a id="res-10"></a>
## RES-10: Site location from a TMY3 weather file

- **Before:** the location block read the latitude and the longitude of a `.tmy3` or `.tm3` file from each other's columns and kept the east-positive
  longitude. Fresno (latitude 36.783, longitude -119.717) gave `LATITUDE` -119.717 and `LONGITUDE` 36.783 in the b18.
- **Now:** `LATITUDE` is 36.783 and `LONGITUDE` is 119.717, west positive as in the EPW branch and in TRNBuild.
- **Existing definitions:** nothing has to change. Other weather formats are not touched.
- **Results:** Radiance and daylight calculations that use the site location can change with a TMY3 file. The solar position of Type 15 comes from the
  weather file, so it should not change. This comes from the code; no fixed model has been run through TRNBuild yet.
