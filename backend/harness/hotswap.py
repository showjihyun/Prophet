"""F22 — Module Hot-Swap.
SPEC: docs/spec/09_HARNESS_SPEC.md#7-f22--module-hot-swap
"""
from __future__ import annotations

from typing import Any


class ModuleRegistry:
    """Runtime module replacement without restarting simulation.

    Used in harness to test alternative implementations.
    SPEC: docs/spec/09_HARNESS_SPEC.md#7-f22--module-hot-swap

    Usage::

        registry = ModuleRegistry()
        registry.register("llm_adapter", real_llm)
        old = registry.swap("llm_adapter", MockLLMAdapter())
        # ... run tests ...
        registry.swap("llm_adapter", old)  # restore
    """

    def __init__(self) -> None:
        self._registry: dict[str, Any] = {}

    def register(self, name: str, module: Any) -> None:
        """Register a named module.

        SPEC: docs/spec/09_HARNESS_SPEC.md#7-f22--module-hot-swap
        """
        self._registry[name] = module

    def swap(self, name: str, new_module: Any) -> Any:
        """Replace module, returns old module for restoration.

        SPEC: docs/spec/09_HARNESS_SPEC.md#7-f22--module-hot-swap
        """
        old = self._registry.get(name)
        self._registry[name] = new_module
        return old

    def get(self, name: str) -> Any:
        """Retrieve a registered module by name.

        SPEC: docs/spec/09_HARNESS_SPEC.md#7-f22--module-hot-swap

        Raises:
            KeyError: if no module is registered under *name*.
        """
        return self._registry[name]

    def __contains__(self, name: str) -> bool:
        return name in self._registry

    def registered_names(self) -> list[str]:
        """Return a sorted list of all registered module names."""
        return sorted(self._registry.keys())


__all__ = ["ModuleRegistry"]
