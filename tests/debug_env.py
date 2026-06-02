# Copyright (c) 2026, AionGenos Cognitive Evolution Pipeline
# All rights reserved.

import traceback
import sys

try:
    print("Starting debug script...")
    import argparse
    from isaaclab.app import AppLauncher
    
    args_cli = argparse.Namespace(headless=True, num_envs=1, use_fabric=True, enable_cameras=True)
    app_launcher = AppLauncher(args_cli)
    simulation_app = app_launcher.app
    
    print("AppLauncher initialized.")
    
    from aiongenos.curriculum.arena_adapter import ArenaEnvBuilder
    from aiongenos.orchestrator.isaaclab_env_interface import IsaacLabEnvInterface
    
    print("Modules imported.")
    
    env = ArenaEnvBuilder.build_env(level=0, num_envs=1)
    print("Env created successfully.")
    
    env_interface = IsaacLabEnvInterface(env)
    print("Interface created.")
    
    env_interface.reset()
    print("Env reset successfully.")
    
    rgb = env_interface.get_rgb()
    print(f"Captured RGB image: {len(rgb)} bytes.")
    
    env.close()
    simulation_app.close()
    print("Done!")
except Exception as e:
    print("CAUGHT EXCEPTION:")
    traceback.print_exc()
    sys.exit(1)
