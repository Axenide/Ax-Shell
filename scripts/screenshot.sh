#!/usr/bin/env sh

sleep 0.25

if [ -z "$XDG_PICTURES_DIR" ]; then
    XDG_PICTURES_DIR="$HOME/Pictures"
fi

save_dir="${3:-$XDG_PICTURES_DIR/Screenshots}"
save_file=$(date +'%y%m%d_%Hh%Mm%Ss_screenshot.png')
full_path="$save_dir/$save_file"
mkdir -p "$save_dir"

mockup_mode="$2"

function print_error {
    cat <<"EOF"
    ./screenshot.sh <action> [mockup]
    ...valid actions are...
        p  : print selected screen
        s  : snip selected region
        sf : snip selected region (frozen)
        m  : print focused monitor
        w  : snip focused window
EOF
}

case $1 in
p) hyprshot -s -m output -o "$save_dir" -f "$save_file" ;;
s) hyprshot -s -m region -o "$save_dir" -f "$save_file" ;;
sf) hyprshot -s -z -m region -o "$save_dir" -f "$save_file" ;;
m) hyprshot -s -m output -m active -o "$save_dir" -f "$save_file" ;;
w) hyprshot -s -m window -o "$save_dir" -f "$save_file" ;; # Added window capture
*)
    print_error
    exit 1
    ;;
esac

if [ -f "$full_path" ]; then
    # Copy original to clipboard if not doing mockup
    if [ "$mockup_mode" != "mockup" ]; then
        if command -v wl-copy >/dev/null 2>&1; then
            wl-copy < "$full_path"
        elif command -v xclip >/dev/null 2>&1; then
            xclip -selection clipboard -t image/png < "$full_path"
        fi
    fi

    # Process as mockup if requested
    if [ "$mockup_mode" = "mockup" ]; then
        temp_file="${full_path%.png}_temp.png"
        mockup_file="${full_path%.png}_mockup.png"
        mockup_success=true # Flag to track success

        # Create a mockup version with rounded corners, shadow, and transparency
        if [ "$mockup_success" = true ]; then
            convert "$full_path" \
                \( +clone -alpha extract -draw 'fill black polygon 0,0 0,20 20,0 fill white circle 20,20 20,0' \
                \( +clone -flip \) -compose Multiply -composite \
                \( +clone -flop \) -compose Multiply -composite \
                \) -alpha off -compose CopyOpacity -composite "$temp_file"
            if [ $? -ne 0 ]; then
                echo "Error: 'convert' failed during corner rounding/transparency." >&2
                mockup_success=false
            fi
        fi

        # Add shadow with increased opacity and size for better visibility
        if [ "$mockup_success" = true ]; then
            convert "$temp_file" \
                \( +clone -background black -shadow 60x20+0+10 -alpha set -channel A -evaluate multiply 1 +channel \) \
                +swap -background none -layers merge +repage "$mockup_file"
            if [ $? -ne 0 ]; then
                echo "Error: 'convert' failed during shadow application." >&2
                mockup_success=false
            fi
        fi

        # Check if mockup processing was successful before moving/copying
        if [ "$mockup_success" = true ] && [ -f "$mockup_file" ]; then
            # Remove temporary files
            rm "$temp_file"

            # Replace original screenshot with mockup version
            mv "$mockup_file" "$full_path"

            # Copy the processed mockup to clipboard
            if command -v wl-copy >/dev/null 2>&1; then
                wl-copy < "$full_path"
            elif command -v xclip >/dev/null 2>&1; then
                xclip -selection clipboard -t image/png < "$full_path"
            fi
        else
            echo "Warning: Mockup processing failed for $full_path. Keeping original." >&2
            # Clean up potentially created temp files if they exist
            rm -f "$temp_file" "$mockup_file" # Also remove potentially incomplete mockup file
            # Copy the original screenshot to clipboard as fallback
            if [ "$mockup_mode" = "mockup" ]; then # Only copy original if mockup was intended but failed
                if command -v wl-copy >/dev/null 2>&1; then
                    wl-copy < "$full_path"
                elif command -v xclip >/dev/null 2>&1; then
                    xclip -selection clipboard -t image/png < "$full_path"
                fi
            fi
        fi
    fi

    ACTION=$(notify-send -a "Ax-Shell" -i "$full_path" "Screenshot saved" "in $full_path" \
        -A "view=View" -A "edit=Edit" -A "open=Open Folder")

    case "$ACTION" in
    view) xdg-open "$full_path" ;;
    edit) swappy -f "$full_path" ;;
    open) xdg-open "$save_dir" ;;
    esac
else
    notify-send -a "Ax-Shell" "Screenshot Aborted"
fi
