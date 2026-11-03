# Components

[Back to the index](README.md)

<a id="com-01"></a>
## COM-01: `checkAdjacent` removed

- **Before:** `sc.sticky[sc.doc.Path]["checkAdjacent"]` was a shared function.
- **Now:** `compileModel` replaces it.
- **Existing definitions:** only custom scripts that call it need a change. All TRNLizard components are updated by `Lizard_Updater`.

<a id="com-02"></a>
## COM-02: Log Check input `start_time`

- **Before:** `Lizard_Log_Check` had the input `start_time`.
- **Now:** removed as redundant.
- **Existing definitions:** nothing has to change.

<a id="com-03"></a>
## COM-03: A component in error upstream stops `Lizard_System`

A component in error often leaves its output empty, which looks like an input that is not connected. A room could disappear from the model
that way, and with the rules of [BC-03](boundary-conditions.md#bc-03) the walls of its neighbours would then get outside air.

- **Before:** `Lizard_System` wrote the model with what it received.
- **Now:** `Lizard_System` follows its inputs back through all wires, also through merges. With an error anywhere it writes nothing and lists the
  errors. `Lizard_Thermal_Airnode` and `Lizard_Multizone` show the same errors at once. Warnings and locked components do not count.
- **Existing definitions:** fix the red components. An error that is not relevant has to go as well, for example by removing that component from
  the path to `Lizard_System`.

<a id="com-04"></a>
## COM-04: Gain inputs of `Lizard_Zone_Regime` take lists

- **Before:** `PeopleGain`, `EquipmentGain` and `LightGain` had item access. A flat list of several gains in one of them ran the component once per gain,
  which gave several regimes and so several airnodes.
- **Now:** they have list access. A flat list is one regime with several gains of that kind, each with its own power and schedule. Data in several branches
  still gives one regime per branch.
- **Existing definitions:** `Lizard_Updater` sets the list access on these inputs and keeps the wires. With one gain per input nothing changes. A definition
  that used a flat list to get one airnode per gain has to put each gain in its own branch, for example with Graft; otherwise it gets one airnode, without an
  error. With several people gains, the CO2 per person of TRNFlow stops `Lizard_System`, since TRNFlow takes one CO2 source schedule.
