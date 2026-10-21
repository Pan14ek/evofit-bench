"""Generic AST analyzers for public APIs, capability graphs, and persistence ownership."""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from architecture.acceptance.a1.engine import SourceInventory, _module_exists


def _capability(module_name: str) -> str | None:
    prefix = "app.modules."
    if not module_name.startswith(prefix):
        return None
    remainder = module_name[len(prefix) :]
    return remainder.split(".", 1)[0] if remainder else None


def _finding(
    code: str,
    message: str,
    *,
    path: str | None = None,
    line: int | None = None,
    source_capability: str | None = None,
    target_capability: str | None = None,
    imported_module: str | None = None,
    imported_name: str | None = None,
) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "source_path": path,
        "line": line,
        "source_capability": source_capability,
        "target_capability": target_capability,
        "imported_module": imported_module,
        "imported_name": imported_name,
    }


def _import_finding(code: str, message: str, item: dict[str, Any]) -> dict[str, Any]:
    return _finding(
        code,
        message,
        path=item["source_path"],
        line=item["line"],
        source_capability=item.get("source_capability"),
        target_capability=item.get("target_capability") or _capability(item["target_module"]),
        imported_module=item["target_module"],
        imported_name=item.get("imported_name"),
    )


def _public_module_symbols(inventory: SourceInventory, capability: str) -> dict[str, str]:
    relative = f"app/modules/{capability}/public.py"
    tree = inventory.trees.get(relative)
    if tree is None:
        return {}
    symbols: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            symbols[node.name] = "function"
        elif isinstance(node, ast.ClassDef):
            symbols[node.name] = "type"
    return symbols


def analyze_public_api(
    config: dict[str, Any], inventory: SourceInventory, architecture_state: str
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    policy = config.get("public_api", {})
    public_pattern = str(policy.get("public_module_pattern", "app.modules.{capability}.public"))
    exception = policy.get("legacy_exception")
    errors: list[str] = []
    findings: list[dict[str, Any]] = []
    observed: list[dict[str, Any]] = []
    raw_interfaces = policy.get("interfaces_by_capability", {})
    interfaces: dict[str, dict[str, str]] = {}
    if not isinstance(raw_interfaces, dict):
        errors.append("CONFIG_PUBLIC_INTERFACES_INVALID")
    else:
        for capability, entries in raw_interfaces.items():
            if not isinstance(entries, dict):
                errors.append(f"CONFIG_PUBLIC_INTERFACES_INVALID:{capability}")
                continue
            normalized = {str(name): str(kind) for name, kind in entries.items()}
            if any(kind not in {"function", "type"} for kind in normalized.values()):
                errors.append(f"CONFIG_PUBLIC_INTERFACE_KIND_INVALID:{capability}")
            interfaces[str(capability)] = normalized
        expected_capabilities = set(config.get("source_scope", {}).get("expected_modules", []))
        if set(interfaces) != expected_capabilities or any(
            not entries for entries in interfaces.values()
        ):
            errors.append("CONFIG_PUBLIC_INTERFACES_COVERAGE_MISMATCH")

    if policy.get("require_public_module_per_capability", False):
        inspected_paths = set(inventory.source_files)
        for module in inventory.modules:
            if not module["discovered"]:
                continue
            capability = str(module["name"])
            expected_path = f"{module['path']}/public.py"
            if expected_path not in inspected_paths:
                findings.append(
                    _finding(
                        "PUBLIC_CONTRACT_MISSING",
                        f"Missing public contract: {expected_path}.",
                        path=expected_path,
                        source_capability=capability,
                    )
                )
                continue
            actual_symbols = _public_module_symbols(inventory, capability)
            expected_symbols = interfaces.get(capability, {})
            for name, expected_kind in sorted(expected_symbols.items()):
                actual_kind = actual_symbols.get(name)
                if actual_kind != expected_kind:
                    code = (
                        "PUBLIC_INTERFACE_MISSING"
                        if actual_kind is None
                        else "PUBLIC_INTERFACE_KIND_MISMATCH"
                    )
                    findings.append(
                        _finding(
                            code,
                            f"{capability}.public must define {name} as {expected_kind}.",
                            path=expected_path,
                            source_capability=capability,
                        )
                    )
            for name in sorted(set(actual_symbols) - set(expected_symbols)):
                findings.append(
                    _finding(
                        "UNDECLARED_PUBLIC_EXPORT",
                        f"{capability}.public defines undeclared interface {name}.",
                        path=expected_path,
                        source_capability=capability,
                    )
                )

    typed_dict_fields = policy.get("typed_dict_fields", {})
    if not isinstance(typed_dict_fields, dict):
        errors.append("CONFIG_TYPED_DICT_FIELDS_INVALID")
        typed_dict_fields = {}
    for qualified_name, raw_fields in typed_dict_fields.items():
        capability, separator, symbol = str(qualified_name).partition(".")
        if (
            not separator
            or not isinstance(raw_fields, list)
            or not all(isinstance(field, str) for field in raw_fields)
        ):
            errors.append(f"CONFIG_TYPED_DICT_FIELDS_INVALID:{qualified_name}")
            continue
        tree = inventory.trees.get(f"app/modules/{capability}/public.py")
        typed_dict = (
            next(
                (
                    node
                    for node in tree.body
                    if isinstance(node, ast.ClassDef)
                    and node.name == symbol
                    and any(
                        (isinstance(base, ast.Name) and base.id == "TypedDict")
                        or (
                            isinstance(base, ast.Subscript)
                            and isinstance(base.value, ast.Name)
                            and base.value.id == "TypedDict"
                        )
                        for base in node.bases
                    )
                ),
                None,
            )
            if tree is not None
            else None
        )
        if typed_dict is None:
            findings.append(
                _finding(
                    "PUBLIC_TYPED_DICT_MISSING",
                    f"{capability}.public.{symbol} is not a TypedDict.",
                    path=f"app/modules/{capability}/public.py",
                    source_capability=capability,
                )
            )
            continue
        actual_fields = {
            node.target.id
            for node in typed_dict.body
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)
        }
        expected_fields = set(raw_fields)
        if actual_fields != expected_fields:
            findings.append(
                _finding(
                    "PUBLIC_TYPED_DICT_FIELDS_MISMATCH",
                    f"{capability}.public.{symbol} fields differ from the frozen contract.",
                    path=f"app/modules/{capability}/public.py",
                    source_capability=capability,
                )
            )

    final_state = str(policy.get("final_architecture_state", "A1_MODULAR_MONOLITH"))
    allowed_states = (
        set(exception.get("allowed_architecture_states", []))
        if isinstance(exception, dict)
        else set()
    )
    if final_state in allowed_states:
        errors.append("CONFIG_LEGACY_EXCEPTION_INCLUDES_FINAL_STATE")

    for item in inventory.imports:
        source_capability = item.get("source_capability")
        target_capability = item.get("target_capability") or _capability(item["target_module"])
        if (
            source_capability is None
            or target_capability is None
            or source_capability == target_capability
        ):
            continue
        public_module = public_pattern.format(capability=target_capability)
        target_module = item["target_module"]
        if target_module == public_module:
            imported_name = item.get("imported_name")
            module_binding = item["kind"] == "import" or (
                imported_name == "public" and item.get("imported_module") != public_module
            )
            if module_binding:
                classification = "declared_public_module"
            else:
                declared_import_kind = interfaces.get(target_capability, {}).get(str(imported_name))
                actual_import_kind = _public_module_symbols(inventory, target_capability).get(
                    str(imported_name)
                )
                classification = "declared_public_interface"
                if declared_import_kind is None or actual_import_kind != declared_import_kind:
                    classification = "undeclared_public_interface"
                    findings.append(
                        _import_finding(
                            "UNDECLARED_PUBLIC_INTERFACE",
                            f"{target_capability}.public does not declare {imported_name} "
                            "as an exported contract.",
                            item,
                        )
                    )
            observed.append(
                {
                    "source_path": item["source_path"],
                    "source_module": item["source_module"],
                    "line": item["line"],
                    "target_module": target_module,
                    "target_capability": target_capability,
                    "imported_name": imported_name,
                    "classification": classification,
                }
            )
            continue
        if target_module.startswith(f"{public_module}."):
            findings.append(
                _import_finding(
                    "UNDECLARED_PUBLIC_INTERFACE",
                    f"Nested public import {target_module} is outside the frozen "
                    "public module contract.",
                    item,
                )
            )
            continue
        if target_module.startswith("app.modules."):
            is_legacy = (
                isinstance(exception, dict)
                and architecture_state in allowed_states
                and item["source_module"] == exception.get("source_module")
                and target_module == exception.get("target_module")
                and item.get("imported_name") in set(exception.get("imported_names", []))
            )
            row = {
                "source_path": item["source_path"],
                "source_module": item["source_module"],
                "line": item["line"],
                "target_module": target_module,
                "target_capability": target_capability,
                "imported_name": item.get("imported_name"),
                "classification": "legacy_exception"
                if is_legacy
                else "private_or_undeclared_contract",
            }
            observed.append(row)
            if is_legacy:
                continue
            findings.append(
                _import_finding(
                    "CROSS_MODULE_IMPORT_NOT_PUBLIC",
                    f"Non-public import {target_module}; expected {public_module}.",
                    item,
                )
            )
    return (
        {
            "public_module_pattern": public_pattern,
            "interfaces_by_capability": interfaces,
            "exports_by_capability": {
                capability: _public_module_symbols(inventory, capability)
                for capability in sorted(interfaces)
            },
            "typed_dict_fields": typed_dict_fields,
            "cross_capability_imports": observed,
            "legacy_exception": exception,
        },
        findings,
        errors,
    )


def _cycle_paths(nodes: set[str], edges: set[tuple[str, str]]) -> list[list[str]]:
    adjacency: dict[str, list[str]] = {node: [] for node in nodes}
    for source, target in sorted(edges):
        adjacency.setdefault(source, []).append(target)
        adjacency.setdefault(target, [])
    state: dict[str, int] = {}
    stack: list[str] = []
    cycles: set[tuple[str, ...]] = set()

    def visit(node: str) -> None:
        state[node] = 1
        stack.append(node)
        for target in adjacency.get(node, []):
            if state.get(target, 0) == 0:
                visit(target)
            elif state.get(target) == 1:
                start = stack.index(target)
                cycle = stack[start:] + [target]
                body = cycle[:-1]
                rotations = [tuple(body[i:] + body[:i]) for i in range(len(body))]
                canonical = min(rotations)
                cycles.add(canonical + (canonical[0],))
        stack.pop()
        state[node] = 2

    for node in sorted(adjacency):
        if state.get(node, 0) == 0:
            visit(node)
    return [list(cycle) for cycle in sorted(cycles)]


def analyze_module_graph(
    config: dict[str, Any], inventory: SourceInventory, architecture_state: str
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    policy = config.get("module_graph", {})
    states = policy.get("allowed_dependencies_by_state", {})
    forbidden_states = policy.get("forbidden_dependencies_by_state", {})
    errors: list[str] = []
    findings: list[dict[str, Any]] = []
    if architecture_state not in states:
        errors.append("CONFIG_GRAPH_STATE_UNAVAILABLE")
    allowed = {(str(edge["from"]), str(edge["to"])) for edge in states.get(architecture_state, [])}
    forbidden = {
        (str(edge["from"]), str(edge["to"]))
        for edge in forbidden_states.get(architecture_state, [])
    }
    shared_roots = tuple(
        str(item).rstrip(".") for item in policy.get("shared_infrastructure_roots", [])
    )
    edge_references: dict[tuple[str, str], list[dict[str, Any]]] = {}
    shared_imports: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    unresolved_local: list[dict[str, Any]] = []
    discovered = {item["name"] for item in inventory.modules if item["discovered"]}
    strict_roots = tuple(
        str(item).rstrip(".") for item in policy.get("strict_local_import_roots", [])
    )

    for item in inventory.imports:
        source = item.get("source_capability")
        target_module = item["target_module"]
        target = item.get("target_capability") or _capability(target_module)
        if source is None:
            continue
        if any(
            target_module == root or target_module.startswith(f"{root}.") for root in strict_roots
        ) and not _module_exists(inventory.repo_root, target_module):
            unresolved_local.append(
                {
                    "source_path": item["source_path"],
                    "line": item["line"],
                    "source_module": item["source_module"],
                    "target_module": target_module,
                    "imported_name": item.get("imported_name"),
                }
            )
            findings.append(
                _import_finding(
                    "UNRESOLVED_LOCAL_IMPORT",
                    f"Unresolved local import: {target_module}.",
                    item,
                )
            )
            continue
        if target is not None:
            reference = {
                "source_path": item["source_path"],
                "line": item["line"],
                "source_module": item["source_module"],
                "target_module": target_module,
                "imported_name": item.get("imported_name"),
            }
            if target not in discovered:
                unresolved.append(reference)
                findings.append(
                    _import_finding(
                        "UNRESOLVED_CAPABILITY_IMPORT",
                        f"Capability {target} was not discovered.",
                        item,
                    )
                )
                continue
            if source != target:
                edge_references.setdefault((source, target), []).append(reference)
            continue
        if any(
            target_module == root or target_module.startswith(f"{root}.") for root in shared_roots
        ):
            shared_imports.append(
                {
                    "source_path": item["source_path"],
                    "line": item["line"],
                    "source_module": item["source_module"],
                    "target_module": target_module,
                    "imported_name": item.get("imported_name"),
                }
            )

    observed_edges: list[dict[str, Any]] = []
    for source, target in sorted(edge_references):
        refs: list[dict[str, Any]] = edge_references[(source, target)]
        observed_edges.append(
            {
                "from": source,
                "to": target,
                "references": sorted(refs, key=lambda row: (row["source_path"], row["line"])),
            }
        )
    for edge in sorted(edge_references):
        if edge in forbidden:
            findings.append(
                _finding(
                    "FORBIDDEN_DEPENDENCY",
                    f"Forbidden capability dependency {edge[0]} -> {edge[1]} was observed.",
                    source_capability=edge[0],
                    target_capability=edge[1],
                )
            )
        elif edge not in allowed:
            findings.append(
                _finding(
                    "UNDECLARED_DEPENDENCY",
                    f"Undeclared capability edge: {edge[0]} -> {edge[1]}.",
                    source_capability=edge[0],
                    target_capability=edge[1],
                )
            )
    cycles = _cycle_paths(discovered, set(edge_references))
    for cycle in cycles:
        findings.append(
            _finding(
                "DEPENDENCY_CYCLE",
                "Capability dependency cycle detected: " + " -> ".join(cycle),
                source_capability=cycle[0],
                target_capability=cycle[1] if len(cycle) > 1 else cycle[0],
            )
        )
    return (
        {
            "nodes": sorted(discovered),
            "edges": observed_edges,
            "shared_infrastructure_imports": sorted(
                shared_imports, key=lambda row: (row["source_path"], row["line"])
            ),
            "unresolved_capability_imports": unresolved,
            "unresolved_local_imports": unresolved_local,
            "cycles": cycles,
            "allowed_edges": [{"from": source, "to": target} for source, target in sorted(allowed)],
            "forbidden_edges": [
                {"from": source, "to": target} for source, target in sorted(forbidden)
            ],
        },
        findings,
        errors,
    )


def _literal_assignment(class_node: ast.ClassDef, name: str) -> str | None:
    for node in class_node.body:
        value: ast.expr | None = None
        if isinstance(node, ast.Assign):
            if any(isinstance(target, ast.Name) and target.id == name for target in node.targets):
                value = node.value
        elif (
            isinstance(node, ast.AnnAssign)
            and isinstance(node.target, ast.Name)
            and node.target.id == name
        ):
            value = node.value
        if value is not None:
            try:
                literal = ast.literal_eval(value)
            except (ValueError, TypeError):
                return None
            return literal if isinstance(literal, str) else None
    return None


def _dotted_expression(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = _dotted_expression(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    return ""


def _is_metadata_tables(node: ast.expr) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == "tables"
        and ".metadata" in _dotted_expression(node.value)
    )


def analyze_data_ownership(
    config: dict[str, Any], inventory: SourceInventory, architecture_state: str
) -> tuple[dict[str, Any], list[dict[str, Any]], list[str]]:
    policy = config.get("data_ownership", {})
    table_owners = {str(key): str(value) for key, value in policy.get("table_owners", {}).items()}
    model_symbols: dict[str, set[str]] = {
        name: set() for name in config["source_scope"]["expected_modules"]
    }
    discovered_tables: dict[str, dict[str, str]] = {}
    findings: list[dict[str, Any]] = []
    errors: list[str] = []
    table_mismatches: list[dict[str, str]] = []
    for relative, tree in inventory.trees.items():
        parts = Path(relative).parts
        if len(parts) == 4 and parts[:2] == ("app", "modules") and parts[3] == "model.py":
            capability = parts[2]
            for class_item in tree.body:
                if isinstance(class_item, ast.ClassDef):
                    table = _literal_assignment(class_item, "__tablename__")
                    if table:
                        model_symbols.setdefault(capability, set()).add(class_item.name)
                        discovered_tables[table] = {"owner": capability, "model": class_item.name}
                        declared_owner = table_owners.get(table)
                        if declared_owner is not None and declared_owner != capability:
                            table_mismatches.append(
                                {
                                    "table": table,
                                    "configured_owner": declared_owner,
                                    "source_owner": capability,
                                }
                            )
    for declared_table, expected_owner in table_owners.items():
        declaration = discovered_tables.get(declared_table)
        if declaration is None:
            errors.append(f"SOURCE_TABLE_DECLARATION_MISSING:{declared_table}")
        elif declaration["owner"] != expected_owner:
            errors.append(
                f"SOURCE_TABLE_OWNER_MISMATCH:{declared_table}:{expected_owner}!={declaration['owner']}"
            )
    for table_name, declaration in discovered_tables.items():
        if table_name not in table_owners:
            findings.append(
                _finding(
                    "UNCONFIGURED_TABLE_OWNER",
                    f"Table {table_name} has no configured owner.",
                    target_capability=declaration["owner"],
                )
            )
    for mismatch in table_mismatches:
        findings.append(
            _finding(
                "MODEL_TABLE_OWNERSHIP_MISMATCH",
                (
                    f"Ownership mismatch for {mismatch['table']}: "
                    f"expected {mismatch['configured_owner']}, found {mismatch['source_owner']}."
                ),
                target_capability=mismatch["source_owner"],
            )
        )

    exception = policy.get("model_registry_exception", {})
    exception_path = str(exception.get("path", "app/db/model_registry.py"))
    exception_module = str(exception.get("module", "app.db.model_registry"))
    allowed_registry_imports: list[dict[str, Any]] = []
    disallowed_symbols = policy.get("disallowed_persistence_symbols", [])
    disallowed_modules = set(policy.get("disallowed_persistence_modules", []))
    symbol_owners = {symbol: cap for cap, symbols in model_symbols.items() for symbol in symbols}
    import_bindings: dict[str, dict[str, dict[str, dict[str, str | None]]]] = {}
    for item in inventory.imports:
        source_path = item["source_path"]
        source_capability = item.get("source_capability")
        target_module = item["target_module"]
        target_capability = item.get("target_capability") or _capability(target_module)
        imported_name = item.get("imported_name")
        if item["kind"] == "import":
            import_bindings.setdefault(source_path, {}).setdefault("modules", {})[
                item["binding"]
            ] = {"module": target_module, "capability": target_capability, "name": None}
        elif imported_name:
            import_bindings.setdefault(source_path, {}).setdefault("symbols", {})[
                item["binding"]
            ] = {"module": target_module, "capability": target_capability, "name": imported_name}

        if source_path == exception_path:
            allowed_suffix = str(exception.get("allowed_target_suffix", ".model"))
            if target_capability and target_module.endswith(allowed_suffix):
                allowed_registry_imports.append(
                    {
                        "source_path": source_path,
                        "line": item["line"],
                        "target_module": target_module,
                        "target_capability": target_capability,
                        "imported_name": imported_name,
                    }
                )
            elif target_module.startswith("app.modules."):
                findings.append(
                    _import_finding(
                        "UNJUSTIFIED_INFRASTRUCTURE_EXCEPTION",
                        f"Registry exception cannot cover {target_module}.",
                        item,
                    )
                )

        if (
            source_capability is not None
            and target_capability
            and source_capability != target_capability
        ):
            suffix = target_module.rsplit(".", 1)[-1]
            if suffix == "repository":
                findings.append(
                    _import_finding(
                        "FOREIGN_REPOSITORY_IMPORT",
                        f"{source_capability} imports foreign repository {target_capability}.",
                        item,
                    )
                )
            elif suffix == "model" or imported_name in model_symbols.get(target_capability, set()):
                findings.append(
                    _import_finding(
                        "FOREIGN_MODEL_IMPORT",
                        f"{source_capability} imports foreign model {target_capability}.",
                        item,
                    )
                )
            if item.get("imported_name") is None and target_module == exception_module:
                findings.append(
                    _import_finding(
                        "DISALLOWED_PERSISTENCE_DEPENDENCY",
                        f"{source_capability} imports the model registry directly.",
                        item,
                    )
                )

        imported_module = item.get("imported_module") or target_module
        for rule in disallowed_symbols:
            if imported_module == rule.get("module") and (
                item.get("imported_name") in set(rule.get("names", []))
                or "*" in set(rule.get("names", []))
            ):
                findings.append(
                    _import_finding(
                        "DISALLOWED_PERSISTENCE_DEPENDENCY",
                        f"Disallowed persistence symbol {imported_module}.",
                        item,
                    )
                )
        if source_capability is not None and target_module in disallowed_modules:
            findings.append(
                _import_finding(
                    "DISALLOWED_PERSISTENCE_DEPENDENCY",
                    f"Disallowed persistence module: {target_module}.",
                    item,
                )
            )

    table_accesses: list[dict[str, Any]] = []
    orm_accesses: list[dict[str, Any]] = []
    for relative, tree in inventory.trees.items():
        source_capability = next(
            (
                item.get("source_capability")
                for item in inventory.imports
                if item["source_path"] == relative
            ),
            None,
        )
        if source_capability is None:
            # Files without imports are still capability sources.
            # Derive their package from the path.
            parts = Path(relative).parts
            if len(parts) >= 4 and parts[:2] == ("app", "modules"):
                source_capability = parts[2]
        if source_capability is None:
            continue
        bindings = import_bindings.get(relative, {})
        module_bindings = bindings.get("modules", {})
        symbol_bindings = bindings.get("symbols", {})
        for source_node in ast.walk(tree):
            accessed_table: str | None = None
            if isinstance(source_node, ast.Call):
                call_name = _dotted_expression(source_node.func).rsplit(".", 1)[-1]
                if call_name in set(policy.get("table_constructors", ["Table"])):
                    if (
                        source_node.args
                        and isinstance(source_node.args[0], ast.Constant)
                        and isinstance(source_node.args[0].value, str)
                    ):
                        accessed_table = source_node.args[0].value
                    for keyword in source_node.keywords:
                        if (
                            keyword.arg == "name"
                            and isinstance(keyword.value, ast.Constant)
                            and isinstance(keyword.value.value, str)
                        ):
                            accessed_table = keyword.value.value
            elif isinstance(source_node, ast.Subscript) and _is_metadata_tables(source_node.value):
                if isinstance(source_node.slice, ast.Constant) and isinstance(
                    source_node.slice.value, str
                ):
                    accessed_table = source_node.slice.value
            if (
                accessed_table
                and accessed_table in table_owners
                and table_owners[accessed_table] != source_capability
            ):
                table_owner = table_owners[accessed_table]
                access = {
                    "source_path": relative,
                    "line": getattr(source_node, "lineno", 0),
                    "table": accessed_table,
                    "owner": table_owner,
                }
                table_accesses.append(access)
                findings.append(
                    _finding(
                        "FOREIGN_TABLE_ACCESS",
                        f"Foreign table access: {accessed_table} ({table_owner}).",
                        path=relative,
                        line=getattr(source_node, "lineno", 0),
                        source_capability=source_capability,
                        target_capability=table_owner,
                    )
                )

            if isinstance(source_node, ast.Call):
                call_name = _dotted_expression(source_node.func)
                simple_name = call_name.rsplit(".", 1)[-1]
                if simple_name in set(policy.get("orm_access_calls", [])):
                    for argument in source_node.args:
                        for reference in ast.walk(argument):
                            model_owner: str | None = None
                            symbol: str | None = None
                            if isinstance(reference, ast.Name):
                                binding = symbol_bindings.get(reference.id)
                                if binding and binding.get("capability"):
                                    model_owner = str(binding["capability"])
                                    symbol = str(binding.get("name") or "")
                                elif reference.id in symbol_owners:
                                    model_owner = symbol_owners[reference.id]
                                    symbol = reference.id
                            elif isinstance(reference, ast.Attribute) and isinstance(
                                reference.value, ast.Name
                            ):
                                binding = module_bindings.get(reference.value.id)
                                if binding and binding.get("capability"):
                                    model_owner = str(binding["capability"])
                                    symbol = reference.attr
                            if (
                                model_owner
                                and model_owner != source_capability
                                and symbol in model_symbols.get(model_owner, set())
                            ):
                                access = {
                                    "source_path": relative,
                                    "line": getattr(reference, "lineno", source_node.lineno),
                                    "model": symbol,
                                    "owner": model_owner,
                                    "call": simple_name,
                                }
                                orm_accesses.append(access)
                                findings.append(
                                    _finding(
                                        "FOREIGN_MODEL_ACCESS",
                                        f"Foreign model {symbol} used in {simple_name}.",
                                        path=relative,
                                        line=getattr(reference, "lineno", source_node.lineno),
                                        source_capability=source_capability,
                                        target_capability=model_owner,
                                        imported_name=symbol,
                                    )
                                )

            if isinstance(source_node, ast.Attribute) and source_node.attr in {
                "create_engine",
                "create_async_engine",
                "sessionmaker",
                "async_sessionmaker",
                "scoped_session",
            }:
                dotted = _dotted_expression(source_node)
                for rule in disallowed_symbols:
                    module_name = str(rule.get("module", ""))
                    if dotted.endswith("." + source_node.attr) and source_node.attr in set(
                        rule.get("names", [])
                    ):
                        root_binding = dotted.split(".", 1)[0]
                        imported = module_bindings.get(root_binding)
                        if imported and str(imported.get("module", "")).startswith(module_name):
                            findings.append(
                                _finding(
                                    "DISALLOWED_PERSISTENCE_DEPENDENCY",
                                    f"Disallowed persistence constructor: {dotted}.",
                                    path=relative,
                                    line=getattr(source_node, "lineno", 0),
                                    source_capability=source_capability,
                                    imported_module=module_name,
                                    imported_name=source_node.attr,
                                )
                            )

    unique: dict[tuple[Any, ...], dict[str, Any]] = {}
    for item in findings:
        key = (
            item["code"],
            item.get("source_path"),
            item.get("line"),
            item.get("target_capability"),
            item.get("imported_name"),
            item["message"],
        )
        unique[key] = item
    return (
        {
            "table_owners": table_owners,
            "source_model_declarations": discovered_tables,
            "model_symbols": {
                name: sorted(symbols) for name, symbols in sorted(model_symbols.items())
            },
            "table_owner_mismatches": table_mismatches,
            "foreign_table_accesses": sorted(
                table_accesses, key=lambda row: (row["source_path"], row["line"])
            ),
            "foreign_model_accesses": sorted(
                orm_accesses, key=lambda row: (row["source_path"], row["line"])
            ),
            "model_registry_exception": {
                "path": exception_path,
                "module": exception_module,
                "observed_allowed_imports": allowed_registry_imports,
            },
            "policy_findings": sorted(
                unique.values(),
                key=lambda row: (row["source_path"] or "", row["line"] or 0, row["code"]),
            ),
        },
        sorted(
            unique.values(),
            key=lambda row: (row["source_path"] or "", row["line"] or 0, row["code"]),
        ),
        errors,
    )


ANALYZERS = {
    "AC_PUBLIC_API": analyze_public_api,
    "AC_MODULE_GRAPH": analyze_module_graph,
    "AC_DATA_OWNERSHIP": analyze_data_ownership,
}
