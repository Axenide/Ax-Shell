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

print_error() {
    cat <<EOF
    ./screenshot.sh <action> [mockup]
    ...valid actions are...
        p  : print selected screen
        s  : snip selected region
        w  : snip focused window
EOF
}

case $1 in
    p)
        hyprshot -z -s -m output -o "$save_dir" -f "$save_file"
        ;;
    s)
        hyprshot -z -s -m region -o "$save_dir" -f "$save_file"
        ;;
    w)
        hyprshot -s -m window -o "$save_dir" -f "$save_file";
        ;;
    *)
        print_error
        exit 1
        ;;
esac

if [ -f "$full_path" ]; then
    # Copiar al portapapeles si no es mockup
    if [ "$mockup_mode" != "mockup" ]; then
        if command -v wl-copy >/dev/null 2>&1; then
            wl-copy < "$full_path"
        elif command -v xclip >/dev/null 2>&1; then
            xclip -selection clipboard -t image/png < "$full_path"
        fi
    fi

    # Procesar mockup
    if [ "$mockup_mode" = "mockup" ]; then
        temp_file="${full_path%.png}_temp.png"
        mockup_file="${full_path%.png}_mockup.png"
        mockup_success=true

        # Redondear esquinas y transparencia
        if [ "$mockup_success" = true ]; then
            magick "$full_path" \
                \( +clone -alpha extract -draw 'fill black polygon 0,0 0,20 20,0 fill white circle 20,20 20,0' \
                   \( +clone -flip \) -compose Multiply -composite \
                   \( +clone -flop \) -compose Multiply -composite \
                \) -alpha off -compose CopyOpacity -composite "$temp_file" || mockup_success=false
        fi

        # Añadir sombra
        if [ "$mockup_success" = true ]; then
            magick "$temp_file" \
                \( +clone -background black -shadow 60x20+0+10 -alpha set -channel A -evaluate multiply 1 +channel \) \
                +swap -background none -layers merge +repage "$mockup_file" || mockup_success=false
        fi

        if [ "$mockup_success" = true ] && [ -f "$mockup_file" ]; then
            rm "$temp_file"
            mv "$mockup_file" "$full_path"
            if command -v wl-copy >/dev/null 2>&1; then
                wl-copy < "$full_path"
            elif command -v xclip >/dev/null 2>&1; then
                xclip -selection clipboard -t image/png < "$full_path"
            fi
        else
            echo "Warning: Mockup processing failed, manteniendo original." >&2
            rm -f "$temp_file" "$mockup_file"
            if [ "$mockup_mode" = "mockup" ]; then
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
