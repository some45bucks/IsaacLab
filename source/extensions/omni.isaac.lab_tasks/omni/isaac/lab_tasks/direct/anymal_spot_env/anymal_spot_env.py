# Copyright (c) 2022-2024, The Isaac Lab Project Developers.
# All rights reserved.
#
# SPDX-License-Identifier: BSD-3-Clause

from __future__ import annotations

import gymnasium as gym
import torch

import omni.isaac.lab.envs.mdp as mdp
import omni.isaac.lab.sim as sim_utils
from omni.isaac.lab.assets import Articulation, ArticulationCfg, AssetBase, AssetBaseCfg, RigidObject, RigidObjectCfg
from omni.isaac.lab.envs import DirectRLEnv, DirectRLEnvCfg, DirectMARLEnv, DirectMARLEnvCfg
from omni.isaac.lab.managers import EventTermCfg as EventTerm
from omni.isaac.lab.managers import SceneEntityCfg
from omni.isaac.lab.scene import InteractiveSceneCfg
from omni.isaac.lab.sensors import ContactSensor, ContactSensorCfg, RayCaster, RayCasterCfg, patterns
from omni.isaac.lab.sim import SimulationCfg
from omni.isaac.lab.terrains import TerrainImporterCfg
from omni.isaac.lab.utils import configclass
from omni.isaac.lab.utils.assets import ISAAC_NUCLEUS_DIR
import copy
from omni.isaac.core.utils.torch.rotations import compute_heading_and_up, compute_rot, quat_conjugate
import omni.isaac.core.utils.torch as torch_utils
##
# Pre-defined configs
##
from omni.isaac.lab_assets.anymal import ANYMAL_C_CFG  # isort: skip
from omni.isaac.lab_assets.spot import SPOT_CFG  # isort: skip
from omni.isaac.lab.terrains.config.rough import ROUGH_TERRAINS_CFG  # isort: skip


def normalize_angle(x):
    return torch.atan2(torch.sin(x), torch.cos(x))

@configclass
class EventCfg:
    """Configuration for randomization."""

    physics_material_0 = EventTerm(
        func=mdp.randomize_rigid_body_material,
        mode="startup",
        params={
            "asset_cfg": SceneEntityCfg("robot_0", body_names=".*"),
            "static_friction_range": (0.8, 0.8),
            "dynamic_friction_range": (0.6, 0.6),
            "restitution_range": (0.0, 0.0),
            "num_buckets": 64,
        },
    )

    physics_material_1 = EventTerm(
        func=mdp.randomize_rigid_body_material,
        mode="startup",
        params={
            "asset_cfg": SceneEntityCfg("robot_1", body_names=".*"),
            "static_friction_range": (0.8, 0.8),
            "dynamic_friction_range": (0.6, 0.6),
            "restitution_range": (0.0, 0.0),
            "num_buckets": 64,
        },
    )

    add_base_mass_0 = EventTerm(
        func=mdp.randomize_rigid_body_mass,
        mode="startup",
        params={
            "asset_cfg": SceneEntityCfg("robot_0", body_names="base"),
            "mass_distribution_params": (-5.0, 5.0),
            "operation": "add",
        },
    )

    add_base_mass_1 = EventTerm(
        func=mdp.randomize_rigid_body_mass,
        mode="startup",
        params={
            "asset_cfg": SceneEntityCfg("robot_1", body_names="body"),
            "mass_distribution_params": (-5.0, 5.0),
            "operation": "add",
        },
    )


@configclass
class HeterogeneousMultiAgentFlatEnvCfg(DirectMARLEnvCfg):
    # env
    episode_length_s = 20.0
    decimation = 4
    action_scale = 0.5
    action_spaces = {}
    observation_spaces = {}
    state_space = 0
    state_spaces = {}
    possible_agents = []

    # simulation
    sim: SimulationCfg = SimulationCfg(
        dt=1 / 200,
        render_interval=decimation,
        disable_contact_processing=True,
        physics_material=sim_utils.RigidBodyMaterialCfg(
            friction_combine_mode="multiply",
            restitution_combine_mode="multiply",
            static_friction=1.0,
            dynamic_friction=1.0,
            restitution=0.0,
        ),
    )
    terrain = TerrainImporterCfg(
        prim_path="/World/ground",
        terrain_type="plane",
        collision_group=-1,
        physics_material=sim_utils.RigidBodyMaterialCfg(
            friction_combine_mode="multiply",
            restitution_combine_mode="multiply",
            static_friction=1.0,
            dynamic_friction=1.0,
            restitution=0.0,
        ),
        debug_vis=False,
    )

    # scene
    scene: InteractiveSceneCfg = InteractiveSceneCfg(num_envs=1, env_spacing=6.0, replicate_physics=True)

    # events
    events: EventCfg = EventCfg()

    ########### ROBOT_0 ANYMAL ###########

    robot_0: ArticulationCfg = ANYMAL_C_CFG.replace(prim_path="/World/envs/env_.*/Robot_0")
    contact_sensor_0: ContactSensorCfg = ContactSensorCfg(
        prim_path="/World/envs/env_.*/Robot_0/.*", history_length=3, update_period=0.005, track_air_time=True
    )
    robot_0.init_state.rot = (1.0, 0.0, 0.0, 1)
    robot_0.init_state.pos = (-1.0, 0.0, .5)

    action_spaces['robot_0'] = 12
    observation_spaces['robot_0'] = 48
    state_spaces['robot_0'] = 0
    possible_agents.append('robot_0')

    ########### ROBOT_0 ANYMAL ###########

    ########### ROBOT_1 SPOT ###########

    robot_1: ArticulationCfg = SPOT_CFG.replace(prim_path="/World/envs/env_.*/Robot_1")
    contact_sensor_1: ContactSensorCfg = ContactSensorCfg(
        prim_path="/World/envs/env_.*/Robot_1/.*", history_length=3, update_period=0.005, track_air_time=True
    )
    robot_1.init_state.rot = (1.0, 0.0, 0.0, 1)
    robot_1.init_state.pos = (1.0, 0.0, .6)

    height_scanner_1 = RayCasterCfg(
        prim_path="/World/envs/env_.*/Robot_1/body",
        offset=RayCasterCfg.OffsetCfg(pos=(0.0, 0.0, 20.0)),
        attach_yaw_only=True,
        pattern_cfg=patterns.GridPatternCfg(resolution=0.1, size=[1.6, 1.0]),
        debug_vis=True,
        mesh_prim_paths=["/World/ground"],
    )

    action_spaces['robot_1'] = 12
    observation_spaces['robot_1'] = 235
    state_spaces['robot_1'] = 0
    possible_agents.append('robot_1')

    ########### ROBOT_1 SPOT ###########


    # rec prism
    cfg_rec_prism= RigidObjectCfg(
        prim_path="/World/envs/env_.*/Object",
        spawn=sim_utils.CuboidCfg( 
            size=(5,.1,.1),
            rigid_props=sim_utils.RigidBodyPropertiesCfg(),
            mass_props=sim_utils.MassPropertiesCfg(mass=1.0),
            collision_props=sim_utils.CollisionPropertiesCfg(),
            visual_material=sim_utils.PreviewSurfaceCfg(diffuse_color=(0.0, 1.0, 0.0))
        ),
        init_state=RigidObjectCfg.InitialStateCfg(pos=(0.0, 0, 1.5), rot=(1.0, 0.0, 0.0, 0.0)),
    )

    # we add a height scanner for perceptive locomotion




    # reward scales (override from flat config)
    flat_orientation_reward_scale = 0.0

    # reward scales
    lin_vel_reward_scale = 1.0
    yaw_rate_reward_scale = 0.5
    z_vel_reward_scale = -2.0
    ang_vel_reward_scale = -0.05
    joint_torque_reward_scale = -2.5e-5
    joint_accel_reward_scale = -2.5e-7
    action_rate_reward_scale = -0.01
    feet_air_time_reward_scale = 0.5
    undersired_contact_reward_scale = -1.0
    flat_orientation_reward_scale = -5.0
    flat_bar_roll_angle_reward_scale = -10



@configclass
class HeterogeneousMultiAgentRoughEnvCfg(HeterogeneousMultiAgentFlatEnvCfg):
    # env
    observation_space = 235

    terrain = TerrainImporterCfg(
        prim_path="/World/ground",
        terrain_type="generator",
        terrain_generator=ROUGH_TERRAINS_CFG,
        max_init_terrain_level=9,
        collision_group=-1,
        physics_material=sim_utils.RigidBodyMaterialCfg(
            friction_combine_mode="multiply",
            restitution_combine_mode="multiply",
            static_friction=1.0,
            dynamic_friction=1.0,
        ),
        visual_material=sim_utils.MdlFileCfg(
            mdl_path="{NVIDIA_NUCLEUS_DIR}/Materials/Base/Architecture/Shingles_01.mdl",
            project_uvw=True,
        ),
        debug_vis=False,
    )

    # we add a height scanner for perceptive locomotion
    height_scanner_0 = RayCasterCfg(
        prim_path="/World/envs/env_.*/Robot_0/base",
        offset=RayCasterCfg.OffsetCfg(pos=(0.0, 0.0, 20.0)),
        attach_yaw_only=True,
        pattern_cfg=patterns.GridPatternCfg(resolution=0.1, size=[1.6, 1.0]),
        debug_vis=False,
        mesh_prim_paths=["/World/ground"],
    )

    height_scanner_1 = RayCasterCfg(
        prim_path="/World/envs/env_.*/Robot_1/body",
        offset=RayCasterCfg.OffsetCfg(pos=(0.0, 0.0, 20.0)),
        attach_yaw_only=True,
        pattern_cfg=patterns.GridPatternCfg(resolution=0.1, size=[1.6, 1.0]),
        debug_vis=False,
        mesh_prim_paths=["/World/ground"],
    )

    # reward scales (override from flat config)
    flat_orientation_reward_scale = 0.0


class HeterogeneousMultiAgent(DirectMARLEnv):
    cfg: HeterogeneousMultiAgentFlatEnvCfg | HeterogeneousMultiAgentRoughEnvCfg

    def __init__(self, cfg: HeterogeneousMultiAgentFlatEnvCfg | HeterogeneousMultiAgentRoughEnvCfg, render_mode: str | None = None, **kwargs):
        super().__init__(cfg, render_mode, **kwargs)
        # Joint position command (deviation from default joint positions)
        self.cfg.action_spaces = {robot_id:robot.data.default_joint_pos.shape[1] for robot_id, robot in self.robots.items()}
        self.actions = {agent : torch.zeros(self.num_envs, action_space, device=self.device) for agent, action_space in self.cfg.action_spaces.items()}
        self.previous_actions = {agent : torch.zeros(self.num_envs, action_space, device=self.device) for agent, action_space in self.cfg.action_spaces.items()}

        # X/Y linear velocity and yaw angular velocity commands
        self._commands = {agent : torch.zeros(self.num_envs, 3, device=self.device) for agent in self.cfg.possible_agents}

        # Logging
        self._episode_sums = {
            key: torch.zeros(self.num_envs, dtype=torch.float, device=self.device)
            for key in [
                "track_lin_vel_xy_exp",
                "track_ang_vel_z_exp",
                "lin_vel_z_l2",
                "ang_vel_xy_l2",
                "dof_torques_l2",
                "dof_acc_l2",
                "action_rate_l2",
                "feet_air_time",
                "undesired_contacts",
                "flat_orientation_l2",
                "flat_bar_roll_angle"
            ]
        }

        self.base_ids = {}
        self.feet_ids = {}
        self.undesired_body_contact_ids = {}


        robot_id = "robot_0"
        contact_sensor = self.contact_sensors[robot_id]
        _base_id, _ = contact_sensor.find_bodies("base")
        _feet_ids, _ = contact_sensor.find_bodies(".*FOOT")
        _undesired_contact_body_ids, _ = contact_sensor.find_bodies(".*THIGH")
        self.base_ids[robot_id] = _base_id
        self.feet_ids[robot_id] = _feet_ids
        self.undesired_body_contact_ids[robot_id] = _undesired_contact_body_ids  

        robot_id = "robot_1"
        contact_sensor = self.contact_sensors[robot_id]
        _base_id, _ = contact_sensor.find_bodies("body")
        _feet_ids, _ = contact_sensor.find_bodies(".*foot")
        _undesired_contact_body_ids, _ = contact_sensor.find_bodies(".*hip")
        self.base_ids[robot_id] = _base_id
        self.feet_ids[robot_id] = _feet_ids
        self.undesired_body_contact_ids[robot_id] = _undesired_contact_body_ids    

        self.targets = torch.tensor([1000, 0, 0], dtype=torch.float32, device=self.sim.device).repeat(
            (self.num_envs, 1)
        )
        self.targets += self.scene.env_origins

        self.start_rotation = torch.tensor([1, 0, 0, 0], device=self.sim.device, dtype=torch.float32)
        self.inv_start_rot = quat_conjugate(self.start_rotation).repeat((self.num_envs, 1))
        self.basis_vec0 = self.heading_vec.clone()
        self.basis_vec1 = self.up_vec.clone()

    def _setup_scene(self):
        self.num_robots = sum(1 for key in self.cfg.__dict__.keys() if "robot_" in key)
        self.robots = {}
        self.contact_sensors = {}
        self.height_scanners = {}
        self.object = RigidObject(self.cfg.cfg_rec_prism)
        
        self.scene.rigid_objects["object"] = self.object

        for i in range(self.num_robots):
            self.robots[f"robot_{i}"] = (Articulation(self.cfg.__dict__["robot_" + str(i)]))
            self.scene.articulations[f"robot_{i}"] = self.robots[f"robot_{i}"]
            self.contact_sensors[f"robot_{i}"] = ContactSensor(self.cfg.__dict__["contact_sensor_" + str(i)])
            self.scene.sensors[f"robot_{i}"] = self.contact_sensors[f"robot_{i}"]
            self.height_scanners[f"robot_{i}"] = RayCaster(self.cfg.__dict__["height_scanner_" + str(i)])
            self.scene.sensors[f"robot_{i}"] = self.height_scanners[f"robot_{i}"]

        self.cfg.terrain.num_envs = self.scene.cfg.num_envs
        self.cfg.terrain.env_spacing = self.scene.cfg.env_spacing
        self._terrain = self.cfg.terrain.class_type(self.cfg.terrain)
        # clone, filter, and replicate
        self.scene.clone_environments(copy_from_source=False)
        self.scene.filter_collisions(global_prim_paths=[self.cfg.terrain.prim_path])
        # add lights
        light_cfg = sim_utils.DomeLightCfg(intensity=2000.0, color=(0.75, 0.75, 0.75))
        light_cfg.func("/World/Light", light_cfg)

    def _pre_physics_step(self, actions: torch.Tensor):
        self.processed_actions = copy.deepcopy(actions)
        for robot_id, robot in self.robots.items():
            self.actions[robot_id] = actions[robot_id].clone()
            self.processed_actions[robot_id] = self.cfg.action_scale * self.actions[robot_id] + robot.data.default_joint_pos

    def _apply_action(self):
        for robot_id, robot in self.robots.items():
            robot.set_joint_position_target(self.processed_actions[robot_id])

    def _get_observations(self) -> dict:
        self.previous_actions = copy.deepcopy(self.actions)
        height_datas = {}
        for robot_id, robot in self.robots.items():
            height_data = None
            # if isinstance(self.cfg, HeterogeneousMultiAgentWalkingRoughEnvCfg):
            height_data = (
                self.height_scanners[robot_id].data.pos_w[:, 2].unsqueeze(1) - self.height_scanners[robot_id].data.ray_hits_w[..., 2] - 0.5
            ).clip(-1.0, 1.0)
            height_datas[robot_id] = (height_data)

        
        obs = {}
        for robot_id, robot in self.robots.items():
            obs[robot_id] = (torch.cat(
            [
                tensor
                for tensor in (
                    robot.data.root_lin_vel_b,
                    robot.data.root_ang_vel_b,
                    robot.data.projected_gravity_b,
                    self._commands[robot_id],
                    robot.data.joint_pos - robot.data.default_joint_pos,
                    robot.data.joint_vel,
                    height_datas[robot_id],
                    self.actions[robot_id],
                )
                if tensor is not None
            ],
            dim=-1,
            ))

        robotId = "robot_1"
        robot_1 = self.robots[robot_id]
        vel_loc, angvel_loc, roll, pitch, yaw, angle_to_target = compute_rot(
        torso_quat, velocity, ang_velocity, targets, torso_position
        )
        obs[robot_id] = torch.cat(
            (
                self.torso_position[:, 2].view(-1, 1),
                self.vel_loc,
                self.angvel_loc * self.cfg.angular_velocity_scale,
                normalize_angle(self.yaw).unsqueeze(-1),
                normalize_angle(self.roll).unsqueeze(-1),
                normalize_angle(self.angle_to_target).unsqueeze(-1),
                self.up_proj.unsqueeze(-1),
                self.heading_proj.unsqueeze(-1),
                self.dof_pos_scaled,
                self.dof_vel * self.cfg.dof_vel_scale,
                self.actions,
                self.commands
            ),
            dim=-1,
        )
        # obs = torch.cat(obs, dim=0)
        # observations = {"policy": obs}
        return obs
    

    def _compute_intermediate_values(self):
        self.torso_position, self.torso_rotation = self.robots["robot_1"].data.root_link_pos_w, self.robots["robot_1"].data.root_link_quat_w
        self.velocity, self.ang_velocity = self.robots["robot_1"].data.root_com_lin_vel_w, self.robots["robot_1"].data.root_com_ang_vel_w
        self.dof_pos, self.dof_vel = self.robots["robot_1"].data.joint_pos, self.robots["robot_1"].data.joint_vel

        (
            self.up_proj,
            self.heading_proj,
            self.up_vec,
            self.heading_vec,
            self.vel_loc,
            self.angvel_loc,
            self.roll,
            self.pitch,
            self.yaw,
            self.angle_to_target,
            self.dof_pos_scaled,
            self.prev_potentials,
            self.potentials,
        ) = compute_intermediate_values(
            self.targets,
            self.torso_position,
            self.torso_rotation,
            self.velocity,
            self.ang_velocity,
            self.dof_pos,
            self.robots["robot_1"].data.soft_joint_pos_limits[0, :, 0],
            self.robots["robot_1"].data.soft_joint_pos_limits[0, :, 1],
            self.inv_start_rot,
            self.basis_vec0,
            self.basis_vec1,
            self.potentials,
            self.prev_potentials,
            self.cfg.sim.dt,
        )
    
    def get_y_euler_from_quat(self, quaternion):
        w, x, y, z = quaternion[:,0], quaternion[:,1], quaternion[:,2], quaternion[:,3]
        y_euler_angle = torch.arcsin(2 * (w * y - z * x))
        return y_euler_angle

    def _get_rewards(self) -> dict:
        reward = {}
        for robot_id, robot in self.robots.items():
            # linear velocity tracking
            lin_vel_error = torch.sum(torch.square(self._commands[robot_id][:, :2] - robot.data.root_lin_vel_b[:, :2]), dim=1)
            lin_vel_error_mapped = torch.exp(-lin_vel_error / 0.25)
            # yaw rate tracking
            yaw_rate_error = torch.square(self._commands[robot_id][:, 2] - robot.data.root_ang_vel_b[:, 2])
            yaw_rate_error_mapped = torch.exp(-yaw_rate_error / 0.25)
            # z velocity tracking
            z_vel_error = torch.square(robot.data.root_lin_vel_b[:, 2])
            # angular velocity x/y
            ang_vel_error = torch.sum(torch.square(robot.data.root_ang_vel_b[:, :2]), dim=1)
            # joint torques
            joint_torques = torch.sum(torch.square(robot.data.applied_torque), dim=1)
            # joint acceleration
            joint_accel = torch.sum(torch.square(robot.data.joint_acc), dim=1)
            # action rate            
            action_rate = torch.sum(torch.square(self.actions[robot_id] - self.previous_actions[robot_id]).view(1,-1), dim=1)
            # feet air time
            first_contact = self.contact_sensors[robot_id].compute_first_contact(self.step_dt)[:, self.feet_ids[robot_id]]
            last_air_time = self.contact_sensors[robot_id].data.last_air_time[:, self.feet_ids[robot_id]]
            air_time = torch.sum((last_air_time - 0.5) * first_contact, dim=1) * (
                torch.norm(self._commands[robot_id][:, :2], dim=1) > 0.1
            )
            # undersired contacts
            net_contact_forces = self.contact_sensors[robot_id].data.net_forces_w_history
            is_contact = (
                torch.max(torch.norm(net_contact_forces[:, :, self.undesired_body_contact_ids[robot_id]], dim=-1), dim=1)[0] > 1.0
            )
            contacts = torch.sum(is_contact, dim=1)
            # flat orientation
            flat_orientation = torch.sum(torch.square(robot.data.projected_gravity_b[:, :2]), dim=1)

            rewards = {
                "track_lin_vel_xy_exp": lin_vel_error_mapped * self.cfg.lin_vel_reward_scale * self.step_dt,
                "track_ang_vel_z_exp": yaw_rate_error_mapped * self.cfg.yaw_rate_reward_scale * self.step_dt,
                "lin_vel_z_l2": z_vel_error * self.cfg.z_vel_reward_scale * self.step_dt,
                "ang_vel_xy_l2": ang_vel_error * self.cfg.ang_vel_reward_scale * self.step_dt,
                "dof_torques_l2": joint_torques * self.cfg.joint_torque_reward_scale * self.step_dt,
                "dof_acc_l2": joint_accel * self.cfg.joint_accel_reward_scale * self.step_dt,
                "action_rate_l2": (action_rate * self.cfg.action_rate_reward_scale * self.step_dt).repeat(self.num_envs),
                "feet_air_time": air_time * self.cfg.feet_air_time_reward_scale * self.step_dt,
                "undesired_contacts": contacts * self.cfg.undersired_contact_reward_scale * self.step_dt,
                "flat_orientation_l2": flat_orientation * self.cfg.flat_orientation_reward_scale * self.step_dt,
                "flat_bar_roll_angle" : torch.abs(self.get_y_euler_from_quat(self.object.data.root_quat_w))\
                      * self.cfg.flat_bar_roll_angle_reward_scale * self.step_dt
            }
            curr_reward = torch.sum(torch.stack(list(rewards.values())), dim=0)

            reward[robot_id] = curr_reward

        # Logging
        for key, value in rewards.items():
            self._episode_sums[key] += value

        return reward

    # def _get_dones(self) -> tuple[torch.Tensor, torch.Tensor]:
    #     all_dones = {}
    #     all_died = []
    #     for i in range(self.num_robots):
    #         time_out = self.episode_length_buf >= self.max_episode_length - 1
    #         net_contact_forces = self.contact_sensors[i].data.net_forces_w_history
    #         died = torch.any(torch.max(torch.norm(net_contact_forces[:, :, self.base_ids[i]], dim=-1), dim=1)[0] > 1.0, dim=1)
    #         all_dones.append(time_out)
    #         all_died.append(died)
        
    #     return torch.any(torch.cat(all_dones), dim=0), torch.any(torch.cat(all_died), dim=0)

    #TODO: Implement a dones function that handles multiple robots 
    def _get_dones(self) -> tuple[dict, dict]:
        y_euler_angle = self.get_y_euler_from_quat(self.object.data.root_quat_w) 
        # if the angle of the bar > pi/64 reset
        bar_angle_dones = (torch.abs(y_euler_angle) > 0.1)

        # check if the bar has fallen on the ground
        bar_z_pos = self.object.data.body_pos_w[:,:,2].view(-1)
        bar_fallen = bar_z_pos < 0.2

        dones = torch.logical_or(bar_angle_dones, bar_fallen)

        time_out = self.episode_length_buf >= self.max_episode_length - 1
        # net_contact_forces = contact_sensor.data.net_forces_w_history
        # died = torch.any(torch.max(torch.norm(net_contact_forces[:, :, base_id], dim=-1), dim=1)[0] > 1.0, dim=1)
        return {key:time_out for key in self.robots.keys()}, {key:dones  for key in self.robots.keys()}
    
    def _reset_idx(self, env_ids: torch.Tensor | None):
        super()._reset_idx(env_ids)

        object_default_state = self.object.data.default_root_state.clone()[env_ids]
        object_default_state[:, 0:3] = (
            object_default_state[:, 0:3] + self.scene.env_origins[env_ids]
        )
        self.object.write_root_state_to_sim(object_default_state, env_ids)
        # self.object.reset(env_ids)

        # Joint position command (deviation from default joint positions)
        self.actions = {agent : torch.zeros(self.num_envs, action_space, device=self.device) for agent, action_space in self.cfg.action_spaces.items()}
        self.previous_actions = {agent : torch.zeros(self.num_envs, action_space, device=self.device) for agent, action_space in self.cfg.action_spaces.items()}

        # X/Y linear velocity and yaw angular velocity commands
        self._commands = {agent : torch.zeros(self.num_envs, 3, device=self.device) for agent in self.cfg.possible_agents}

        for _, robot in self.robots.items():
            if env_ids is None or len(env_ids) == self.num_envs:
                env_ids = robot._ALL_INDICES
            robot.reset(env_ids)
            if len(env_ids) == self.num_envs:
                # Spread out the resets to avoid spikes in training when many environments reset at a similar time
                self.episode_length_buf[:] = torch.randint_like(self.episode_length_buf, high=int(self.max_episode_length))

            # Reset robot state
            joint_pos = robot.data.default_joint_pos[env_ids]
            joint_vel = robot.data.default_joint_vel[env_ids]
            default_root_state = robot.data.default_root_state[env_ids]
            default_root_state[:, :3] += self._terrain.env_origins[env_ids]
            robot.write_root_pose_to_sim(default_root_state[:, :7], env_ids)
            robot.write_root_velocity_to_sim(default_root_state[:, 7:], env_ids)
            robot.write_joint_state_to_sim(joint_pos, joint_vel, None, env_ids)
            # Logging
            extras = dict()
            for key in self._episode_sums.keys():
                episodic_sum_avg = torch.mean(self._episode_sums[key][env_ids])
                extras["Episode_Reward/" + key] = episodic_sum_avg / self.max_episode_length_s
                self._episode_sums[key][env_ids] = 0.0
            self.extras["log"] = dict()
            self.extras["log"].update(extras)
            extras = dict()
            # extras["Episode_Termination/base_contact"] = torch.count_nonzero(self.reset_terminated[env_ids]).item()
            # extras["Episode_Termination/time_out"] = torch.count_nonzero(self.reset_time_outs[env_ids]).item()
            self.extras["log"].update(extras)
    

@torch.jit.script
def compute_intermediate_values(
    targets: torch.Tensor,
    torso_position: torch.Tensor,
    torso_rotation: torch.Tensor,
    velocity: torch.Tensor,
    ang_velocity: torch.Tensor,
    dof_pos: torch.Tensor,
    dof_lower_limits: torch.Tensor,
    dof_upper_limits: torch.Tensor,
    inv_start_rot: torch.Tensor,
    basis_vec0: torch.Tensor,
    basis_vec1: torch.Tensor,
    potentials: torch.Tensor,
    prev_potentials: torch.Tensor,
    dt: float,
):
    to_target = targets - torso_position
    to_target[:, 2] = 0.0
    torso_quat, up_proj, heading_proj, up_vec, heading_vec = compute_heading_and_up(
        torso_rotation, inv_start_rot, to_target, basis_vec0, basis_vec1, 2
    )

    vel_loc, angvel_loc, roll, pitch, yaw, angle_to_target = compute_rot(
        torso_quat, velocity, ang_velocity, targets, torso_position
    )

    dof_pos_scaled = torch_utils.maths.unscale(dof_pos, dof_lower_limits, dof_upper_limits)

    to_target = targets - torso_position
    to_target[:, 2] = 0.0
    prev_potentials[:] = potentials
    potentials = -torch.norm(to_target, p=2, dim=-1) / dt

    return (
        up_proj,
        heading_proj,
        up_vec,
        heading_vec,
        vel_loc,
        angvel_loc,
        roll,
        pitch,
        yaw,
        angle_to_target,
        dof_pos_scaled,
        prev_potentials,
        potentials,
    )