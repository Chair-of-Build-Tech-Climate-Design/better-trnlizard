from __future__ import annotations

import re
import unittest
from collections import OrderedDict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
COMPONENT_SOURCE = REPO_ROOT / "Lizard_Component.py"


class OrderedAttributes(OrderedDict):
    """Python 2-style mapping with deterministic iteration order."""

    def iteritems(self):
        return self.items()


class StubItem:
    __slots__ = ("_attributes",)

    def __init__(self):
        self._attributes = OrderedAttributes(
            [
                ("Gain", 1),
                ("Conv", 0),
                ("Rad", 0),
                ("Convective", "INPUT 0.4*Q_COMP_KJ_A1"),
                ("Radiative", "INPUT 0.6*Q_COMP_KJ_A1"),
            ]
        )

    @property
    def __dict__(self):
        return self._attributes

    def __getattr__(self, name):
        try:
            return self._attributes[name]
        except KeyError:
            raise AttributeError(name)


class StubTemplate:
    Gain = (
        "CONVECTIVE=@self.Convective : "
        "RADIATIVE=@self.Radiative : "
        "LITERAL=@selfXConvective"
    )


def load_render_functions():
    source = COMPONENT_SOURCE.read_text(encoding="utf-8")
    start = source.index("@timing\ndef printData")
    end = source.index("@timing\ndef getDataParagraph", start)
    namespace = {
        "re": re,
        "Template": StubTemplate,
        "timing": lambda function: function,
    }
    exec(compile(source[start:end], str(COMPONENT_SOURCE), "exec"), namespace)
    return namespace["printData"], namespace["printSingleData"]


class TemplatePlaceholderTests(unittest.TestCase):
    def test_renderers_replace_only_exact_attribute_placeholders(self):
        print_data, print_single_data = load_render_functions()
        item = StubItem()
        expected = (
            "CONVECTIVE=INPUT 0.4*Q_COMP_KJ_A1 : "
            "RADIATIVE=INPUT 0.6*Q_COMP_KJ_A1 : "
            "LITERAL=@selfXConvective"
        )

        for renderer, argument in (
            (print_data, [item]),
            (print_single_data, item),
        ):
            with self.subTest(renderer=renderer.__name__):
                self.assertEqual(expected, renderer(argument, "Gain"))


if __name__ == "__main__":
    unittest.main()
