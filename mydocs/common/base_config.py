import hashlib
import json
import os
from typing import Any, Dict, Literal, Optional

import yaml
from pydantic import BaseModel
from tinystructlog import get_logger

import mydocs.config as C

log = get_logger(__name__)


class SerializedConfig(BaseModel):
    config_dict: Dict[str, Any]
    config_yaml: Optional[str] = None
    config_json: Optional[str] = None
    config_hash: str


class BaseConfig(BaseModel):
    config_name: str
    config_root: str = C.CONFIG_ROOT

    def __init__(self, **kwargs):
        is_internal_load = kwargs.pop('_is_internal_load', False)
        super().__init__(**kwargs)

        if not is_internal_load:
            updated_instance = self.apply_yaml_config(self.config_name, self.config_root)
            self.__dict__.update(updated_instance.__dict__)

    def apply_config(self, other_config: 'BaseConfig') -> 'BaseConfig':
        """Apply configuration updates from another BaseConfig instance with recursive merging."""
        if other_config is None:
            return self

        update_data = other_config.model_dump(exclude_unset=True)
        new_config_data = self.model_dump()

        def recursive_update(original, updates):
            for key, value in updates.items():
                if key in original and isinstance(original.get(key), dict) and isinstance(value, dict):
                    recursive_update(original[key], value)
                else:
                    original[key] = value
            return original

        merged_data = recursive_update(new_config_data, update_data)
        return self.__class__(**merged_data, _is_internal_load=True)

    def apply_yaml_config(self, config_name: str, config_root: str = None) -> 'BaseConfig':
        """Load and apply YAML configuration on top of current config."""
        if config_root is None:
            config_root = self.config_root

        config_path = os.path.join(config_root, f"{config_name}.yml")

        if not os.path.exists(config_path):
            log.debug(f"Configuration file not found at: {config_path}. Using existing configuration.")
            return self

        try:
            with open(config_path, 'r') as f:
                yaml_data = yaml.safe_load(f) or {}

            temp_config = self.__class__(**yaml_data, _is_internal_load=True)
            updated_config = self.apply_config(temp_config)
            log.info(f"Successfully loaded and applied configuration from: {config_path}")
            return updated_config

        except yaml.YAMLError as e:
            log.error(f"Error parsing YAML file {config_path}: {e}")
            log.warning("Using existing configuration values due to YAML parsing error.")
            return self

        except Exception as e:
            log.error(f"Error loading configuration from {config_path}: {e}")
            log.warning("Using existing configuration values due to loading error.")
            return self

    def dump_config(self, format: Literal["yaml", "json"] = "yaml") -> SerializedConfig:
        """Dump configuration to YAML or JSON with deterministic output and SHA256 hash."""
        config_data = self.model_dump(exclude_none=True)

        config_yaml = None
        config_json = None

        if format == "yaml":
            serialized_str = yaml.dump(
                config_data, default_flow_style=False,
                allow_unicode=True, sort_keys=True, indent=2
            )
            config_yaml = serialized_str
        elif format == "json":
            serialized_str = json.dumps(
                config_data, indent=2, sort_keys=True,
                ensure_ascii=False, separators=(',', ': ')
            )
            config_json = serialized_str
        else:
            raise ValueError(f"Unsupported format: {format}. Use 'yaml' or 'json'")

        config_hash = hashlib.sha256(serialized_str.encode('utf-8')).hexdigest()

        return SerializedConfig(
            config_dict=config_data,
            config_yaml=config_yaml,
            config_json=config_json,
            config_hash=config_hash,
        )
