# -*- Mode: Python; indent-tabs-mode: t; python-indent: 4; tab-width: 4 -*-
from gi.repository import Gtk, Gdk
from config.cava_config import AttributeDict
from math import pi


class Spectrum:
	"""Spectrum drawing"""
	def __init__(self, config, cavaconfig):
		self.silence_value = 0
		self.config = config
		self.cavaconfig = cavaconfig
		self.audio_sample = []
		self.color = None

		self.area = Gtk.DrawingArea()
		self.area.connect("draw", self.redraw)
		self.area.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)

		self.sizes = AttributeDict()
		self.sizes.area = AttributeDict()
		self.sizes.bar = AttributeDict()

		self.area.connect("configure-event", self.size_update)
		self.color_update()

	def is_silence(self, value):
		"""Check if volume level critically low during last iterations"""
		self.silence_value = 0 if value > 0 else self.silence_value + 1
		return self.silence_value > self.config["draw"]["silence"]

	def update(self, data):
		"""Audio data processing"""
		self.audio_sample = data
		if not self.is_silence(self.audio_sample[0]):
			self.area.queue_draw()
		elif self.silence_value == (self.config["draw"]["silence"] + 1):
			self.audio_sample = [0] * self.sizes.number
			self.area.queue_draw()

	# noinspection PyUnusedLocal
	def redraw(self, widget, cr):
		"""Draw spectrum graph"""
		cr.set_source_rgba(*self.color)
		#cr.set_source_rgba(170/255, 170/255, 1, 1)

		dx = self.config["offset"]["left"]

		center_y = self.sizes.area.height / 2  # Centro vertical del área de dibujo
		for i, value in enumerate(self.audio_sample):

			#width = self.sizes.bar.width + int(i < self.sizes.wcpi)
			width = self.sizes.area.width / self.sizes.number - self.sizes.padding
			radius = width / 2
			height = max(self.sizes.bar.height * min(self.config["draw"]["scale"] * value, 1), self.sizes.zero)/2
			height = height - 1.5

			# Dibujar rectángulo
			cr.rectangle(dx, center_y - height, width, height * 2)
			cr.arc(dx + radius, center_y - height, radius, 0, 2*pi)
			cr.arc(dx + radius, center_y + height, radius, 0, 2*pi)

			cr.close_path()

			dx += width + self.sizes.padding
		cr.fill()

	# noinspection PyUnusedLocal
	def size_update(self, *args):
		"""Update drawing geometry"""
		self.sizes.number = self.cavaconfig["general"]["bars"]
		self.sizes.padding = self.config["draw"]["padding"]
		self.sizes.zero = self.config["draw"]["zero"]

		self.sizes.area.width = self.area.get_allocated_width() - self.config["offset"]["right"]
		self.sizes.area.height = self.area.get_allocated_height() - self.config["offset"]["bottom"]

		tw = (self.sizes.area.width - self.config["offset"]["left"]) - self.sizes.padding * (self.sizes.number - 1)
		self.sizes.bar.width = max(int(tw / self.sizes.number), 1)
		self.sizes.bar.height = self.sizes.area.height - self.config["offset"]["top"]
		self.sizes.wcpi = tw % self.sizes.number  # width correction point index

	def color_update(self):
		"""Set drawing color according current settings"""
		self.color = self.config["color"]["autofg"] if self.config["color"]["auto"] else self.config["color"]["fg"]
