import yaml


def load_config():
    with open("./status-dashboard.yaml", "r") as yaml_file:
        return yaml.safe_load(yaml_file)
