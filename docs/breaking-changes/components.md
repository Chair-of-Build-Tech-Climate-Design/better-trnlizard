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

<a id="com-05"></a>
## COM-05: The installer of a release stays at its release

- **Before:** the installer had no source, so `Lizard_Updater` read the latest `main` of the default repository, whatever release the file came from.
- **Now:** the installer attached to a release has a panel named `source <release>` at the input `source`, with the commit of that release. The instructions
  panel is named `TRNLizard <release>`. The same installer always installs the same scripts.
- **Existing definitions:** nothing, this is only the installer file. To install newer scripts, take the installer of a newer release, or replace the panel by
  a GitHub URL or a folder. Components already in a definition follow the `source` of their own `Lizard_Updater`.

<a id="com-06"></a>
## COM-06: The scripts moved to `components/`, manifest format 2

- **Before:** the component scripts were at the root of the repository, and `trnlizard_manifest.json` (format 1) listed them as `<script>.py`.
- **Now:** the scripts are in `components/`, and the manifest (format 2) lists them as `components/<script>.py`. The manifest, `trnlizard_icons.json` and
  `trnlizard_presets.json` stay at the root. `Lizard_Updater` still reads a source with the old layout, such as an older release.
- **Existing definitions:** nothing in the definition changes, since components are matched by name. Only an older `Lizard_Updater` needs a change:
  - With a GitHub source, it stops with `format 2 is newer than this updater reads` and changes nothing.
  - With a local clone as `source`, it stops with `No Python files found in source folder` and changes nothing.
  - In both cases, paste `components/Lizard_Updater.py` into it by hand, or take the installer of a newer release. An installer that is fixed to its release
    (COM-05) keeps installing that release.

<a id="com-07"></a>
## COM-07: Scripts changed by hand are no longer overwritten

- **Before:** `Lizard_Updater` replaced every script that differed from the source, so changes made by hand in a component were lost without notice.
- **Now:** every script it writes starts with a line that holds the hash of the script. A script that no longer matches that hash is left alone and listed under
  `errors`, and so is a shared cluster that contains one. The new input `force` overwrites them when it is `True`, and those changes are lost.
- **Existing definitions:**
  - The first update adds the hash line to every script, also to those already up to date.
  - A script without that line cannot be checked and is updated as before, so changes made before that first update are still overwritten.
  - A script that stays changed keeps its old code, which can give other results than the current scripts.
  - An updater that upgrades itself gets the input `force` by itself. For an updater pasted by hand, add an input named `force`, or take a new one from the
    TRNLizard tab.
