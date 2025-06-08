from fabric import Fabricator
from fabric.widgets.box import Box
from fabric.widgets.label import Label
from fabric.widgets.button import Button
from fabric.widgets.scale import Scale
from widgets.image import CustomImage
from gi.repository import GLib, GdkPixbuf, Playerctl, Gdk, Pango
import modules.icons as icons
import requests


class Media(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="box-1",
            orientation="v",
            spacing=4,
            h_align="center",
            overflow="hidden",
            **kwargs,
        )
        # Initialize artist and title label
        DEFAULT_PLAYER = "spotify"
        self.artist_and_title = Label("NO MEDIA PLAYER EXIST YET", name="media-title")
        self.artist_and_title.set_ellipsize(Pango.EllipsizeMode.END)  # Enable ellipsization at the end
        self.artist_and_title.set_max_width_chars(20)  # Limit the visible characters
        self.artist_and_title.set_xalign(0.5)  # Align left
        self.title_text = ""
        # Set up album art display
        self.art = CustomImage(name="media-image", width=170, height=170)
        self.artbox = Box(
            name="media-image-box",
            h_align="center",
            children=Box(style="padding: 6px; border-radius: 15px; background-color: var(--primary);", children=self.art)
        )

        #Set up text shifting animation
        self.text_shift = Fabricator(
            interval=500,
            default_value=0,
            poll_from=lambda f: f.get_value() + 1,
            on_changed=lambda f, v: [
                self.artist_and_title.set_label((self.title_text + self.title_text)[v:v+20])
                if f.get_value() <= len(self.title_text)
                else f.set_value(0)
            ]
        )

        # Initialize progress bar
        self.progress = Scale(
            name="media-bar",
            min=0,
            max=0,
            value=90,
            orientation='h'
        )
        self.progress.add_events(Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_MOTION_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK)
        self.progress.connect("button-press-event", self.on_click)
        self.progress.connect("motion-notify-event", self.on_drag)
        self.progress.connect("button-release-event", self.on_release)

        # Set up time display
        self.song_time = Label(
            "0:00",
            name="song-time"
        )
        self.song_length = Label(
            "1:30",
            name="song-length"
        )

        # Set up player icons
        self.spotify_bt = Button(
            name="player-spotify",
            child=Label(name="button-label", markup=icons.spotify),
            on_CLICKED=lambda *_: self.set_to_player("spotify")
        )
        self.firefox_bt = Button(
            name="player-firefox",
            child=Label(name="button-label", markup=icons.firefox),
            on_CLICKED=lambda *_: self.set_to_player("firefox")
        )

        # Create progress bar label box
        self.progress_label_box = Box(
            name="media-bar-box-label",
            h_align="center",
            children=[self.song_time, self.spotify_bt, self.firefox_bt, self.song_length]
        )

        # Create progress bar container
        self.progress_box = Box(
            name="media-bar-box",
            orientation='v',
            children=[self.progress, self.progress_label_box]
        )

        # Initialize player controls
        self.player = Playerctl.Player()
        self.play_pause_icon = Label(name="button-label", markup=icons.play)

        # Set up time counter
        self.counter = Fabricator(
            interval=1000,
            default_value=self.progress.value,
            poll_from=lambda f: self.progress.value + 1,
            on_changed=lambda *_: self.update_time()
        )

        # Set up progress bar signal
        #self.progress.connect('change_value', self.set_player_time)

        # Initialize UI state
        self.set_to_player(DEFAULT_PLAYER)

        # Create control buttons
        buttons = [
            Button(
                name="media-menu-button",
                child=Label(name="button-label", markup=icons.skip_back),
                on_clicked=self.prev,
            ),
            Button(
                name="media-menu-button",
                child=self.play_pause_icon,
                on_clicked=self.play,
            ),
            Button(
                name="media-menu-button",
                child=Label(name="button-label", markup=icons.skip_forward),
                on_clicked=self.next,
            )
        ]

        # Create button container
        self.buttons1 = Box(
            orientation="h",
            spacing=4,
            h_align="center",
            h_expand=True,
            children=buttons
        )

        # Add all components to main container
        self.add(self.artbox)
        self.add(self.artist_and_title)
        self.add(self.progress_box)
        self.add(self.buttons1)

        # Show all widgets
        self.show_all()

    def play(self, *args):
        try:
            self.player.play_pause()
        except Exception as e:
            print(f"Error: {e}")
            self.set_to_player(self.player.props.player_name)

    def prev(self, *args):
        self.player.previous()

    def next(self, *args):
        self.player.next()

    def icon_player(self, player, status):
        match status:
            case status.PLAYING:
                self.play_pause_icon.set_markup(icons.pause)
                self.counter.start()
            case status.PAUSED:
                self.play_pause_icon.set_markup(icons.play)
                self.counter.stop()
        self.song_progress(self.progress, self.player.props.position)

    def song_progress(self, player, position):
        pos = position/1000000
        self.progress.value = pos
        self.counter.value = pos

    def set_player_time(self, range_value, scroll, value):
        margin = 5000000
        match scroll:
            case scroll.JUMP:
                if -margin < value*1000000 - self.player.props.position < margin:
                    return
                self.player.set_position(value*1000000)

    def on_click(self, widget, event):
        if event.button == 1:
            self.song_math = (self.get_allocated_width() - 20)/(self.player.props.metadata['mpris:length']/1000000)
            self.progress.value = event.x/self.song_math
            self.song_time.set_label(self.format_to_cool(round(self.progress.value)))

    def on_drag(self, widget, event):
        #print(event.x, self.player.props.metadata['mpris:length']/100000000, self.progress.value, self.song_math, self.get_allocated_width())
        if event.state & Gdk.ModifierType.BUTTON1_MASK:
            self.song_math = (self.get_allocated_width() - 20)/(self.player.props.metadata['mpris:length']/1000000)
            self.counter.stop()
            self.progress.value = event.x/self.song_math
            self.song_time.set_label(self.format_to_cool(round(self.progress.value)))

    def on_release(self, widget, event):
        if event.button == 1:
            self.player.set_position(self.progress.value*1000000)
            self.song_time.set_label(self.format_to_cool(round(self.player.props.position/1000000)))
            self.counter.start()

    def load_song(self, player, metadata):
        try:
            album_art_url = metadata['mpris:artUrl']
            self.title_text = "Now playing: "
            self.title_text += metadata['xesam:title']
            self.title_text += " - " + metadata['xesam:artist'][0] + " | "
            for i in range(20 - len(self.title_text)):
                self.title_text+=" "
            self.progress.set_range(
                min=0,
                max=metadata['mpris:length']/1000000
            )

            if self.player.props.player_name == "spotify":
                img_data = requests.get(album_art_url).content
                loader = GdkPixbuf.PixbufLoader()
                loader.set_size(170, 170)
                loader.write_bytes(GLib.Bytes.new(img_data)) # type: ignore
                loader.close()
                self.art.set_from_pixbuf(loader.get_pixbuf())
            elif self.player.props.player_name == "firefox":
                self.art.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_size(album_art_url[7:], width=500, height=175).new_subpixbuf(66,0,170,170))
            elif self.player.props.player_name == "brave":
                self.art.set_from_pixbuf(GdkPixbuf.Pixbuf.new_from_file_at_size(album_art_url[6:], width=500, height=175).new_subpixbuf(66,0,170,170))

            self.song_progress(self.progress, self.player.props.position)
            self.song_length.set_label(
                self.format_to_cool(round(self.player.props.metadata['mpris:length']/1000000))
            )
            self.update_time()

        except Exception as e:
            print(f"Error: {e}")
            return False


    def set_to_player(self, player):
        for p in Playerctl.list_players():
            if p.name == player:
                the_one = p

        try:
            self.player = Playerctl.Player.new_from_name(the_one)
        except:
            print(f'Tried to switch media controll. Could not find {player}')

        self.player.connect('metadata', self.load_song)
        self.player.connect('playback-status', self.icon_player)
        self.player.connect('seeked', self.song_progress)

        self.icon_player(self.player, self.player.props.playback_status)
        self.load_song(self.player, self.player.props.metadata)

    def format_to_cool(self, number):
        formatted = ""
        if int(number//60) // 60 >= 1:
            formatted += str(int(number//60) // 60)+":"
        formatted += str(int(number/60) % 60)
        formatted += ":" + str(number%60 if number%60 >= 10 else "0"+str(number%60))
        return formatted

    def update_time(self):
        if self.player:
            self.progress.set_value(self.player.props.position/1000000)
            self.song_time.set_label(self.format_to_cool(round(self.player.props.position/1000000)))
