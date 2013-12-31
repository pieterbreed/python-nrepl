# /usr/bin/env python

import unittest, threading, logging, queue, socket

TCP_CHANNEL_TIMEOUT = 1 # seconds, float value
TCP_READ_BUFFER_SIZE = 4098

def callbackThreadMain(receiveQueue, mustStopEvent, dataReceivedCallback):
	'''this method is responsible for callbacks for data received from the socket.
	It will read read data from receiveQueue and push it on via dataReceivedCallback(byte[])
	It will check the value of mustStopEvent and exit once it is signalled

	The onus is on dataReceivedCallback's implementation not to hang.
	'''

	logger = logging.getLogger(__name__ + 'callbackThreadMain')

	while not mustStopEvent.wait(0.5):
		logger.debug('iterating in callbackThreadMain')

		if receiveQueue.empty():
			logger.debug('receive queue is empty...')
			continue

		logger.debug('apparently, the receive queue is not empty')
		received = ''
		while not receiveQueue.empty():
			try:
				received = received + receiveQueue.get(False)
			except queue.Empty:
				pass
		logger.debug('calling the callback method with {0} bytes of data'.format(len(received)))
		dataReceivedCallback(received)


	logger.debug('stopping on callbackThreadMain')

def socketThreadMain(isocket, sendQueue, receiveQueue):
	'''this method will perform the communications with a socket-like object
	and perform sending and receiving of data via the passed Queues.

	isocket => an object supporting send(byte[]) : int, recv(int) : byte[] & close()

	sendQueue => a Queue object with which this thread is controlled

	SendQueue expects dicts for instructions:

	two types are supported: 
	Control message, deals with the state of the thread
	{
		"type": "control",
		"op": "stop" # only one supported
	}

	Messaging message, instructs the thread to send a message on the isocket:
	{
		"type": "message",
		"contents": string/bytes to be sent
	}

	receiveQueue => a queue containing raw bytes/string read from the isocket

	'''

	logger = logging.getLogger(__name__ + 'socketThreadMain')

	mustStop = False
	received = ''
	while not mustStop:
		logger.debug('iterating in thread main method')

		# sends everything that is in the send queue first
		hasStuffToSend = True
		while hasStuffToSend:
			logger.debug('looking for something to send...')
			try:
				stuffToSend = sendQueue.get_nowait() # raises queue.Empty if there is nothing to read
				logger.debug("found an instruction on the sendQueue '{0}'".format(
					stuffToSend))

				if stuffToSend['type'] == 'control':
					if stuffToSend['op'] == 'stop':
						logger.debug("received signal to stop the thread")
						mustStop = True
						break
				elif stuffToSend['type'] == 'message':
					messageContents = stuffToSend['contents']
					logger.debug(
						"Received something to send on the socket: '{0}'".format(
							messageContents))
					while len(messageContents) > 0:
						sent = isocket.send(bytes(messageContents, 'UTF-8'))
						messageContents = messageContents[sent:]
			except queue.Empty as e:
				logger.debug("nothing to send atm")
				hasStuffToSend = False

		# if we don't have anything else to send
		# and we did not get a request to stop then 
		# lets try reading for a while
		received = ''
		if not mustStop:
			logger.debug('looking to read something from the socket')
			moreToRead = True
			# try to read everything from the isocket
			# that we can read now without waiting to long for
			while moreToRead:
				try:
					received = received + isocket.recv(TCP_READ_BUFFER_SIZE).decode('UTF-8')
					logger.debug("Have something from the socket: '{0}'".format(
						received))
				except socket.timeout:
					logger.debug("isocket timed out waiting for incoming bytes")
					moreToRead = False

			if len(received) == 0:
				continue

			# we've received everything that we can right now
			# let's try sending it back
			try:
				receiveQueue.put_nowait(received)
				received = ''
			except queue.Full:
				# we can't send it back right now because the queue is full
				# we're not doing anything with this
				# since we can just put it next time round
				logger.debug("Can't place the received contents on the out queue because it's full")
				pass

	logger.debug("stopping the thread")
	isocket.close()

class Tcp:
	'''provides an abstraction over a tcp/ip connection'''

	def __init__(self, host, port, dataReceivedCallback=None):
		'''creates a new TcpChannel which can send and receive data
		to and from a tcp/ip socket.

		host => the hostname or address to connect to
		port => the port number to connect to on host'''

		self._logger = logging.getLogger(__name__ + '.Tcp_logger')
		self._socketSendQueue = queue.Queue()
		self._socketReceiveQueue = queue.Queue()

		self._host = host
		self._port = port

		self._callbacks = []
		if dataReceivedCallback != None:
			self.add_callback(dataReceivedCallback)

	def add_callback(self, callback):
		self._callbacks.append(callback)

	def callback_internal(self, bytes):
		map(lambda f: f(bytes), self._callbacks)

	def start(self):
		'''starts the socket and threads'''
		self._socket = socket.create_connection((self._host, self._port))
		self._socket.settimeout(0.5)
		
		self._socketThread = threading.Thread(target=socketThreadMain, args = (self._socket, self._socketSendQueue, self._socketReceiveQueue))
		self._socketThread.daemon = True
		self._socketThread.start();

		self._callbackMustStopvent = threading.Event()
		self._callbackThread = threading.Thread(target=callbackThreadMain, args = (self._socketReceiveQueue, self._callbackMustStopvent, self.callback_internal))
		self._callbackThread.daemon = True
		self._callbackThread.start();

	def stop(self):
		'''stops the tcp thread and the socket and waits for it to clean itself up'''
		self._logger.debug('stopping the Tcp')
		self._socketSendQueue.put(
			{
				'type': 'control', 
				'op': 'stop'
			})
		try:
			if self._socketThread.isAlive():
				self._logger.debug('waiting for the tcp thread to stop itself...')
				self._socketThread.join()
				self._logger.debug('tcp thread stopped :)')
			else:
				self._logger.warn('the socket thread was not alive anymore when the stop() method was called.')
		except:
			self._logger.warn('it looks like the socket was never started')

		try:
			if self._callbackThread.isAlive():
				self._logger.debug('waiting for the callback thread to stop')
				self._callbackMustStopvent.set()
				self._callbackThread.join()
			else:
				self._logger.warn('the callback thread was not alive anymore when the stop() method was called')
		except:
			self._logger.warn('it looks like the socket was never started')
		
		self._logger.debug('done stopping, all done.')

	def send(self, data, session=None):
		# self._sessions.add(session)
		self._socketSendQueue.put(
			{
				'type': 'message',
				'contents': data
			})


mockLogger = logging.getLogger(__name__ + 'mocks')

class MockSocket:

	def __init__(self, recvs):
		'''recvs => list of items. items must be either strings or the value True.
		When True is read, a queue.Empty will be raised

		sends => similarly a list of items. items must be strings or the Value True.
		When True is encountered, a queue.Empty is raised'''
		self._recvs = recvs
		self._sends = []
		self._closeCalled = False


	def send(self, bs):
		mockLogger.debug("Mock socket sending something: '{0}'".format(bs))
		self._sends.append(bs)
		return len(bs)

	def recv(self, i):
		if len(self._recvs) == 0:
			mockLogger.debug("MockSocket raising timeout")
			raise socket.timeout

		res = self._recvs.pop(0)

		if res == None:
			mockLogger.debug("MockSocket raising timeout")
			raise socket.timeout

		mockLogger.debug("Mocket socket recv'ing something: '{0}'".format(res))
		return res

	def close(self):
		self._closeCalled = True

class MockQueue:

	def __init__(self, gets, putsAllows):
		'''gets => a list of things that will be read. Must be either a None or 
		python item. For every None a queue.Empty will be raised

		putsAllows => an item corresponding to every puts invocation. True
		accepts the put and False raises an queue.Full'''
		self._gets = gets
		self._puts = []
		self._putsAllows = putsAllows

	def get_nowait(self):
		res = self._gets.pop(0)
		if res == None:
			mockLogger.debug('MockQueue raising queue.Empty')
			raise queue.Empty
		mockLogger.debug("MockQueue getting '{0}'".format(res))
		return res

	def put_nowait(self, received):
		allow = self._putsAllows.pop(0)
		if allow:
			mockLogger.debug("MockQueue putting: '{0}'".format(received))
			self._puts.append(received)
		else:
			mockLogger.debug("MockQueue refusing to put, raising queue.Full")
			raise queue.Full


class TcpTests(unittest.TestCase):
	def test_thread_read_1(self):
		socketReceives = ['1234']
		socket = MockSocket(socketReceives)

		sendQueue = MockQueue(
			[
				None,  
				{'type': 'message', 'contents': 'aoeu'},
				None,
				{'type': 'control', 'op': 'stop'}
			], 
			None)
		receiveQueue = MockQueue(None, [True])
		
		stoppedEvent = threading.Event()

		socketThreadMain(socket, sendQueue, receiveQueue, stoppedEvent)

		self.assertTrue(stoppedEvent.is_set())
		self.assertEquals('1234', receiveQueue._puts.pop())
		self.assertEquals(1, len(socket._sends))
		self.assertEquals('aoeu', socket._sends[0])




if __name__ == '__main__':
	logging.basicConfig(level=logging.DEBUG)
	unittest.main()











