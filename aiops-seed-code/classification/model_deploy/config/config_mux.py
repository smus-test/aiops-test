# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: MIT-0

"""Configuration multiplexer for stage-specific config loading."""

from pathlib import Path
from dataclasses import dataclass
from aws_cdk import Stack, Stage
import constructs
from yamldataclassconfig.config import YamlDataClassConfig
from abc import ABCMeta


DEFAULT_STAGE_NAME = "dev"
DEFAULT_STACK_NAME = "dev"


def get_config_for_stage(scope: constructs, path: str):
    """Get config file path for the current stage."""
    default_path = Path(__file__).parent.joinpath(DEFAULT_STAGE_NAME, path)
    if stage_name := Stage.of(scope).stage_name:
        config_path = Path(__file__).parent.joinpath(stage_name.lower(), path)
        if not config_path.exists():
            print(f"Config file {path} for stage {stage_name} not found. Using {default_path}")
            config_path = default_path
        return config_path
    else:
        print(f"Stack created without a stage. Using {default_path}")
        return default_path


def get_config_for_stack(scope: constructs, path: str):
    """Get config file path for the current stack."""
    default_path = Path(__file__).parent.joinpath(DEFAULT_STACK_NAME, path)
    if stack_name := Stack.of(scope).stack_name:
        config_path = Path(__file__).parent.joinpath(stack_name.lower(), path)
        if not config_path.exists():
            print(f"Config file {path} for stack {stack_name} not found. Using {default_path}")
            config_path = default_path
        return config_path
    else:
        print(f"Stack created without a stack. Using {default_path}")
        return default_path


@dataclass
class StageYamlDataClassConfig(YamlDataClassConfig, metaclass=ABCMeta):
    """YAML config loader with stage-specific config loading capabilities."""

    def load(self):
        """Load config from default dev path."""
        path = Path(__file__).parent().joinpath("config/", "dev", self.FILE_PATH)
        return super().load(path=path)

    def load_for_stage(self, scope):
        """Load config for the current stage."""
        path = get_config_for_stage(scope, self.FILE_PATH)
        return super().load(path=path)

    def load_for_stack(self, scope):
        """Load config for the current stack."""
        path = get_config_for_stack(scope, self.FILE_PATH)
        return super().load(path=path)
