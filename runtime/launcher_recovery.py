#!/usr/bin/python3

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path


RECIPE_ID_PATTERN = re.compile(r"[a-z0-9][a-z0-9._-]{1,63}")
TIMESTAMP_PATTERN = re.compile(r"[0-9]{8}T[0-9]{6}Z")
MAX_RECIPE_STEPS = 8
MAX_POSTCONDITIONS = 16
MAX_SNAPSHOT_FILES = 20000
MAX_SNAPSHOT_BYTES = 2 * 1024 * 1024 * 1024
REGISTRY_FILES = frozenset(("system.reg", "user.reg", "userdef.reg"))


class LauncherRecoveryError(RuntimeError):
    def __init__(self, message, snapshot_path=""):
        self.snapshot_path = str(snapshot_path) if snapshot_path else ""
        if self.snapshot_path:
            message = f"{message}; snapshot: {self.snapshot_path}"
        super().__init__(message)


def utc_timestamp():
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def file_sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def atomic_write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.parent.chmod(0o700)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=str(path.parent)
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            json.dump(value, stream, indent=2, sort_keys=True)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        temporary.chmod(0o600)
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def require_relative_path(value, label):
    if (
        not isinstance(value, str)
        or not value
        or len(value.encode("utf-8")) > 1024
        or "\0" in value
    ):
        raise LauncherRecoveryError(f"{label} is invalid")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise LauncherRecoveryError(f"{label} must be relative")
    return path


def resolve_bounded_path(root, relative, label):
    root = Path(root).resolve()
    candidate = root / require_relative_path(relative, label)
    resolved = candidate.resolve(strict=False)
    if resolved != root and root not in resolved.parents:
        raise LauncherRecoveryError(f"{label} escapes its allowed root")
    return candidate


def normalize_snapshot_glob(value):
    path = require_relative_path(value, "snapshot glob")
    if "**" in value or any(
        character in value for character in ("[", "]", "?")
    ):
        raise LauncherRecoveryError("snapshot glob is unsupported")
    if sum(part == "*" for part in path.parts) > 1:
        raise LauncherRecoveryError("snapshot glob is too broad")
    if any("*" in part and part != "*" for part in path.parts):
        raise LauncherRecoveryError("snapshot glob is unsupported")
    return value


def normalize_recipe(context, recipe):
    if not isinstance(recipe, dict):
        raise LauncherRecoveryError("launcher recovery recipe is invalid")
    recipe_id = recipe.get("id")
    if not isinstance(recipe_id, str) or not RECIPE_ID_PATTERN.fullmatch(
        recipe_id
    ):
        raise LauncherRecoveryError("launcher recovery recipe ID is invalid")
    if recipe.get("appid") != context.get("appid"):
        raise LauncherRecoveryError(
            "launcher recovery recipe AppID does not match"
        )
    snapshot_paths = recipe.get("snapshot_paths")
    if not isinstance(snapshot_paths, list) or not snapshot_paths:
        raise LauncherRecoveryError(
            "launcher recovery snapshot paths are invalid"
        )
    normalized_snapshot_paths = []
    for value in snapshot_paths:
        path = require_relative_path(value, "snapshot path")
        resolve_bounded_path(context["prefix"], str(path), "snapshot path")
        normalized_snapshot_paths.append(str(path))

    snapshot_globs = recipe.get("snapshot_globs", [])
    if not isinstance(snapshot_globs, list):
        raise LauncherRecoveryError(
            "launcher recovery snapshot globs are invalid"
        )
    normalized_snapshot_globs = [
        normalize_snapshot_glob(value) for value in snapshot_globs
    ]

    steps = recipe.get("steps")
    if (
        not isinstance(steps, list)
        or not steps
        or len(steps) > MAX_RECIPE_STEPS
    ):
        raise LauncherRecoveryError(
            "launcher recovery steps are invalid"
        )
    normalized_steps = []
    step_ids = set()
    for raw_step in steps:
        if not isinstance(raw_step, dict):
            raise LauncherRecoveryError(
                "launcher recovery step is invalid"
            )
        step_id = raw_step.get("id")
        if (
            not isinstance(step_id, str)
            or not RECIPE_ID_PATTERN.fullmatch(step_id)
            or step_id in step_ids
        ):
            raise LauncherRecoveryError(
                "launcher recovery step ID is invalid"
            )
        step_ids.add(step_id)
        installer_value = raw_step.get("installer")
        installer = resolve_bounded_path(
            context["install_path"],
            installer_value,
            "launcher recovery installer",
        )
        size = raw_step.get("size")
        digest = raw_step.get("sha256")
        arguments = raw_step.get("arguments")
        success_codes = raw_step.get("success_codes")
        postconditions = raw_step.get("postconditions")
        if (
            not isinstance(size, int)
            or size <= 0
            or size > 512 * 1024 * 1024
            or not isinstance(digest, str)
            or not re.fullmatch(r"[0-9a-f]{64}", digest)
            or not isinstance(arguments, list)
            or len(arguments) > 32
            or not all(
                isinstance(argument, str)
                and len(argument.encode("utf-8")) <= 512
                and "\0" not in argument
                for argument in arguments
            )
            or not isinstance(success_codes, list)
            or not success_codes
            or not all(
                isinstance(code, int) and 0 <= code <= 65535
                for code in success_codes
            )
            or not isinstance(postconditions, list)
            or not postconditions
            or len(postconditions) > MAX_POSTCONDITIONS
        ):
            raise LauncherRecoveryError(
                f"launcher recovery step is invalid: {step_id}"
            )
        normalized_postconditions = []
        for postcondition in postconditions:
            if not isinstance(postcondition, dict):
                raise LauncherRecoveryError(
                    f"launcher recovery postcondition is invalid: {step_id}"
                )
            condition_type = postcondition.get("type")
            if condition_type == "pe":
                relative = require_relative_path(
                    postcondition.get("path"),
                    "launcher recovery PE path",
                )
                resolve_bounded_path(
                    context["prefix"],
                    str(relative),
                    "launcher recovery PE path",
                )
                normalized_postconditions.append(
                    {"type": "pe", "path": str(relative)}
                )
            elif condition_type == "registry_key":
                registry_file = postcondition.get("file")
                key = postcondition.get("key")
                if (
                    registry_file not in REGISTRY_FILES
                    or not isinstance(key, str)
                    or not key
                    or len(key.encode("utf-8")) > 512
                    or "\n" in key
                    or "\r" in key
                    or "[" in key
                    or "]" in key
                    or not (
                        key.startswith("Software\\")
                        or key.startswith("System\\")
                    )
                ):
                    raise LauncherRecoveryError(
                        "launcher recovery registry key is invalid"
                    )
                normalized_postconditions.append(
                    {
                        "type": "registry_key",
                        "file": registry_file,
                        "key": key,
                    }
                )
            else:
                raise LauncherRecoveryError(
                    "launcher recovery postcondition type is unsupported"
                )
        normalized_steps.append(
            {
                "id": step_id,
                "installer": str(installer),
                "size": size,
                "sha256": digest,
                "arguments": list(arguments),
                "success_codes": list(success_codes),
                "postconditions": normalized_postconditions,
            }
        )
    return {
        "id": recipe_id,
        "appid": recipe["appid"],
        "snapshot_paths": normalized_snapshot_paths,
        "snapshot_globs": normalized_snapshot_globs,
        "steps": normalized_steps,
    }


def registry_key_exists(path, key):
    try:
        if path.stat().st_size > 64 * 1024 * 1024:
            raise LauncherRecoveryError(
                f"Wine registry file is unexpectedly large: {path}"
            )
        header = f"[{key.replace(chr(92), chr(92) * 2)}]"
        with path.open("r", encoding="utf-8", errors="strict") as stream:
            for line in stream:
                stripped = line.rstrip("\r\n")
                if stripped == header or stripped.startswith(f"{header} "):
                    return True
        return False
    except (OSError, UnicodeError) as error:
        raise LauncherRecoveryError(
            f"could not inspect Wine registry file: {path}"
        ) from error


def postcondition_satisfied(context, postcondition):
    if postcondition["type"] == "pe":
        path = resolve_bounded_path(
            context["prefix"],
            postcondition["path"],
            "launcher recovery PE path",
        )
        if not path.exists():
            return False
        if not path.is_file():
            raise LauncherRecoveryError(
                f"installed target is not a file: {path}"
            )
        try:
            with path.open("rb") as stream:
                magic = stream.read(2)
        except OSError as error:
            raise LauncherRecoveryError(
                f"could not inspect installed target: {path}"
            ) from error
        if magic != b"MZ":
            raise LauncherRecoveryError(
                f"installed target is not PE: {path}"
            )
        return True
    registry_path = context["prefix"] / postcondition["file"]
    return registry_key_exists(registry_path, postcondition["key"])


def inspect_recovery_state(context, recipe):
    step_states = []
    for step in recipe["steps"]:
        conditions = [
            postcondition_satisfied(context, condition)
            for condition in step["postconditions"]
        ]
        step_states.append(
            {
                "id": step["id"],
                "complete": all(conditions),
                "postconditions": conditions,
            }
        )
    first_incomplete = next(
        (
            index
            for index, state in enumerate(step_states)
            if not state["complete"]
        ),
        None,
    )
    return {
        "state": (
            "complete" if first_incomplete is None else "recoverable"
        ),
        "first_incomplete": first_incomplete,
        "steps": step_states,
    }


def verify_installers(recipe):
    for step in recipe["steps"]:
        installer = Path(step["installer"])
        try:
            if (
                not installer.is_file()
                or installer.stat().st_size != step["size"]
                or file_sha256(installer) != step["sha256"]
            ):
                raise LauncherRecoveryError(
                    "depot prerequisite does not match its pinned manifest: "
                    f"{installer}"
                )
            with installer.open("rb") as stream:
                if stream.read(2) != b"MZ":
                    raise LauncherRecoveryError(
                        f"depot prerequisite is not PE: {installer}"
                    )
        except OSError as error:
            raise LauncherRecoveryError(
                f"could not verify depot prerequisite: {installer}"
            ) from error


def snapshot_sources(context, recipe):
    sources = []
    external_skipped = []
    seen = set()
    prefix = Path(context["prefix"])
    resolved_prefix = prefix.resolve()
    for relative in recipe["snapshot_paths"]:
        source = prefix / relative
        key = str(source)
        if key not in seen:
            seen.add(key)
            sources.append(("prefix", relative, source))
    for pattern in recipe["snapshot_globs"]:
        for source in sorted(prefix.glob(pattern)):
            try:
                resolved_source = source.resolve(strict=False)
            except OSError:
                external_skipped.append(str(source))
                continue
            if (
                resolved_source != resolved_prefix
                and resolved_prefix not in resolved_source.parents
            ):
                external_skipped.append(str(source))
                continue
            relative = str(source.relative_to(prefix))
            key = str(source)
            if key not in seen:
                seen.add(key)
                sources.append(("prefix", relative, source))
    runtime_logs = Path(context["state"]) / "logs"
    if runtime_logs.exists():
        sources.append(("state", "logs", runtime_logs))
    return sources, sorted(external_skipped)


def record_source_files(source, destination, records, limits):
    def add_file(path, copied):
        if limits["files"] >= MAX_SNAPSHOT_FILES:
            raise LauncherRecoveryError(
                "launcher recovery snapshot contains too many files"
            )
        limits["files"] += 1
        if path.is_symlink():
            records.append(
                {
                    "source": str(path),
                    "snapshot": str(copied),
                    "type": "symlink",
                    "target": os.readlink(path),
                }
            )
            return
        if not path.is_file():
            raise LauncherRecoveryError(
                f"snapshot source contains a special file: {path}"
            )
        size = path.stat().st_size
        limits["bytes"] += size
        if limits["bytes"] > MAX_SNAPSHOT_BYTES:
            raise LauncherRecoveryError(
                "launcher recovery snapshot is too large"
            )
        records.append(
            {
                "source": str(path),
                "snapshot": str(copied),
                "type": "file",
                "size": size,
                "sha256": file_sha256(path),
            }
        )

    if source.is_symlink() or source.is_file():
        add_file(source, destination)
        return
    if not source.is_dir():
        return
    for root, directories, filenames in os.walk(
        source, followlinks=False
    ):
        root_path = Path(root)
        relative_root = root_path.relative_to(source)
        copied_root = destination / relative_root
        for name in list(directories):
            path = root_path / name
            if path.is_symlink():
                add_file(path, copied_root / name)
                directories.remove(name)
        for name in filenames:
            path = root_path / name
            add_file(path, copied_root / name)


def unique_destination(root, timestamp):
    destination = root / timestamp
    suffix = 1
    while destination.exists():
        destination = root / f"{timestamp}-{suffix:02d}"
        suffix += 1
    return destination


def create_prefix_snapshot(context, recipe, timestamp=None):
    timestamp = timestamp or utc_timestamp()
    if not TIMESTAMP_PATTERN.fullmatch(timestamp):
        raise LauncherRecoveryError(
            "launcher recovery timestamp is invalid"
        )
    root = Path(context["state"]) / "recovery" / "snapshots"
    root.mkdir(parents=True, exist_ok=True)
    root.chmod(0o700)
    destination = unique_destination(root, timestamp)
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{destination.name}.", dir=str(root))
    )
    records = []
    missing = []
    limits = {"files": 0, "bytes": 0}
    try:
        sources, external_skipped = snapshot_sources(context, recipe)
        for namespace, relative, source in sources:
            copied = temporary / namespace / relative
            if not source.exists() and not source.is_symlink():
                missing.append(str(source))
                continue
            copied.parent.mkdir(parents=True, exist_ok=True)
            record_source_files(source, copied, records, limits)
            if source.is_symlink():
                copied.symlink_to(os.readlink(source))
            elif source.is_dir():
                shutil.copytree(source, copied, symlinks=True)
            else:
                shutil.copy2(source, copied, follow_symlinks=False)
        for record in records:
            copied = Path(record["snapshot"])
            record["snapshot"] = str(
                destination / copied.relative_to(temporary)
            )
        atomic_write_json(
            temporary / "manifest.json",
            {
                "schema": 1,
                "appid": context["appid"],
                "recipe": recipe["id"],
                "created_at": timestamp,
                "prefix": str(context["prefix"]),
                "install_path": str(context["install_path"]),
                "files": records,
                "missing": sorted(missing),
                "external_skipped": external_skipped,
                "total_files": limits["files"],
                "total_bytes": limits["bytes"],
            },
        )
        temporary.chmod(0o700)
        os.replace(temporary, destination)
        return destination
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def plan_launcher_recovery(context, raw_recipe, timestamp=None):
    recipe = normalize_recipe(context, raw_recipe)
    try:
        state = inspect_recovery_state(context, recipe)
    except LauncherRecoveryError as error:
        snapshot = create_prefix_snapshot(
            context, recipe, timestamp=timestamp
        )
        raise LauncherRecoveryError(
            str(error), snapshot_path=snapshot
        ) from error
    preserve = [str(context["install_path"]), str(context["prefix"])]
    if state["state"] == "complete":
        return {
            "schema": 1,
            "appid": context["appid"],
            "recipe": recipe["id"],
            "state": "complete",
            "snapshot_path": "",
            "preserve": preserve,
            "steps": [],
            "inspection": state,
        }
    snapshot = create_prefix_snapshot(
        context, recipe, timestamp=timestamp
    )
    try:
        verify_installers(recipe)
    except LauncherRecoveryError as error:
        raise LauncherRecoveryError(
            str(error), snapshot_path=snapshot
        ) from error
    first_incomplete = state["first_incomplete"]
    return {
        "schema": 1,
        "appid": context["appid"],
        "recipe": recipe["id"],
        "state": "recoverable",
        "snapshot_path": str(snapshot),
        "preserve": preserve,
        "steps": recipe["steps"][first_incomplete:],
        "inspection": state,
    }


def wait_for_step(context, step, timeout):
    deadline = time.monotonic() + max(0, timeout)
    while True:
        if all(
            postcondition_satisfied(context, condition)
            for condition in step["postconditions"]
        ):
            return True
        if time.monotonic() >= deadline:
            return False
        time.sleep(0.25)


def report_path(context, timestamp):
    root = Path(context["state"]) / "recovery" / "reports"
    root.mkdir(parents=True, exist_ok=True)
    root.chmod(0o700)
    return unique_destination(root, f"{timestamp}.json")


def execute_launcher_recovery(
    context,
    recipe,
    wine64,
    environment,
    *,
    runner=subprocess.run,
    timestamp=None,
    postcondition_timeout=30,
):
    timestamp = timestamp or utc_timestamp()
    plan = plan_launcher_recovery(
        context, recipe, timestamp=timestamp
    )
    if plan["state"] == "complete":
        return {
            "state": "complete",
            "snapshot_path": "",
            "report_path": "",
            "steps": [],
        }

    report = {
        "schema": 1,
        "appid": context["appid"],
        "recipe": plan["recipe"],
        "state": "running",
        "started_at": timestamp,
        "snapshot_path": plan["snapshot_path"],
        "preserve": plan["preserve"],
        "steps": [],
    }
    destination = report_path(context, timestamp)
    atomic_write_json(destination, report)
    log_root = Path(context["state"]) / "recovery" / "logs"
    log_root.mkdir(parents=True, exist_ok=True)
    log_root.chmod(0o700)
    log_path = log_root / f"{destination.stem}.log"
    descriptor = os.open(
        log_path,
        os.O_WRONLY | os.O_CREAT | os.O_APPEND,
        0o600,
    )
    try:
        with os.fdopen(descriptor, "a", encoding="utf-8") as stream:
            descriptor = -1
            for step in plan["steps"]:
                command = [
                    str(wine64),
                    step["installer"],
                    *step["arguments"],
                ]
                stream.write(
                    f"\n[{utc_timestamp()}] install {step['id']}\n"
                )
                stream.write(
                    "$ "
                    + " ".join(json.dumps(part) for part in command)
                    + "\n"
                )
                stream.flush()
                try:
                    result = runner(
                        command,
                        cwd=str(context["install_path"]),
                        env=dict(environment),
                        stdout=stream,
                        stderr=subprocess.STDOUT,
                        check=False,
                    )
                except OSError as error:
                    report["state"] = "failed"
                    report["message"] = (
                        f"could not run launcher prerequisite: {step['id']}"
                    )
                    atomic_write_json(destination, report)
                    raise LauncherRecoveryError(
                        report["message"],
                        snapshot_path=plan["snapshot_path"],
                    ) from error
                step_report = {
                    "id": step["id"],
                    "command": command,
                    "exit_code": result.returncode,
                }
                report["steps"].append(step_report)
                atomic_write_json(destination, report)
                if result.returncode not in step["success_codes"]:
                    report["state"] = "failed"
                    report["message"] = (
                        "launcher prerequisite failed with exit code "
                        f"{result.returncode}: {step['id']}"
                    )
                    atomic_write_json(destination, report)
                    raise LauncherRecoveryError(
                        report["message"],
                        snapshot_path=plan["snapshot_path"],
                    )
                if not wait_for_step(
                    context, step, postcondition_timeout
                ):
                    report["state"] = "failed"
                    report["message"] = (
                        "launcher prerequisite did not satisfy its "
                        f"postconditions: {step['id']}"
                    )
                    atomic_write_json(destination, report)
                    raise LauncherRecoveryError(
                        report["message"],
                        snapshot_path=plan["snapshot_path"],
                    )
    finally:
        if descriptor >= 0:
            os.close(descriptor)

    normalized = normalize_recipe(context, recipe)
    final_state = inspect_recovery_state(context, normalized)
    if final_state["state"] != "complete":
        report["state"] = "failed"
        report["message"] = (
            "launcher recovery ended in an incomplete state"
        )
        atomic_write_json(destination, report)
        raise LauncherRecoveryError(
            report["message"], snapshot_path=plan["snapshot_path"]
        )
    report["state"] = "recovered"
    report["finished_at"] = utc_timestamp()
    report["inspection_after"] = final_state
    report["log_path"] = str(log_path)
    atomic_write_json(destination, report)
    return {
        "state": "recovered",
        "snapshot_path": plan["snapshot_path"],
        "report_path": str(destination),
        "steps": report["steps"],
    }


def load_launcher_recovery_catalog(path):
    catalog_path = Path(path).expanduser()
    try:
        value = json.loads(catalog_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise LauncherRecoveryError(
            f"launcher recovery catalog is invalid: {catalog_path}"
        ) from error
    entries = value.get("launcher_recoveries", [])
    if value.get("schema") != 1 or not isinstance(entries, list):
        raise LauncherRecoveryError(
            f"launcher recovery catalog is invalid: {catalog_path}"
        )
    result = {}
    for entry in entries:
        if not isinstance(entry, dict):
            raise LauncherRecoveryError(
                f"launcher recovery catalog is invalid: {catalog_path}"
            )
        appid = entry.get("appid")
        if (
            not isinstance(appid, int)
            or appid <= 0
            or appid in result
        ):
            raise LauncherRecoveryError(
                f"launcher recovery catalog AppID is invalid: {appid}"
            )
        result[appid] = entry
    return result
