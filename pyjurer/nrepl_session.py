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

    def _generic_command(
        self, optype, 
        extraRequest=None, 
        extraResponse=None,
        extraStatus=None,
        value=None, stdout=None, stdin=None, 
        done=None, closed=None):
        '''internal method for constructing a data structure to be sent to the nrepl'''

        data = {
            "op": optype,
            "session": self._sessionId,
            "id": self._idGenerator.next()
        }

        if not extraRequest is None:
            for k in extraRequest.keys():
                data[k] = extraRequest[k]

        callbackItem = {
            'id': data['id'],
            'status': {}
        }

        if not extraResponse is None:
            for k in extraResponse.keys():
                callbackItem[k] = extraResponse[k]

        if not value is None:
            callbackItem['value'] = value

        if not stdout is None:
            callbackItem['out'] = stdout

        if not stdin is None:
            callbackItem['status']['need-input'] = stdin

        if not done is None:
            callbackItem['status']['done'] = done

        if not closed is None:
            callbackItem['status']['session-closed'] = closed

        if not extraStatus is None:
            for s in extraStatus.keys():
                callbackItem['status'][s] = extraStatus[s]

        logger.debug("sending data structure to channel: {0}".format(data))

        self._callbacks.register(callbackItem)
        self._channel._submit(data)

        return data['id']

    def eval(self, lispCode, value=None, stdout=None, stdin=None, done=None):
        """evals lispcode in the nrepl, and calls value callback with the session and the result

        :param lispCode: the actual code that will be eval'd
        :type lispCode: string
        :param value: callback invoked with the session and with the value of the eval
        :type value: function, taking two arguments, the first a session the second a python data structure
        :param stdout: callback invoked with the stdout contents
        :type stdout: function taking two parameters, the first is the session and the second is the string that makes up the stdout
        :param stdin: callback invoked when content is required for stdin. With default value of None, the session will be notified that no more input from stdin is available
        :type stdin: function, taking one parameter, the session
        :param done: callback invoked when the session is finished processing this eval.
        :type done: function, taking one argument, the session

        """

        return self._generic_command(
            "eval", 
            extraRequest={"code": lispCode}, 
            value=value, stdout=stdout, stdin=stdin, done=done)

    def close(self, closed=None):
        """closes a session, calls closed when complete"""

        return self._generic_command(
            "close", 
            closed=closed)

    def describe(self, described):
        '''asks the nrepl to decribe itself, reporting version information and operational capability

        :param described: function callback, taking the session and a python map containing keys for 'versions' and 'ops'
        '''

        result = {}
        def addData(k, v):
            result[k] = v

        return self._generic_command(
            "describe", 
            extraResponse={
                'versions': lambda s, v: addData('versions', v),
                'ops': lambda s, v: addData('ops', v.keys()),
            },
            done=lambda s: described(s, result))

    def interrupt(self, interrupt_id=None, result=None, done=None):
        '''Interrupts a running request on the nrepl bound with the current session. Calls back on result
        with the result of the operation, which will be an int corresponding to one of the values in InterruptStatus
        class.

        :param interrupt_id: the id of the original request
        :type interrupt_id: int
        :param result: the callback, a function taking two arguments, the session and an INT defined in InterruptStatus
        :type result: a function
        :param done: a function, taking one argument, the session, when this command is completed

        '''

        extraRequest = None
        if not interrupt_id is None:
        	extraRequest['interrupt-id'] = interrupt_id

        extraStatus = {}
        for k in InterruptStatus._dict.keys():
        	extraStatus[k] = lambda s: result(s, InterruptStatus.from_string(k))

        return _generic_command(
	        self, "interrupt", 
	        extraRequest=extraRequest,
	        extraStatus=extraStatus
	        done=None)

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

    def load_file(self, fileContents,
        fileName=None, filePath=None,
        value=None, stdout=None, stdin=None, done=None):
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

        extra = {
            'file': fileContents
        }

        if not fileName is None:
            extra['file-name'] = fileName

        if not filePath is None:
            extra['file-path'] = filePath

        self._generic_command(
            "load-file",
            extraRequest=extra,
            value=value, stdout=stdout, stdin=stdin, done=done):

    def loadStdIn(self, contents, stdin=None, done=None):
        '''adds the contents of 'contents' to stdin on the nrepl session.
        needInputCb will be called if more data is required to satisfy a read
        operation on the session'''

        self._generic_command(
            "stdin", 
            extraRequest={"stdin": contents},
            stdin=stdin, done=done)

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