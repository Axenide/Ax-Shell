#!/usr/bin/env sh

sleep 0.25

if [ -z "$XDG_PICTURES_DIR" ]; then
    XDG_PICTURES_DIR="$HOME/Pictures"
fi

save_dir="${2:-$XDG_PICTURES_DIR/Screenshots}"
save_file=$(date +'%y%m%d_%Hh%Mm%Ss_screenshot.png')
full_path="$save_dir/$save_file"
mkdir -p "$save_dir"

function print_error {
    cat <<"EOF"
    ./screenshot.sh <action>
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
