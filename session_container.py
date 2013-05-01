#! /usr/bin/env python
# base interface for channel

import socket, Queue

class SessionContainer(object):
	'''a nrepl-aware container for logic dealing with nrepl sessions.

	probably requires some kind of transport for doing the actual communication'''

	def submit(self, data, session):
		"""Submits data to the channel. 

		data => Standard python data structure, but probably a map.
		session => A session object that will be called back with the result"""


		raise NotImplementedError()

