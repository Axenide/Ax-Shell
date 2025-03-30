import subprocess
import json

import config.data as data

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

def get_screen_dimensions():
    """
    Get screen dimensions from hyprctl.
    
    Returns:
        tuple: (width, height) of the monitor containing the current workspace
    """
    try:
        # Get current workspace
        workspace_id = get_current_workspace()
        
        # Get monitor information
        result = subprocess.run(
            ["hyprctl", "-j", "monitors"],
            capture_output=True,
            text=True
        )
        monitors = json.loads(result.stdout)
        
        # Find the monitor containing our workspace
        for monitor in monitors:
            if monitor.get("activeWorkspace", {}).get("id") == workspace_id:
                return monitor.get("width", data.CURRENT_WIDTH), monitor.get("height", data.CURRENT_HEIGHT)
                
        # Fallback to first monitor
        if monitors:
            return monitors[0].get("width", data.CURRENT_WIDTH), monitors[0].get("height", data.CURRENT_HEIGHT)
    except Exception as e:
        print(f"Error getting screen dimensions: {e}")
    
    # Default fallback values
    return data.CURRENT_WIDTH, data.CURRENT_HEIGHT

def check_occlusion(occlusion_region, workspace=None):
    """
    Check if a region is occupied by any window on a given workspace.

    Parameters:
        occlusion_region: Can be one of:
            - tuple (side, size): where side is "top", "bottom", "left", or "right"
              and size is the pixel width of the region
            - tuple (x, y, width, height): The full region coordinates (legacy format)
        workspace (int, optional): The workspace ID to check. If None, the current workspace is used.

    Returns:
        bool: True if any window overlaps with the occlusion region, False otherwise.
    """
    if workspace is None:
        workspace = get_current_workspace()
    
    # Handle simplified side-based format
    if isinstance(occlusion_region, tuple) and len(occlusion_region) == 2:
        side, size = occlusion_region
        if isinstance(side, str):
            # Convert side-based format to coordinates
            screen_width, screen_height = get_screen_dimensions()
            
            if side.lower() == "bottom":
                occlusion_region = (0, screen_height - size, screen_width, size)
            elif side.lower() == "top":
                occlusion_region = (0, 0, screen_width, size)
            elif side.lower() == "left":
                occlusion_region = (0, 0, size, screen_height)
            elif side.lower() == "right":
                occlusion_region = (screen_width - size, 0, size, screen_height)
    
    # Ensure occlusion_region is in the correct format (x, y, width, height)
    if not isinstance(occlusion_region, tuple) or len(occlusion_region) != 4:
        print(f"Invalid occlusion region format: {occlusion_region}")
        return False

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
