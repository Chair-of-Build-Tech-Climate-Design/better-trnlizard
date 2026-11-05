# Better TRNLizard

A maintained fork of [TRNLizard](https://www.food4rhino.com/en/app/trnlizard), the Grasshopper plug-in for parametric thermal and daylight building simulation with TRNSYS 18. You define the model in Grasshopper, and TRNLizard writes it as a complete TRNSYS model into the project directory.

**Author:** [Junfeng Xiao](https://github.com/JunfXiao)

## Origin and acknowledgement

The source code is based on this version of TRNLizard from [food4rhino](https://www.food4rhino.com/en/app/trnlizard):

`TRNLizard Component Package 06/2019 2019-06-27`

Many thanks to the original authors, **[Christian Frenzel](https://transsolar.com/de/team/christian-frenzel)** and **TRANSSOLAR Energietechnik GmbH**, for creating TRNLizard and sharing it with the building simulation community.

## What this fork adds

- **Install and update from GitHub.** `Lizard_Updater` downloads new and changed scripts, updates the script components of a definition, and writes all components and presets as UserObjects into the `TRNLizard` tab.
- **Multizone models from geometry.** Rooms pair by geometry, partly overlapping surfaces are split, and a zone accepts closed solids next to surfaces. Unmatched surfaces follow `FallbackBoundary` and `GroundLevel`.
- **Constructions and gains.** Construction and boundary condition can be set separately, `Lizard_Construction_Set` fills what is left, and `Lizard_Zone_Regime` takes several gains of one kind.
- **Hygrothermal walls.** `Lizard_Hygro` and a reworked coupling to TRNSYS Type 395 (HAMT). Type 395 itself is not part of this repository.
- **Airflow and ventilation.** `Lizard_Trnflow_Network` defines a TRNFlow airflow network, and `Lizard_Stack_Ventilation_2` adds a second stack ventilation.
- **Placeholder.** `Lizard_Placeholder` becomes what a wire needs: connect it to an input or output of a TRNLizard component and it is replaced by the Value List or component that fits, or asks which one. See [docs/placeholder.md](docs/placeholder.md).
- **Checks.** `Lizard_Model_Inspect` shows the compiled model without writing anything, and an error upstream stops the components after it.
- **Fixes.** Many fixes to the written b18 and deck, with a test suite that runs without Rhino.

> [!IMPORTANT]
> Existing definitions can stop or give different results. [docs/breaking-changes](docs/breaking-changes/README.md) lists each change and the smallest fix.

## Requirements

- Windows
- Rhino 7 or 8 with Grasshopper
- TRNSYS 18

## Installation

1. Download `TRNLizard_Installer.ghx` from the [latest release](https://github.com/JunfXiao/better-trnlizard/releases/latest).
2. Open it in Grasshopper.
3. Set `runUpdate` to `True` (double-click the toggle) and wait for the log.
4. Restart Rhino. The `TRNLizard` tab then holds all components and presets.

The installer stays at its release. To install other scripts, replace the panel at `source` with a GitHub URL (optionally ending in `/tree/<branch or tag>`) or a local folder.

The installer also moves the UserObjects of earlier TRNLizard installs out of the UserObjects folder. Set `cleanOldUserObjects` to `False` to only list them in the log.

### Updating an existing definition

Add a `Lizard_Updater` component to the definition and set `runUpdate` to `True`. With an empty `source`, it follows `main` of the [chair's repository](https://github.com/Chair-of-Build-Tech-Climate-Design/better-trnlizard). A component that lost inputs or outputs is replaced by a new copy in a red group, next to the locked old one. The docstring at the top of [components/Lizard_Updater.py](components/Lizard_Updater.py) has the details.

With a GitHub source, `Lizard_Updater` also upgrades itself. It checks the new version, including its syntax, before it replaces its own code. If a check fails, it stays as it is and the log points to the installer.

Scripts changed by hand are left alone and listed under `errors`. Setting `force` to `True` overwrites them, and those changes are lost.

## About the chair

This project comes from the **Chair of Building Technology and Climate Responsive Design** (*Lehrstuhl für Gebäudetechnologie und klimagerechtes Bauen*), led by Prof. Thomas Auer at the TUM School of Engineering and Design, Technical University of Munich.

The chair's teaching and research follow a holistic approach to building design: high comfort inside buildings and in the spaces around them, with minimal energy use. Its research uses simulation software as a planning instrument.

Meet the team: [English](https://www.arc.ed.tum.de/en/klima/team/) · [Deutsch](https://www.arc.ed.tum.de/klima/team/)

## Contributing

Issues and contributions are very welcome, whether a bug report, a question, an idea or a pull request. Please [open an issue](https://github.com/JunfXiao/better-trnlizard/issues) or send a pull request.

For a bug report, the Rhino and TRNSYS versions and the smallest definition that shows the problem help most.

For a pull request:

- The `components/Lizard_*.py` scripts are IronPython 2 code. The tests run on plain Python 3: `python -m unittest discover -s tests`
- After changing a script, icon or preset, run `python tools/build_manifest.py` and commit the result. CI checks it.
- A line `StandardOutput: False` before `Args:` in the docstring of a script means that its UserObject has no output `out`.
- An input in the docstring of a script can have more lines after `Required`. `Options: A, B` lists the values to choose from (`Label=value` for a value with a label), for the mouse-over text and for the Value List of `Lizard_Placeholder`. `Source: Lizard_X.Output, Lizard_Y.Output` names the outputs that feed the input: `Lizard_Placeholder` offers them, and offers the input for those outputs. `Default: x` is the value the script uses when the input is not set: `Lizard_Updater` stores it on inputs that have no wire and no data, and the script has to treat "not set" the same way. `Required: True` means the script cannot run without the input: `Lizard_Updater` writes one line after the docstring that stops the script with an error when such an input has no data. In Grasshopper all inputs stay optional, so that the script always runs and says what is missing.
- After changing `components/Lizard_Updater.py`, raise its `UPDATER_VERSION`. Otherwise `tools/build_manifest.py` refuses to write the manifest.
- When a change can stop a definition or change results, add an entry to [docs/breaking-changes](docs/breaking-changes/README.md).

## Citation

Citations are welcome. If this project helps your work, please cite it and give the version you used:

```bibtex
@software{xiao_better_trnlizard,
  author  = {Xiao, Junfeng},
  title   = {Better {TRNLizard}},
  year    = {2026},
  version = {V1.0.1},
  url     = {https://github.com/JunfXiao/better-trnlizard}
}
```

Please also credit the original: Christian Frenzel and TRANSSOLAR Energietechnik GmbH, *TRNLizard Component Package 06/2019*, 2019, <https://www.food4rhino.com/en/app/trnlizard>.

## License

TRNLizard is published free of charge, and its [food4rhino page](https://www.food4rhino.com/en/app/trnlizard) describes the Grasshopper components as open source and lists the license type as "Other". No license text could be found, though: the script headers say "All Rights Reserved" and refer to a `License.txt`, which the published package does not contain, and the official documentation we could find does not mention license terms.

The copyright of the original code stays with TRANSSOLAR Energietechnik GmbH, as stated in the script headers. This repository does not add a license of its own.

For questions or concerns about licensing or copyright, please [open an issue](https://github.com/JunfXiao/better-trnlizard/issues).
