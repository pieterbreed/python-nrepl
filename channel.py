#! /usr/bin/env python
# base interface for channel

class Channel(object):
	def submit(self, data, session):
		"""Submits data to the channel.

		data => Standard python data structure, but probably a map.
		session => A session object that will be called back with the result"""


		raise NotImplementedError()

class Transport(object):
	'''nrepl transport. the on-the-line encoding and decoding of the data that goes to
	and from the nrepl'''

	def __init__(self, receivedDataCb):
		'''creates a new transport. 

		receivedDataCb => callback function with one parameter that is a python
		data structure'''
		self._cb = receivedDataCb

	def send(self, data):
		'''sends data to the nrepl after it's been encoded'''

		raise NotImplementedError()

	def receive(self, raw):
		'''receives raw data from the channel. If onough data has been received
		that a complete python data structure can be assembled, the callback
		will be invoked'''

		raise NotImplementedError()

	def _receveidData(self, data):
		'''invoked when a full python data structure can be assembled from 
		the received bytes. Meant for invoking privately'''

		self._cb(data)