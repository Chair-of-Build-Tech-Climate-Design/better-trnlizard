# Lizard_Placeholder

`Lizard_Placeholder` stands in for the component a wire needs. Connect it to a TRNLizard component and it becomes what that input or output takes, so you do not have to look up which component fits. You find it in the `TRNLizard` tab, under `5 | Tools`.

## Using it

1. Place a `Lizard_Placeholder` on the canvas.
2. Connect its `Output` to an input of a TRNLizard component, or connect an output of a TRNLizard component to its `Input`.

What happens then depends on what that input or output can take:

| Candidates | Result |
| --- | --- |
| One | The Placeholder is replaced by it, at the same place and with the wire. |
| Several | A window asks which one. Type to filter the list, use the arrow keys to move, and press Enter to confirm. |
| None | The wire is removed. A warning, and a short text under the component, say why. |

An input with a fixed set of values gets a Value List, on the `Default` of the input if it has one.

**Cancel** in the window removes the new wire and leaves everything else as it was. **Ctrl+Z** after a replacement brings the Placeholder back without wires, ready for the next try.

## Which wires count

Only a new wire does something, and it takes over: when the Placeholder is replaced, its other wires go too.

| Wire | Result |
| --- | --- |
| One new wire to a TRNLizard component, or one new wire on `Input` | Used as above. |
| Several new wires at once (only possible with the solver locked) | Nothing happens, and a warning asks to remove all but one. The one that is left is then used. |
| Already there when the Placeholder is first computed (pasted or loaded) | Does nothing. `Waiting for a wire` under the component says so. |
| To a component that is not a TRNLizard component, or to the outer input of a cluster | Stays and does nothing. |

Only components written by `Lizard_Updater` notice a Placeholder. Run the updater once if a TRNLizard component in an older definition does not react.

While the window is open, the components after the wire are not computed: they compute once, after your choice. Grasshopper reports this as `Solution aborted by user`, which is not an error.

## Adding candidates

The candidates come from the docstrings of the scripts. Add these lines to an input, after `Required`:

```text
Args:
    Regime (object): connect the regime component
        Access: item
        Required: False
        Source: Lizard_Zone_Regime.Regime, Lizard_Lite_Zone_Regime.Regime

    Mode (object): comfort evaluation mode
        Access: item
        Required: True
        Options: PMV, Elevated Air Speed=SET
```

- `Source: Lizard_X.Output, Lizard_Y.Output` names the outputs that feed the input. An output offers the inputs that name it, so this line belongs on the input only.
- `Options: A, B` lists the values of the input for a Value List. `Label=value` shows the label and passes the value. Only list a complete set of values: a few common ones are not options.

Then run `python tools/build_manifest.py`. It writes these lines into the tables of `components/Lizard_Placeholder.py` and stops when a `Source` names an output that no script has.
