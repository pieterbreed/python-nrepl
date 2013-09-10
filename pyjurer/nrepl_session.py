#! /usr/bin/env python
""" Deals with NREPL sessions and submitting instructions
to the repl given an abstract idea of how to communicate 
with such a NREPL"""

from __future__ import nested_scopes

import unittest, logging, itertools, threading, collections

logger = logging.getLogger(__name__)

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

class _CallbackHandler:
    '''in internal class for communicating callback handlers'''

    def __init__(self, session):
        self._registerDeque = collections.deque()
        self._idCallbacks = {}
        self._session = session

    def register(self, item):
        '''registers a bunch of callbacks associated with an id.

        :param item: a map containing at least an 'id' which will be
        corresponded with the 'id' in a nrepl result data structure. 
        then also members called 'out' and 'value' which will be
        invoked when that id receives either stdout or a value from
        the nrepl
        '''

        # we are hooking in ourselves to the status
        # of 'done' after which we take the id out
        # but we have to make sure that if there is 
        # a registered listener against 'done' that
        # it will be invoked too.
        closeCb = lambda s: self._done(s, item['id'])

        if 'status' not in item:
            item['status'] = {'done': closeCb}
        elif 'done' not in item['status']:
            item['status']['done'] = closeCb
        else:
            oldDone = item['status']['done']
            def newDone(s):
                oldDone(s)
                closeCb(s)
            item['status']['done'] = newDone

        self._registerDeque.appendleft(item)

    def _done(self, session, id_):
        logger.debug('status is done for id {0}'.format(id_))
        self._idCallbacks.pop(id_)

    def _read_registerQueue(self):
        '''reads out all callbacks sent from the invoking threading
        before trying to handle any callbacks for results'''
        while True:
            try:
                item = self._registerDeque.pop()
                self._idCallbacks[item['id']] = item
            except IndexError:
                break

    def accept_data(self, data):
        self._read_registerQueue()

        id_ = data['id']
        if not id_ in self._idCallbacks:
            raise IndexError('{0} not registered as a session id'.format(id_))

        cbitem = self._idCallbacks[id_]
        for op in cbitem.keys():
            # 'id' and 'status' is special
            # 'id' because it is a value and not a callback
            # and 'status' because it's a list of callbacks
            # instead of a single callback
            if op == "id" or op == "status":
                continue

            # anything else is assumed to be a function
            # that takes two values, the session
            # and the value in the data dict
            if op in data:
                cbitem[op](self._session, data[op])

        # the status callbacks only take the session
        datastatus = data["status"] if "status" in data else []
        for s in datastatus:
            if s in cbitem['status']:
                cbitem['status'][s](self._session)

class NREPLSession:


    def __init__(self, channel, sessionId, idGenerator):
        """channel => instance implementing Channel
        sessionId => a unique id associated with this session, probably assigned by the nrepl
        idGenerater => an iterable that produces unique ids, in string type"""

        self._channel = channel
        self._sessionId = sessionId
        self._idGenerator = idGenerator

        self._closeCb = None
        self._sessionClosing = False

        self._callbacks = _CallbackHandler(self)

    def _stdout(self, session, output):
        logger.info('received stdout: {0}'.format(output))

    def _receive_results(self, data):
        """Called by the channel when data is received that belongs to this session"""

        logger.debug("Raw results: {0}".format(data))
        self._callbacks.accept_data(data)

    def eval(self, lispCode, valueCb=None):
        """evals lispcode in the nrepl, and calls valueCb with the session and the result,
        possibly many times"""

        data = {
            "op": "eval",
            "session": self._sessionId,
            "code": lispCode,
            "id": self._idGenerator.next()
        }

        callbackItem = {
            'id': data['id'],
            'value': valueCb,
            'out': self._stdout
        }

        logger.debug("sending data structure to be evaled to channel: {0}".format(data))

        self._callbacks.register(callbackItem)
        self._channel._submit(data)

    def close(self, closeCb):
        """closes a session, calls closeCb when complete"""

        data = {
            "op": "close",
            "session": self._sessionId,
            "id": self._idGenerator.next()
        }

        callbackItem = {
            'id': data['id'],
            'out': self._stdout,
            'status': {'session-closed': closeCb}
        }

        self._callbacks.register(callbackItem)
        self._channel._submit(data)

    def describe(self, dataCb):
        data = {
            "op": "describe",
            "session": self._sessionId,
            "id": self._idGenerator.next()
        }

        result = {}
        def addData(k, v):
            result[k] = v

        callbackItem = {
            'id': data['id'],
            'out': self._stdout,
            'versions': lambda s, v: addData('versions', v),
            'ops': lambda s, v: addData('ops', v.keys()),
            'status': {'done': lambda s: dataCb(s, result)}
        }

        self._callbacks.register(callbackItem)
        self._channel._submit(data)

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

        self._channel._submit(data)

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
        self._channel._submit(data)

    def load_file(self, fileContents, valueCb=None, doneCb=None, fileName=None, filePath=None):
        '''loads the contents of a file into the session. optionally associates this
        with a name for the file and a relative path. Calls back with the value

        :param fileContents: the raw string that makes up the file's contents
        :type fileContents: string
        :param valueCb: optional callback, taking the session and the value that the file produced after it was eval'd.
        :param doneCb: optional callback, taking the session and indicating when the operation is complete
        :param fileName: optional, the name of the file
        :type fileName: string
        :param filePath: optional, the relative path to the file
        :type filePath: string

        '''

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

        callbackItem = {
            'id': data['id'],
            'out': self._stdout
        }

        if not doneCb is None:
            callbackItem['status'] = {'done': doneCb}

        if not valueCb is None:
            callbackItem['value'] = valueCb

        self._callbacks.register(callbackItem)
        self._channel._submit(data)

    def loadStdIn(self, contents, needInputCb):
        '''adds the contents of 'contents' to stdin on the nrepl session.
        needInputCb will be called if more data is required to satisfy a read
        operation on the session'''

        data = {
            "op": "stdin",
            "stdin": contents,
            "session": self._sessionId,
            "id": self._idGenerator.next()
        }

        logger.debug("request to add contents to stdin")

        def callback(data):
            logger.debug("callback for stdin '{0}'".format(data))
            if 'status' in data and 'need-input' in data['status']:
                needInputCb()

        self._idBasedCallbacks[data['id']] = callback
        self._channel._submit(data)


class FakeListChannel(object):
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
            session._receive_results(d)


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