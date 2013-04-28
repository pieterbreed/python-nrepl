#! /usr/bin/env python
""" Deals with NREPL sessions and submitting instructions
to the repl given an abstract idea of how to communicate 
with such a NREPL"""

import unittest, logging, itertools

logger = logging.getLogger(__name__)

class Channel:
	def submit(self, data, session):
		"""Submits data to the channel.

		data => Standard python data structure, but probably a map.
		        An id will be assigned to this structure if it's not present
		session => A session object that will be called back with the result"""


		raise NotImplementedError()

class InterruptStatus:
	INTERRUPTED=1
	SESSION_IDLE=2
	INTERRUPT_ID_MISMATCH=3

	@staticmethod
	def has_string(s):
		return s in InterruptStatus._dict

	@staticmethod
	def from_string(s):
		return InterruptStatus._dict[s]

InterruptStatus._dict = {
			"interrupted": InterruptStatus.INTERRUPTED,
			"session-idle": InterruptStatus.SESSION_IDLE,
			"interrupt-id-mismatch": InterruptStatus.INTERRUPT_ID_MISMATCH
		}

class NREPLSession:


	def __init__(self, channel, sessionId, idGenerator):
		"""channel => instance implementing Channel
		sessionId => a unique id associated with this session, probably assigned by the nrepl
		idGenerater => an iterable that produces unique ids, in string type"""

		self._channel = channel
		self._sessionId = sessionId
		self._idGenerator = idGenerator

		self._idBasedCallbacks = {}
		self._closeCb = None
		self._sessionClosing = False

	
	def resultsReceived(self, data):
		"""Called by the channel when data is received that belongs to this session"""

		logger.debug("Raw results: {0}".format(data))

		status = data["status"] if "status" in data else []

		if "id" in data:
			dataId = data["id"]
			cb = self._idBasedCallbacks[dataId] if dataId in self._idBasedCallbacks else None
			if "done" in status:
				self._idBasedCallbacks.pop(dataId)
			if cb != None:
				cb(data)

		if "session-closed" in status:
			logger.debug("Received session-closed status")
			self._sessionClosing = True

		if self._sessionClosing and len(self._idBasedCallbacks) == 0 and self._closeCb != None:
			logger.debug("Calling close callback function")
			self._closeCb()



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

		self._idBasedCallbacks[data["id"]] = interCb
		self._channel.submit(data, self)

	def close(self, closeCb):
		"""closes a session, calls closeCb when complete"""

		data = {
			"op": "close",
			"session": self._sessionId,
			"id": self._idGenerator.next()
		}

		self._closeCb = closeCb
		self._channel.submit(data, self)

	def describe(self, dataCb):
		pass

	def interrupt(self, statusCb, interrupt_id=None):
		'''Interrupts a running request on the nrepl bound with the current session. Calls back 
		with the result of the operation, which will be an int corresponding to one of the values in InterruptStatus
		class.'''

		data = {
			"op": "interrupt",
			"session": self._sessionId,
			"id": self._idGenerator.next()
		}

		if interrupt_id != None:
			data["interrupt-id"] = interrupt_id

		logger.debug("Sending interrupt {0}".format(data))

		def dataCb(rdata):
			logger.debug("Received interrupt {0}".format(rdata))
			for s in rdata['status']:
				if InterruptStatus.has_string(s):
					statusCb(InterruptStatus.from_string(s))
					break


		self._idBasedCallbacks[data["id"]] = dataCb

		self._channel.submit(data, self)

	def clone(self, newSessionCb):
		'''clones a session, calls newSessionCb with a new session instance'''
		data = {
			"op": "clone",
			"session": self._sessionId,
			"id": self._idGenerator.next()
		}

		def dataReceivedCb(data):
			logger.debug('clone received data: {0}'.format(data))
			newSessionCb(NREPLSession(self._channel, data['new-session'], self._idGenerator))

		logger.debug("received request to clone session '{0}'".format(self._sessionId))

		self._idBasedCallbacks[data['id']] = dataReceivedCb
		self._channel.submit(data, self)

	def loadFile(self, fileContents, loadFileCb, fileName=None, filePath=None):
		'''loads the contents of a file into the session. optionally associates this
		with a name for the file and a relative path'''

		data = {
			"op": "load-file",
			"file": fileContents,
			"session": self._sessionId,
			"id": self._idGenerator.next()
		}

		if fileName != None:
			data['file-name'] = fileName

		if filePath != None:
			data['file-path'] = filePath

		logger.debug("request to load file '{0}'".format(data))

		def dataReceivedCb(data):
			loadFileCb()

		self._idBasedCallbacks[data['id']] = dataReceivedCb
		self._channel.submit(data, self)


class FakeListChannel(Channel):
	"""Channel that responds with a list of responses that are passed in as ctor arg"""

	def __init__(self, responses):
		self._responses = list(responses)
		self._responses.reverse()

	def processResult(self, session):
		if len(self._responses) == 0:
			raise Exception('not enough data')

		nextData = self._responses.pop()
		logger.debug("FaketListChannel: nextData = {0}".format(nextData))
		for d in nextData:
			session.resultsReceived(d)


	def submit(self, data, session):
		self.processResult(session)


class NREPLSessionTests(unittest.TestCase):

	def test_LoadFile(self):
		session = NREPLSession(FakeListChannel([
				[
					{"id": "0"}
				]
				]),
			"1",
			(str(i) for i in range(100)))

		def called():
			called.called = True
		called.called = False

		session.loadFile("this is the contents", called, "filename", "filepath")

		self.assertTrue(called.called)

	def test_happy_cases(self):
		'''This tests that when a simple command is sent, it successfully 
		receives the result and removes the callbacks when status 'done'
		is received'''

		# fake responses in reverse order
		cbResponses = [
			[
				{"value": "6", "id": "0"},
				{"value": "7", "id": "0"},
				{"status": ["done"], "id": "0"}
			]
		]
		channel = FakeListChannel(cbResponses)
		session = NREPLSession(channel, "1", (str(i) for i in range(100)))

		responses = []
		session.eval("(+ 3 4)", lambda v: responses.append(v))

		self.assertEquals(2, len(responses))
		self.assertEquals("6", responses[0])
		self.assertEquals("7", responses[1])
		self.assertEquals(0, len(session._idBasedCallbacks))

	def test_clone(self):
		'''this tests that a session can clone itself'''
		cbResponses = [
			[
				{"id": '1', "session": "1", "new-session": "2"}
			]
		]

		channel = FakeListChannel(cbResponses)
		session = NREPLSession(channel, '1', (str(i) for i in itertools.count(1)))

		def accept_clone(clonedSession):
			self.assertEquals('2', clonedSession._sessionId)
			accept_clone.called = True
		accept_clone.called = False

		session.clone(accept_clone)
		self.assertTrue(accept_clone.called)


	def test_interrupt(self):

		cbResponses = [
			[{"id": "1", "status": ["interrupted"]}],
			[{"id": "2", "status": ["session-idle"]}],
			[{"id": "3", "status": ["interrupt-id-mismatch"]}]
		]

		channel = FakeListChannel(cbResponses)
		session = NREPLSession(channel, '2', (str(i) for i in itertools.count(1)))

		statusii = iter([InterruptStatus.INTERRUPTED, InterruptStatus.SESSION_IDLE, InterruptStatus.INTERRUPT_ID_MISMATCH])

		def received(i):
			self.assertEquals(statusii.next(), i)
			received.called = received.called + 1
		received.called = 0

		session.interrupt(received)
		session.interrupt(received)
		session.interrupt(received)

		self.assertEquals(3, received.called)


	def test_closing(self):
		'''This tests that when a close is requested the close callbock will get fired'''

		cbResponses = [
			[],
			[],
			[
				{"status": ["session-closed"]},
				{"value": "7", "id": "0"},
				{"status": ["done"], "id": "0"}
			]
		]

		channel = FakeListChannel(cbResponses)
		session = NREPLSession(channel, "2", (str(i) for i in range(100)))

		def receivedValue(data):
			logger.debug("got data for request: {0}".format(data))
			receivedValue.received = True
		receivedValue.received = False

		session.eval("(+ 3 4)", receivedValue)

		def setClosed():
			logger.debug("Received session closed callback")
			setClosed.closed = True
		setClosed.closed = False
		session.close(setClosed)

		channel.processResult(session)

		self.assertEquals(True, setClosed.closed)
		self.assertEquals(True, receivedValue.received)


if __name__ == '__main__':
	logging.basicConfig(level=logging.DEBUG)
	logger.debug("starting unit tests")
	unittest.main()