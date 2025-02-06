# -*- Mode: Python; indent-tabs-mode: t; python-indent: 4; tab-width: 4 -*-
from gi.repository import Gtk, Gdk
from math import pi

class AttributeDict(dict):
	"""Dictionary with keys as attributes. Does nothing but easy reading"""
	def __getattr__(self, attr):
		return self[attr]

	def __setattr__(self, attr, value):
		self[attr] = value

class Spectrum:
	"""Spectrum drawing"""
	def __init__(self):
		self.silence_value = 0
		self.audio_sample = []
		self.color = None

		self.area = Gtk.DrawingArea()
		self.area.connect("draw", self.redraw)
		self.area.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)

		self.sizes = AttributeDict()
		self.sizes.area = AttributeDict()
		self.sizes.bar = AttributeDict()

		self.silence = 10
		self.max_height = 12

		self.area.connect("configure-event", self.size_update)
		self.color_update()

	def is_silence(self, value):
		"""Check if volume level critically low during last iterations"""
		self.silence_value = 0 if value > 0 else self.silence_value + 1
		return self.silence_value > self.silence

	def update(self, data):
		"""Audio data processing"""
		self.audio_sample = data
		if not self.is_silence(self.audio_sample[0]):
			self.area.queue_draw()
		elif self.silence_value == (self.silence + 1):
			self.audio_sample = [0] * self.sizes.number
			self.area.queue_draw()

	# noinspection PyUnusedLocal
	def redraw(self, widget, cr):
		"""Draw spectrum graph"""
		cr.set_source_rgba(*self.color)
		#cr.set_source_rgba(170/255, 170/255, 1, 1)

		dx = 3

		center_y = self.sizes.area.height / 2  # Centro vertical del área de dibujo
		for i, value in enumerate(self.audio_sample):

			#width = self.sizes.bar.width + int(i < self.sizes.wcpi)
			width = self.sizes.area.width / self.sizes.number - self.sizes.padding 
			radius = width / 2
			height = max(self.sizes.bar.height * min(value, 1), self.sizes.zero)/2
			if height == self.sizes.zero/2 + 1:
				height *= 0.5

			height = min(height, self.max_height)

			# Dibujar rectángulo
			cr.rectangle(dx, center_y - height, width, height * 2)
			#cr.rectangle(0, center_y, self.sizes.area.width, 20)
			cr.arc(dx + radius, center_y - height, radius, 0, 2*pi)
			cr.arc(dx + radius, center_y + height, radius, 0, 2*pi)

			cr.close_path()

			dx += width + self.sizes.padding
		cr.fill()

	# noinspection PyUnusedLocal
	def size_update(self, *args):
		"""Update drawing geometry"""
		self.sizes.number = 20
		self.sizes.padding = 5
		self.sizes.zero = 2

		self.sizes.area.width = self.area.get_allocated_width() 
		self.sizes.area.height = self.area.get_allocated_height() - 2

		tw = self.sizes.area.width - self.sizes.padding * (self.sizes.number - 1)
		self.sizes.bar.width = max(int(tw / self.sizes.number), 1)
		self.sizes.bar.height = self.sizes.area.height
		#self.sizes.wcpi = tw % self.sizes.number  # width correction point index

	def color_update(self):
		"""Set drawing color according current settings"""
		self.color = Gdk.RGBA(red=0.619608, green=0.792157, blue=0.988235, alpha=1.000000)
