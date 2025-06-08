from collections.abc import Iterable
from enum import Enum
from typing import Literal, cast, overload

import gi
import OpenGL.GL as GL
from fabric import Application, Property, Signal
from fabric.widgets.widget import Widget
from OpenGL.GL.shaders import compileProgram, compileShader

gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk


class ShadertoyUniformType(Enum):
    # TODO: add more types
    FLOAT = 1
    INTEGER = 2
    VECTOR = 3
    TEXTURE = 4


class ShadertoyCompileError(Exception): ...


class Shadertoy(Gtk.GLArea, Widget):
    @Signal  # pygobject signal
    def ready(self) -> None: ...

    @Property(str, "read-write")
    def shader_buffer(self) -> str:
        return self._shader_buffer

    @shader_buffer.setter
    def shader_buffer(self, shader_buffer: str) -> None:
        self._shader_buffer = shader_buffer
        if not self._ready:
            return
        self._shader_uniforms.clear()
        self.do_realize()
        self.queue_draw()
        return

    # signatures for building a replica of shadertoy
    DEFAULT_VERTEX_SHADER = """
    #version 330

    in vec2 position;

    void main() {
        gl_Position = vec4(position, 0.0, 1.0);
    }
    """

    DEFAULT_FRAGMENT_UNIFORMS = """
    #version 330

    uniform vec3 iResolution;           // viewport resolution (in pixels)
    uniform float iTime;                 // shader playback time (in seconds)
    uniform float iTimeDelta;            // render time (in seconds)
    uniform float iFrameRate;            // shader frame rate
    uniform int iFrame;                  // shader playback frame
    uniform float iChannelTime[4];       // channel playback time (in seconds)
    uniform vec3 iChannelResolution[4];  // channel resolution (in pixels)
    uniform vec4 iMouse;                 // mouse pixel coords. xy: current (if MLB down), zw: click
    uniform sampler2D iChannel0;         // input channel. XX = 2D/Cube
    uniform sampler2D iChannel1;
    uniform sampler2D iChannel2;
    uniform sampler2D iChannel3;
    uniform vec4 iDate;                  // (year, month, day, time in seconds)
    uniform float iSampleRate;           // sound sample rate (i.e., 44100)

    """

    FRAGMENT_MAIN_FUNCTION = """
    void main() {
        mainImage(gl_FragColor, gl_FragCoord.xy);
    }
    """

    def __init__(
        self,
        shader_buffer: str,
        shader_uniforms: list[
            tuple[
                str,
                ShadertoyUniformType,
                bool | float | int | tuple[float, ...] | GdkPixbuf.Pixbuf,
            ]
        ]
        | None = None,
        name: str | None = None,
        visible: bool = True,
        all_visible: bool = False,
        style: str | None = None,
        style_classes: Iterable[str] | str | None = None,
        tooltip_text: str | None = None,
        tooltip_markup: str | None = None,
        h_align: Literal["fill", "start", "end", "center", "baseline"]
        | Gtk.Align
        | None = None,
        v_align: Literal["fill", "start", "end", "center", "baseline"]
        | Gtk.Align
        | None = None,
        h_expand: bool = False,
        v_expand: bool = False,
        size: Iterable[int] | int | None = None,
        **kwargs,
    ):
        Gtk.GLArea.__init__(
            self  # type: ignore
        )
        Widget.__init__(
            self,
            name,
            visible,
            all_visible,
            style,
            style_classes,
            tooltip_text,
            tooltip_markup,
            h_align,
            v_align,
            h_expand,
            v_expand,
            size,
            **kwargs,
        )
        self._shader_buffer = shader_buffer
        self._shader_uniforms = shader_uniforms or []

        # widget settings
        self.set_required_version(3, 3)
        self.set_has_depth_buffer(False)
        self.set_has_stencil_buffer(False)

        self._ready = False
        self._program = None
        self._vao = None
        self._quad_vbo = None
        self._texture_units = {}

        # timer
        self._start_time = GLib.get_monotonic_time() / 1e6
        self._frame_time = self._start_time
        self._frame_count = 0

        # to avoid a constant framerate we tell
        # gtk to render a frame whenever possible
        self._tick_id = self.add_tick_callback(lambda *_: (self.queue_draw(), True)[1])

    def do_bake_program(self):
        try:
            vertex_shader = compileShader(
                self.DEFAULT_VERTEX_SHADER, GL.GL_VERTEX_SHADER
            )
            fragment_shader = compileShader(
                self.DEFAULT_FRAGMENT_UNIFORMS
                + self._shader_buffer
                + self.FRAGMENT_MAIN_FUNCTION,
                GL.GL_FRAGMENT_SHADER,
            )
        except Exception as e:
            raise ShadertoyCompileError(
                f"couldn't compile the provided shader, OpenGL error:\n {e}"
            )

        return compileProgram(vertex_shader, fragment_shader)

    def do_realize(self, *_):
        Gtk.GLArea.do_realize(self)
        if not self._ready:
            ctx = self.get_context()
            if (err := self.get_error()) or not ctx:
                raise RuntimeError(
                    f"couldn't initialize the drawing context, error: {err or 'context is None'}"
                )

            ctx.make_current()

        if self._program:
            GL.glDeleteProgram(self._program)
            self._program = None
        self._program = self.do_bake_program()

        # NOTE: for this to work (alpha pixels) `self.set_has_alpha(True)` must be done
        # this breaks some fragment shaders, for some reason, so i'm leaving it for anyone willing to use
        GL.glEnable(GL.GL_BLEND)
        GL.glBlendFunc(GL.GL_SRC_ALPHA, GL.GL_ONE_MINUS_SRC_ALPHA)

        self._quad_vbo = GL.glGenBuffers(1)
        GL.glBindBuffer(GL.GL_ARRAY_BUFFER, self._quad_vbo)

        # this is not so good, unless the introduction of numpy, we must do
        # a hack to generate an array GL would accept, i've tried using
        # the "array" python library but it doesn't seem to be working

        # cast python type into GL type (list[float] -> arraybuf[GLfloat])
        quad_verts = (-1.0, -1.0, 1.0, -1.0, -1.0, 1.0, 1.0, 1.0)
        array_type = GL.GLfloat * len(quad_verts)

        GL.glBufferData(
            GL.GL_ARRAY_BUFFER,
            len(quad_verts) * 4,
            array_type(*quad_verts),
            GL.GL_STATIC_DRAW,
        )

        self._vao = GL.glGenVertexArrays(1)
        GL.glBindVertexArray(self._vao)

        position = GL.glGetAttribLocation(self._program, "position")
        GL.glEnableVertexAttribArray(position)
        GL.glVertexAttribPointer(position, 2, GL.GL_FLOAT, GL.GL_FALSE, 0, None)

        for uname, utype, uvalue in self._shader_uniforms:
            self.set_uniform(uname, utype, uvalue)  # type: ignore

        self._ready = True
        self.ready()
        return

    def do_get_timing(self) -> tuple[float, float, float]:
        current_time = GLib.get_monotonic_time() / 1e6
        delta_time = current_time - self._frame_time
        return current_time, delta_time, (1.0 / delta_time) if delta_time > 0 else 0.0

    def do_post_render(self, time: float):
        self._frame_time = time
        self._frame_count += 1
        return

    def do_render(self, ctx: Gdk.GLContext):
        if not self._program:
            if self._tick_id:
                self.remove_tick_callback(self._tick_id)
            self._tick_id = 0
            return False

        GL.glUseProgram(self._program)

        # clear up for next frame
        GL.glClear(GL.GL_COLOR_BUFFER_BIT)

        alloc = self.get_allocation()
        width: int = alloc.width  # type: ignore
        height: int = alloc.height  # type: ignore
        mouse_pos = cast(tuple[int, int], self.get_pointer())

        current_time, delta_time, frame_rate = self.do_get_timing()

        self.set_uniform(
            "iTime", ShadertoyUniformType.FLOAT, current_time - self._start_time
        )
        self.set_uniform("iFrame", ShadertoyUniformType.INTEGER, self._frame_count)
        self.set_uniform("iTimeDelta", ShadertoyUniformType.FLOAT, delta_time)
        self.set_uniform("iFrameRate", ShadertoyUniformType.FLOAT, frame_rate)
        self.set_uniform(
            "iResolution", ShadertoyUniformType.VECTOR, (width, height, 1.0)
        )
        self.set_uniform(
            "iMouse",
            ShadertoyUniformType.VECTOR,
            (mouse_pos[0], height - mouse_pos[1], 0, 0),
        )

        # paint the quad
        GL.glBindVertexArray(self._vao)
        GL.glDrawArrays(GL.GL_TRIANGLE_STRIP, 0, 4)
        self.do_post_render(current_time)
        return True

    def do_resize(self, width: int, height: int):
        Gtk.GLArea.do_resize(self, width, height)
        GL.glViewport(0, 0, width, height)
        return

    @overload
    def set_uniform(
        self, name: str, type: Literal[ShadertoyUniformType.FLOAT], value: float
    ): ...

    @overload
    def set_uniform(
        self, name: str, type: Literal[ShadertoyUniformType.INTEGER], value: int
    ): ...

    @overload
    def set_uniform(
        self,
        name: str,
        type: Literal[ShadertoyUniformType.VECTOR],
        value: tuple[float, ...],
    ): ...

    @overload
    def set_uniform(
        self,
        name: str,
        type: Literal[ShadertoyUniformType.TEXTURE],
        value: GdkPixbuf.Pixbuf,
    ): ...

    def set_uniform(
        self,
        name: str,
        type: ShadertoyUniformType,
        value: bool | float | int | tuple[float, ...] | GdkPixbuf.Pixbuf,
    ):
        if not self._program:
            raise RuntimeError("the shader program is not initialized")
        GL.glUseProgram(self._program)
        location = GL.glGetUniformLocation(self._program, name)
        match type:
            case ShadertoyUniformType.VECTOR:
                value = cast(tuple[float, ...], value)
                (
                    GL.glUniform2f
                    if (vlen := len(value)) == 2
                    else GL.glUniform3f
                    if vlen == 3
                    else GL.glUniform4f
                )(location, *value)
            case ShadertoyUniformType.FLOAT:
                GL.glUniform1f(location, value)
            case ShadertoyUniformType.INTEGER:
                GL.glUniform1i(location, value)
            case ShadertoyUniformType.TEXTURE:
                # who dislikes boilerplate?
                value = cast(GdkPixbuf.Pixbuf, value).flip(False)
                format = GL.GL_RGBA if value.get_has_alpha() else GL.GL_RGB

                if name not in self._texture_units:
                    texture = GL.glGenTextures(1)
                    self._texture_units[name] = (len(self._texture_units), texture)
                else:
                    texture_unit, texture = self._texture_units[name]

                texture_unit = self._texture_units[name][0]
                GL.glActiveTexture(GL.GL_TEXTURE0 + texture_unit)
                GL.glBindTexture(GL.GL_TEXTURE_2D, texture)

                GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_S, GL.GL_REPEAT)
                GL.glTexParameteri(GL.GL_TEXTURE_2D, GL.GL_TEXTURE_WRAP_T, GL.GL_REPEAT)
                GL.glTexParameteri(
                    GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MIN_FILTER, GL.GL_LINEAR
                )
                GL.glTexParameteri(
                    GL.GL_TEXTURE_2D, GL.GL_TEXTURE_MAG_FILTER, GL.GL_LINEAR
                )

                # "upload" the texture
                GL.glTexImage2D(
                    GL.GL_TEXTURE_2D,
                    0,  # detail level (woah?)
                    format,  # result format
                    value.get_width(),
                    value.get_height(),
                    0,  # "border"
                    format,  # input format
                    GL.GL_UNSIGNED_BYTE,
                    value.get_pixels(),
                )
                GL.glGenerateMipmap(GL.GL_TEXTURE_2D)

                # all aboard...
                GL.glUniform1i(location, texture_unit)
