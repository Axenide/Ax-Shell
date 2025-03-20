import subprocess
import json

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
        # Assume the output similar to: "ID <number>"
        # Extracting the number from the output
        parts = result.stdout.split()
        for i, part in enumerate(parts):
            if part == "ID" and i + 1 < len(parts):
                return int(parts[i+1])
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
            ["hyprctl", "-j", "clients"],
            capture_output=True,
            text=True
        )
        clients = json.loads(result.stdout)
    except Exception as e:
        print(f"Error retrieving client windows: {e}")
        return False

    occ_x, occ_y, occ_width, occ_height = occlusion_region
    occ_x2 = occ_x + occ_width
    occ_y2 = occ_y + occ_height

    for client in clients:
        # Check if client is mapped
        if not client.get("mapped", False):
            continue

        # Ensure client has proper workspace information and matches the workspace
        client_workspace = client.get("workspace", {})
        if client_workspace.get("id") != workspace:
            continue

        # Ensure client has position and size info
        position = client.get("at")
        size = client.get("size")
        if not position or not size:
            continue

        x, y = position
        width, height = size
        win_x1, win_y1 = x, y
        win_x2, win_y2 = x + width, y + height

        # Check for intersection between the window and occlusion region
        if not (win_x2 <= occ_x or win_x1 >= occ_x2 or win_y2 <= occ_y or win_y1 >= occ_y2):
            return True  # Occlusion region is occupied

    return False  # No window overlaps the occlusion region
