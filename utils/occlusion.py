import subprocess
import re

def get_current_workspace():
    """
    Get the current workspace ID using hyprctl.
    """
    try:
        result = subprocess.run(
            ["hyprctl", "activeworkspace"],
            capture_output=True,
            text=True
        )
        match = re.search(r"ID (\d+)", result.stdout)
        if match:
            return int(match.group(1))
    except Exception as e:
        print(f"Error getting current workspace: {e}")
    return -1

def check_occlusion(occlusion_region, workspace=None):
    """
    Check if a custom occlusion region is occupied by any window on a given workspace.

    Parameters:
        occlusion_region (tuple): A tuple (x, y, width, height) defining the region to check.
        workspace (int, optional): The workspace ID to check. If None, the current workspace is used.

    Returns:
        bool: True if any window overlaps with the occlusion region, False otherwise.
    """
    if workspace is None:
        workspace = get_current_workspace()

    try:
        result = subprocess.run(
            ["hyprctl", "clients"],
            capture_output=True,
            text=True
        )
        clients = result.stdout
    except Exception as e:
        print(f"Error retrieving client windows: {e}")
        return False

    occ_x, occ_y, occ_width, occ_height = occlusion_region
    occ_x2 = occ_x + occ_width
    occ_y2 = occ_y + occ_height

    # Precompile regex patterns for performance
    workspace_pattern = re.compile(r"workspace:\s*(\d+)")
    position_pattern = re.compile(r"at:\s*(-?\d+),(-?\d+)")
    size_pattern = re.compile(r"size:\s*(\d+),(\d+)")
    mapped_pattern = re.compile(r"mapped:\s*(\d+)")

    # Process each client (window) block
    for client in clients.split("\n\n"):
        if "workspace" not in client or "at:" not in client or "size:" not in client:
            continue

        mapped_match = mapped_pattern.search(client)
        if not mapped_match or int(mapped_match.group(1)) == 0:
            continue  # Skip unmapped windows

        workspace_match = workspace_pattern.search(client)
        if not workspace_match or int(workspace_match.group(1)) != workspace:
            continue  # Skip windows from other workspaces

        position_match = position_pattern.search(client)
        size_match = size_pattern.search(client)
        if not position_match or not size_match:
            continue

        # Extract window position and size
        x, y = map(int, position_match.groups())
        width, height = map(int, size_match.groups())
        win_x1, win_y1 = x, y
        win_x2, win_y2 = x + width, y + height

        # Check for intersection between the window and occlusion region
        if not (win_x2 <= occ_x or win_x1 >= occ_x2 or win_y2 <= occ_y or win_y1 >= occ_y2):
            return True  # Occlusion region is occupied

    return False  # No window overlaps the occlusion region
