"""Prompt and field configuration loading utilities.

Handles loading field definitions and prompt configs from YAML files,
with config fallback from {case_type}/ to generic/.
"""

import hashlib
import os
from typing import Optional

import yaml
from tinystructlog import get_logger

import mydocs.config as C
from mydocs.extracting.exceptions import ConfigNotFoundError, FieldConsistencyError
from mydocs.extracting.models import (
    FieldDefinition,
    PromptConfig,
)

log = get_logger(__name__)

EXTRACTING_CONFIG_ROOT = os.path.join(C.CONFIG_ROOT, "extracting")


# ---------------------------------------------------------------------------
# YAML helpers
# ---------------------------------------------------------------------------

def load_yaml_file(path: str) -> dict | list:
    """Load a YAML file and return parsed content."""
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}


def load_manifest_file(manifest_path: str) -> dict:
    """Load a manifest YAML that tracks content hashes."""
    if not os.path.exists(manifest_path):
        return {}
    return load_yaml_file(manifest_path)


def save_manifest_file(manifest_path: str, manifest: dict) -> None:
    """Save a manifest YAML."""
    os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
    with open(manifest_path, "w") as f:
        yaml.dump(manifest, f, default_flow_style=False, sort_keys=True)


def calculate_content_hash(content: str) -> str:
    """Calculate SHA-256 hash of content string."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# Config path resolution
# ---------------------------------------------------------------------------

def _get_config_dir(case_type: str, document_type: str) -> str:
    """Resolve config directory with fallback to generic/.

    Tries config/extracting/{case_type}/{document_type}/ first,
    then falls back to config/extracting/generic/{document_type}/.
    """
    primary = os.path.join(EXTRACTING_CONFIG_ROOT, case_type, document_type)
    if os.path.isdir(primary):
        return primary

    if case_type != "generic":
        fallback = os.path.join(EXTRACTING_CONFIG_ROOT, "generic", document_type)
        if os.path.isdir(fallback):
            log.info(
                f"Config not found for {case_type}/{document_type}, "
                f"falling back to generic/{document_type}"
            )
            return fallback

    return primary  # Return primary path even if missing — caller handles errors


def get_local_configs(
    case_type: str,
    document_type: str,
    sub_folder: str,
) -> str:
    """Return path to a sub-folder within the config directory."""
    config_dir = _get_config_dir(case_type, document_type)
    return os.path.join(config_dir, sub_folder)


def generate_config_id(case_type: str, document_type: str, name: str) -> str:
    """Generate a deterministic config ID from case_type, document_type, and name."""
    return f"{case_type}_{document_type}_{name}"


def get_split_classify_prompt(case_type: str, prompt_name: str = "main") -> PromptConfig:
    """Load the split-classify prompt for a case type.

    Looks in config/extracting/{case_type}/split_classify/prompts/{prompt_name}.yaml.
    Falls back to the generic case_type's split_classify prompt if not found.
    """
    primary = os.path.join(
        EXTRACTING_CONFIG_ROOT, case_type, "split_classify", "prompts", f"{prompt_name}.yaml"
    )
    if os.path.isfile(primary):
        data = load_yaml_file(primary)
        if isinstance(data, dict):
            return PromptConfig(**data)

    if case_type != "generic":
        fallback = os.path.join(
            EXTRACTING_CONFIG_ROOT, "generic", "split_classify", "prompts", f"{prompt_name}.yaml"
        )
        if os.path.isfile(fallback):
            log.info(
                f"Split-classify prompt not found for {case_type}, "
                f"falling back to generic"
            )
            data = load_yaml_file(fallback)
            if isinstance(data, dict):
                return PromptConfig(**data)

    raise ConfigNotFoundError(
        f"Split-classify prompt '{prompt_name}' not found for case_type '{case_type}'"
    )


# ---------------------------------------------------------------------------
# Field loading
# ---------------------------------------------------------------------------

def get_all_fields(
    case_type: str,
    document_type: str,
) -> list[FieldDefinition]:
    """Load all field definitions for a case_type/document_type pair.

    Reads all YAML files from config/extracting/{case_type}/{document_type}/fields/.
    Each YAML file contains a list of FieldDefinition dicts.
    """
    fields_dir = get_local_configs(case_type, document_type, "fields")
    if not os.path.isdir(fields_dir):
        log.debug(f"No fields directory found at {fields_dir}")
        return []

    all_fields: list[FieldDefinition] = []
    for filename in sorted(os.listdir(fields_dir)):
        if not filename.endswith((".yaml", ".yml")):
            continue
        filepath = os.path.join(fields_dir, filename)
        data = load_yaml_file(filepath)
        if isinstance(data, list):
            for item in data:
                all_fields.append(FieldDefinition(**item))
        elif isinstance(data, dict) and "fields" in data:
            for item in data["fields"]:
                all_fields.append(FieldDefinition(**item))

    log.info(f"Loaded {len(all_fields)} fields for {case_type}/{document_type}")
    return all_fields


def get_field_groups(
    case_type: str,
    document_type: str,
) -> dict[int, list[FieldDefinition]]:
    """Load fields and organize them by group number."""
    fields = get_all_fields(case_type, document_type)
    groups: dict[int, list[FieldDefinition]] = {}
    for field in fields:
        groups.setdefault(field.group, []).append(field)
    return groups


# ---------------------------------------------------------------------------
# Prompt loading
# ---------------------------------------------------------------------------

def get_prompt(
    case_type: str,
    document_type: str,
    group: Optional[int] = None,
) -> PromptConfig:
    """Load the prompt config for a case_type/document_type/group.

    Resolution order:
    1. Group-specific prompt (where groups contains the group number)
    2. Default prompt (main.yaml, where groups is None or [0])
    3. Raise ConfigNotFoundError
    """
    prompts_dir = get_local_configs(case_type, document_type, "prompts")
    if not os.path.isdir(prompts_dir):
        raise ConfigNotFoundError(
            f"Prompts directory not found: {prompts_dir}"
        )

    # Load all prompt files
    prompt_configs: list[PromptConfig] = []
    for filename in sorted(os.listdir(prompts_dir)):
        if not filename.endswith((".yaml", ".yml")):
            continue
        filepath = os.path.join(prompts_dir, filename)
        data = load_yaml_file(filepath)
        if isinstance(data, dict):
            prompt_configs.append(PromptConfig(**data))

    if not prompt_configs:
        raise ConfigNotFoundError(
            f"No prompt configs found in {prompts_dir}"
        )

    # Try group-specific match
    if group is not None:
        for pc in prompt_configs:
            if pc.groups and group in pc.groups:
                return pc

    # Fall back to default (groups is None or contains 0)
    for pc in prompt_configs:
        if pc.groups is None or pc.groups == [0]:
            return pc

    # If only one prompt exists, use it
    if len(prompt_configs) == 1:
        return prompt_configs[0]

    raise ConfigNotFoundError(
        f"No matching prompt config for group={group} in {prompts_dir}"
    )


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_prompt_consistency(prompt_config: PromptConfig) -> bool:
    """Validate that a prompt config has all required template placeholders."""
    required_user = ["{fields}", "{context}"]
    for placeholder in required_user:
        if placeholder not in prompt_config.user_prompt_template:
            log.warning(
                f"Prompt '{prompt_config.name}' missing '{placeholder}' "
                f"in user_prompt_template"
            )
            return False
    return True


def validate_field_consistency(
    fields: list[FieldDefinition],
    prompt_config: PromptConfig,
) -> None:
    """Validate that field definitions are consistent with prompt config.

    Raises FieldConsistencyError if fields reference non-existent dependencies.
    """
    field_names = {f.name for f in fields}
    for field in fields:
        if not field.inputs:
            continue
        for req in field.inputs:
            if req.field_name not in field_names and req.document_type is None:
                raise FieldConsistencyError(
                    f"Field '{field.name}' requires '{req.field_name}' "
                    f"which is not defined in the current field set"
                )
