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
