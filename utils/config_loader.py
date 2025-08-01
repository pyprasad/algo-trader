# utils/config_loader.py

import os
import yaml

def load_global_config():
    with open(os.path.join("configs", "global.yaml"), "r") as f:
        return yaml.safe_load(f)

def load_asset_config(asset_name):
    with open(os.path.join("configs", "assets_comprehensive.yaml"), "r") as f:
        all_assets = yaml.safe_load(f)
        return all_assets.get(asset_name, {})
