#! /usr/bin/env python
# beencoding implementation of the NREPL encoding concept

'''implements an NREPL transport using beencoding'''

from async_bcode_deserialiser import AsyncBCodeDeserialiser
from transport import Transport

import bcode, unittest, logging

class BCodeTransport(Transport):
	'''implements beencoding and bedecoding over channels that may
	send partial section of each data structure'''

	def __init__(self, sendBytes, receivedDataCb=None):
		'''initialises the transport

		sendBytes => method of one param, taking a byte[] which is used to send bytes
		receivedDataCb => method of one param, taking any python data when data is received'''

		self._callbacks = []
		if receivedDataCb != None:
			self._callbacks.append(receivedDataCb)

		self._bcode = AsyncBCodeDeserialiser()
		self._bcode.register_cb(self.receive_internal)
		self._sender = sendBytes

	def receive_internal(self, data):
		map(lambda f: f(data), this._callbacks)

	def send(self, data):
		'''sends the data encoded'''

		self._sender(bcode.bencode(data))

	def receive(self, raw):
		'''accepts raw data and determines when to invoke the callback when
		enough data has been received.

		raw => byte array'''

		self._bcode.push_data(raw)

class BCodeTransportUnitTests(unittest.TestCase):
	def test_sends(self):
		logger = logging.getLogger("{0}:BcodeTransportUnitTest:test_sends".format(__name__))

		def sendBytes(bs):
			logger.debug("sendBytes: {0}".format(bs))
			sendBytes.received.append(bs)
		sendBytes.received = []

		def receivedData(data):
			receivedData.data.append(data)
		receivedData.data = []

		t = BCodeTransport(sendBytes, receivedData)
		t.send(4)
		t.send(['1','2','3','4'])

		self.assertEquals(0, len(receivedData.data))
		self.assertEquals(bcode.bencode(4), sendBytes.received[0])
		self.assertEquals(bcode.bencode(['1','2','3','4']), sendBytes.received[1])

	def test_receives(self):
		logger = logging.getLogger("{0}:BcodeTransportUnitTest:test_receives".format(__name__))

		def sendBytes(bs):
			logger.debug("sendBytes: {0}".format(bs))
			sendBytes.received.append(bs)
		sendBytes.received = []

		def receivedData(data):
			receivedData.data.append(data)
		receivedData.data = []

		t = BCodeTransport(sendBytes, receivedData)
		t.receive('12:aoeuaoeuaoeu')
		t.receive('12:aoeua')
		t.receive('oeuaoeu')

		self.assertEquals(0, len(sendBytes.received))

		self.assertEquals(2, len(receivedData.data))
		self.assertEquals('aoeuaoeuaoeu', receivedData.data[0])
		self.assertEquals('aoeuaoeuaoeu', receivedData.data[1])


if __name__ == '__main__':
	logging.basicConfig(level=logging.DEBUG)
	unittest.main()



