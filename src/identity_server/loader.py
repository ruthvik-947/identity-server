from pathlib import Path
import yaml
from .schema import IdentityConfig

def load_identity(path: Path) -> IdentityConfig:
    if not path.exists():
        raise FileNotFoundError(f"Identity file not found: {path}")

    with open(path) as f:
        data = yaml.safe_load(f)

    return IdentityConfig.from_dict(data)
