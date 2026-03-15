# Talk To Data v3 Backend

# Add project root to path so backend can import shared core (talk_to_data.core)
import os
import sys

_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)
