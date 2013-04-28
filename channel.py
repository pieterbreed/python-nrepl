#! /usr/bin/env python
# base interface for channel

class Channel:
	def submit(self, data, session):
		"""Submits data to the channel.

		data => Standard python data structure, but probably a map.
		session => A session object that will be called back with the result"""


		raise NotImplementedError()
