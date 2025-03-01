# from fabric import Fabricator
# from fabric.widgets.box import Box
# from fabric.widgets.label import Label
from fabric.widgets.webview import WebView
from fabric.widgets.box import Box
# from gi.repository import GLib

class MyCgm(Box):
    def __init__(self, **kwargs):
        super().__init__(
            name="box-2",
            spacing=4,
            h_align="center",
            v_align="center"
        )

        url_file_path = "/home/mathias/.config/nightscoutURL.txt"
        try:
            with open(url_file_path, "r") as file:
                url = file.read().strip()
                if url:
                    self.url = url
        except Exception as e:
            print(f"Error reading URL file: {e}")
        print("$USER")
        self.web = WebView(
            url=self.url,
            size=[610,285]
        )
        self.add(self.web)
