# Copyright (c) 2022-2024, The Isaac Lab Project Developers.
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""
Ant locomotion environment.
"""

import gymnasium as gym

from . import agents
from .h1_anymal_env import HeterogeneousMultiAgent, HeterogeneousMultiAgentFlatEnvCfg, HeterogeneousMultiAgentRoughEnvCfg
from .h1_anymal_push_env import HeterogeneousPushMultiAgent, HeterogeneousPushMultiAgentFlatEnvCfg, HeterogeneousPushMultiAgentRoughEnvCfg

##
# Register Gym environments.
##

gym.register(
    id="Isaac-Anymal-H1-Surf-Flat-Direct-v0",
    entry_point="omni.isaac.lab_tasks.direct.h1_anymal_env:HeterogeneousMultiAgent",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": HeterogeneousMultiAgentFlatEnvCfg,
        "rl_games_cfg_entry_point": f"{agents.__name__}:rl_games_flat_ppo_cfg.yaml",
        "rsl_rl_cfg_entry_point": f"{agents.__name__}.rsl_rl_ppo_cfg:AnymalCFlatPPORunnerCfg",
        "skrl_cfg_entry_point": f"{agents.__name__}:skrl_flat_ppo_cfg.yaml",
        "harl_ppo_cfg_entry_point": f"{agents.__name__}:harl_ppo_cfg.yaml",
    },
)

gym.register(
    id="Isaac-Anymal-H1-Push-Direct-v0",
    entry_point="omni.isaac.lab_tasks.direct.h1_anymal_env:HeterogeneousPushMultiAgent",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": HeterogeneousPushMultiAgentFlatEnvCfg,
        "rl_games_cfg_entry_point": f"{agents.__name__}:rl_games_flat_ppo_cfg.yaml",
        "rsl_rl_cfg_entry_point": f"{agents.__name__}.rsl_rl_ppo_cfg:AnymalCFlatPPORunnerCfg",
        "skrl_cfg_entry_point": f"{agents.__name__}:skrl_flat_ppo_cfg.yaml",
        "harl_ppo_cfg_entry_point": f"{agents.__name__}:harl_ppo_cfg.yaml",
    },
)

gym.register(
    id="Isaac-Anymal-H1-Surf-Rough-Direct-v0",
    entry_point="omni.isaac.lab_tasks.direct.multi_agent_heterogeneous:HeterogeneousMultiAgent",
    disable_env_checker=True,
    kwargs={
        "env_cfg_entry_point": HeterogeneousMultiAgentRoughEnvCfg,
        "rl_games_cfg_entry_point": f"{agents.__name__}:rl_games_rough_ppo_cfg.yaml",
        "rsl_rl_cfg_entry_point": f"{agents.__name__}.rsl_rl_ppo_cfg:AnymalCRoughPPORunnerCfg",
        "skrl_cfg_entry_point": f"{agents.__name__}:skrl_rough_ppo_cfg.yaml",
    },
)
