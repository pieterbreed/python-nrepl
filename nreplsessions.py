#! /usr/bin/env python
""" Deals with NREPL sessions and submitting instructions
to the repl given an abstract idea of how to communicate 
with such a NREPL"""

import unittest, logging

logger = logging.getLogger(__name__)

class Channel:
	def submit(self, data, session):
		"""Submits data to the channel.

		data => Standard python data structure, but probably a map.
		        An id will be assigned to this structure if it's not present
		session => A session object that will be called back with the result"""


		raise NotImplementedError()

class NREPLSession:
	def __init__(self, channel, sessionId, idGenerator):
		"""channel => instance implementing Channel
		sessionId => a unique id associated with this session, probably assigned by the nrepl
		idGenerater => an iterable that produces unique ids, in string type"""

		self._channel = channel
		self._sessionId = sessionId
		self._idGenerator = idGenerator

		self._callbacks = {}

	def resultsReceived(self, data):
		"""Called by the channel when data is received that belongs to this session"""

		logger.debug("Raw resultsReceived: {0}".format(data))
		
		dataId = data["id"]

		if not dataId in self._callbacks:
			return
		
		cb = self._callbacks[dataId]

		status = data["status"] if "status" in data else []

		if "done" in status:
			self._callbacks.pop(dataId)

		cb(data)


	def eval(self, lispCode, cb):
		"""evals lispcode in the nrepl, and calls cb with the result,
		possibly many times"""

		data = {
			"op": "eval",
			"session": self._sessionId,
			"code": lispCode,
			"id": self._idGenerator.next()
		}

		logger.debug("sending data structure to be evaled to channel: {0}".format(data))

		def interCb(receivedData):
			logger.debug("eval received response: {0}".format(receivedData))
			if 'value' in receivedData:
				cb(receivedData['value'])

		self._callbacks[data["id"]] = interCb
		self._channel.submit(data, self)


class FakeChannel(Channel):
	"""used in unit testing"""

	def __init__(self, cb):
		"""cb is invoked with the params of Channel.submit"""

		self._cb = cb

	def submit(self, data, session):
		self._cb(data, session)


class NREPLSessionTests(unittest.TestCase):
	def test_happy_cases(self):
		'''This tests that when a simple command is sent, it successfully 
		receives the result and removes the callbacks when status 'done'
		is received'''

		responses = []

		# fake responses in reverse order
		cbResponses = [
			{"value": "6"},
			{"value": "7"},
			{"status": ["done"]}
		]

		def channelCb(data, session):
			theId = data['id']
			for d in cbResponses:
				d['id'] = theId
				session.resultsReceived(d)

		channel = FakeChannel(channelCb) 
		session = NREPLSession(channel, "1", (str(i) for i in range(100)))
		session.eval("(+ 3 4)", lambda v: responses.append(v))

		self.assertEquals(2, len(responses))
		self.assertEquals("6", responses[0])
		self.assertEquals("7", responses[1])
		self.assertEquals(0, len(session._callbacks))



if __name__ == '__main__':
	logging.basicConfig(level=logging.DEBUG)
	logger.debug("starting unit tests")
	unittest.main()