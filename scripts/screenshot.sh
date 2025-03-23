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
        p  : print all screens
        s  : snip current screen
        sf : snip current screen (frozen)
        m  : print focused monitor
EOF
}

case $1 in
p) grimblast copysave screen "$full_path" ;;
s) grimblast copysave area "$full_path" ;;
sf) grimblast --freeze copysave area "$full_path" ;;
m) grimblast copysave output "$full_path" ;;
*)
    print_error
    exit 1
    ;;
esac

if [ -f "$full_path" ]; then
    # Process as mockup if requested
    if [ "$mockup_mode" = "mockup" ]; then
        temp_file="${full_path%.png}_temp.png"
        cropped_file="${full_path%.png}_cropped.png"
        mockup_file="${full_path%.png}_mockup.png"
        
        # First crop the top pixel using a different approach
        # Use +0+1 to start at y-coordinate 1 (skipping the first pixel row)
        convert "$full_path" -crop +0+1 +repage "$cropped_file"
        
        # Create a mockup version with rounded corners, shadow, and transparency
        convert "$cropped_file" \
            \( +clone -alpha extract -draw 'fill black polygon 0,0 0,20 20,0 fill white circle 20,20 20,0' \
            \( +clone -flip \) -compose Multiply -composite \
            \( +clone -flop \) -compose Multiply -composite \
            \) -alpha off -compose CopyOpacity -composite "$temp_file"
        
        # Add shadow with increased opacity and size for better visibility
        convert "$temp_file" \
            \( +clone -background black -shadow 60x20+0+10 -alpha set -channel A -evaluate multiply 1 +channel \) \
            +swap -background none -layers merge +repage "$mockup_file"
        
        # Remove temporary files
        rm "$temp_file" "$cropped_file"
        
        # Replace original screenshot with mockup version
        mv "$mockup_file" "$full_path"
        
        # Copy the processed mockup to clipboard
        if command -v wl-copy >/dev/null 2>&1; then
            wl-copy < "$full_path"
        elif command -v xclip >/dev/null 2>&1; then
            xclip -selection clipboard -t image/png < "$full_path"
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
