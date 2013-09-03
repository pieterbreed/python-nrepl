# /usr/bin/env python


class Transport(object):
	'''nrepl transport. the on-the-line encoding and decoding of the data that goes to
	and from the nrepl'''

	def send(self, data):
		'''sends data to the nrepl after it's been encoded'''

		raise NotImplementedError()

	def receive(self, raw):
		'''accepts raw data from the channel. If enough data has been received
		that a complete python data structure can be assembled, the callback
		will be invoked'''

		raise NotImplementedError()