# Copyright (c) MENACE SANTANA by vraibledard
# Licensed under the MIT License.
from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass, field
from typing import Callable

import modules


@dataclass
class Tool:
    id: str
    name: str
    icon: str
    description: str
    order: int
    run: Callable[[], None]
    tags: list[str] = field(default_factory=list)


@dataclass
class Category:
    id: str
    name: str
    title: str
    icon: str
    description: str
    order: int
    tools: list[Tool] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


def discover() -> tuple[list[Category], list[str]]:
    """Retourne (catégories triées, erreurs de chargement)."""
    categories: list[Category] = []
    global_errors: list[str] = []

    for cat_info in pkgutil.iter_modules(modules.__path__):
        if not cat_info.ispkg or cat_info.name.startswith("_"):
            continue
        try:
            pkg = importlib.import_module(f"modules.{cat_info.name}")
        except Exception as e:
            global_errors.append(f"modules/{cat_info.name}: {type(e).__name__}: {e}")
            continue

        meta = getattr(pkg, "CATEGORY", {})
        cat = Category(
            id=cat_info.name,
            name=meta.get("name", cat_info.name.capitalize()),
            title=meta.get("title", cat_info.name.upper()),
            icon=meta.get("icon", "📁"),
            description=meta.get("description", ""),
            order=meta.get("order", 100),
        )

        for tool_info in pkgutil.iter_modules(pkg.__path__):
            if tool_info.name.startswith("_"):
                continue
            path = f"modules/{cat_info.name}/{tool_info.name}"
            try:
                mod = importlib.import_module(f"modules.{cat_info.name}.{tool_info.name}")
            except Exception as e:
                cat.errors.append(f"{path}: {type(e).__name__}: {e}")
                continue

            meta_t = getattr(mod, "TOOL", None)
            run = getattr(mod, "run", None)
            if not isinstance(meta_t, dict) or not callable(run):
                cat.errors.append(f"{path}: il faut un dict TOOL et une fonction run()")
                continue

            cat.tools.append(Tool(
                id=tool_info.name,
                name=meta_t.get("name", tool_info.name),
                icon=meta_t.get("icon", "🔧"),
                description=meta_t.get("description", ""),
                order=meta_t.get("order", 100),
                run=run,
                tags=list(meta_t.get("tags", [])),
            ))

        cat.tools.sort(key=lambda t: (t.order, t.name.lower()))
        categories.append(cat)

    categories.sort(key=lambda c: (c.order, c.name.lower()))
    return categories, global_errors
