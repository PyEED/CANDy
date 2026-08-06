from __future__ import annotations

from collections.abc import Callable


class ManualCurationBackend:
    """Interactively prompt the user to group synonymous domain names.

    ``input_fn``/``print_fn`` are injectable so this can be driven
    programmatically in tests without touching real stdin/stdout.
    """

    name = "manual"

    def __init__(
        self,
        input_fn: Callable[[str], str] = input,
        print_fn: Callable[[str], None] = print,
    ) -> None:
        self._input = input_fn
        self._print = print_fn

    def curate(self, domain_names: list[str], *, family: str | None = None) -> dict[str, list[str]]:
        remaining = dict(enumerate(domain_names))
        curated: dict[str, list[str]] = {}

        while remaining:
            self._print("\nDomains still to curate:")
            for index, name in remaining.items():
                self._print(f"{index}: {name}")

            umbrella_name = self._input("\nDomain name: ").strip()
            if umbrella_name.upper() == "STOP":
                for name in remaining.values():
                    curated[name] = [name]
                break

            indices = [int(i) for i in self._input("Includes: ").strip().split(",")]
            curated[umbrella_name] = [remaining.pop(i) for i in indices]

        return curated
