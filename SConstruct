"""SCons build configuration for wikify pipeline."""

import sys

# Add project root to path for imports
sys.path.insert(0, Dir(".").abspath)

from wikify.scons import (
     create_extraction_builder,
     get_data_repo_path,
     init_wikify,
)

env = Environment()
init_wikify(env.Dictionary(as_dict=True))
env.Append(BUILDERS={"Extract": create_extraction_builder(env)})

# Command-line options
AddOption(
    "--session",
    dest="session",
    type="int",
    metavar="N",
    help="Session number to extract (e.g., --session=20)",
)

# Build targets based on options
session_num = GetOption("session")
if session_num:
    data_path = get_data_repo_path()
    source = data_path / "sessions" / "raw" / f"session-{session_num:03d}.txt"
    target = data_path / "sessions" / "extracted" / f"session-{session_num:03d}.json"

    extraction = env.Extract(str(target), str(source))

    # Registry is an implicit dependency
    registry_path = data_path / "entity-registry.json"
    env.Depends(extraction, str(registry_path))
