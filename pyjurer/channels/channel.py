#! /usr/bin/env python
# defines the channel interface

class Channel(object):
	'''A channel is a convenience container for the communication between the python objects that
	expresses clojure concepts in python data structures and communication with an actual nrepl
	instance. An example of an actual Channel would be bencoding-over-tcp'''

	def submit(self, data, session):
		'''accepts python code in data and associated with session. When the response from
		the submission of data is received, the resultsReceived(data) on the session would
		be invoked'''
		raise NotImplementedError()


