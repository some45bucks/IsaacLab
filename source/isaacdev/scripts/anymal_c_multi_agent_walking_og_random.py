# Copyright (c) 2022-2024, The Isaac Lab Project Developers.
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

"""Script to an environment with random action agent."""

"""Launch Isaac Sim Simulator first."""

import argparse

from omni.isaac.lab.app import AppLauncher

# add argparse arguments
parser = argparse.ArgumentParser(description="Random agent for Isaac Lab environments.")
parser.add_argument(
    "--disable_fabric", action="store_true", default=False, help="Disable fabric and use USD I/O operations."
)
parser.add_argument("--num_envs", type=int, default=1, help="Number of environments to simulate.")
parser.add_argument("--num_robots", type=int, default=2, help="Number of environments to simulate.")
parser.add_argument("--task", type=str, default=None, help="Name of the task.")
# append AppLauncher cli args
AppLauncher.add_app_launcher_args(parser)
# parse the arguments
args_cli = parser.parse_args()
print(args_cli)
# launch omniverse app
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

"""Rest everything follows."""

import gymnasium as gym
import torch

import omni.isaac.lab_tasks  # noqa: F401
from omni.isaac.lab_tasks.utils import parse_env_cfg
from omni.isaac.lab.utils.assets import ISAACLAB_NUCLEUS_DIR, check_file_path, read_file


def main():
    """Random actions agent with Isaac Lab environment."""
    # create environment configuration
    env_cfg = parse_env_cfg(
        'Isaac-Velocity-Rough-Anymal-C-Direct-v0', 
        device=args_cli.device, 
        num_envs=args_cli.num_envs, 
        use_fabric=not args_cli.disable_fabric,
        num_robots=args_cli.num_robots
    )
    # create environment
    env = gym.make('Isaac-Velocity-Rough-Anymal-C-Direct-v0', cfg=env_cfg)

    # print info (this is vectorized environment)
    print(f"[INFO]: Gym observation space: {env.observation_space}")
    print(f"[INFO]: Gym action space: {env.action_space}")

    # load level policy
    policy_path = ISAACLAB_NUCLEUS_DIR + "/Policies/ANYmal-C/HeightScan/policy.pt"
    # check if policy file exists
    if not check_file_path(policy_path):
        raise FileNotFoundError(f"Policy file '{policy_path}' does not exist.")
    file_bytes = read_file(policy_path)
    # jit load the policy
    policy = torch.jit.load(file_bytes).to(env.unwrapped.device).eval()
    # reset environment
    obs, _ = env.reset()
    # simulate environment
    while simulation_app.is_running():
        # run everything in inference mode
        with torch.inference_mode():
            # sample actions from -1 to 1
            actions = policy(obs['policy'])
            # actions = 2 * torch.rand((args_cli.num_envs*args_cli.num_robots, env.action_space.shape[1]), device=env.unwrapped.device) - 1
            # apply actions
            env._commands = torch.tensor([[1, 0, 0]], device=env.device).repeat(env.num_envs, 1)
            obs, _, _, _, _ = env.step(actions)
            

    # close the simulator
    env.close()


if __name__ == "__main__":
    # run the main function
    main()
    # close sim app
    simulation_app.close()
