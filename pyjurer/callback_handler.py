#! /usr/bin/env python
"""internal utility class that knows how to associate data returned from the channel with callbacks registered before"""

import collections

class _CallbackHandler:
    '''in internal class for communicating callback handlers'''

    def __init__(self, session_factory, initial_session_callback):
        self._registerDeque = collections.deque()
        self._idCallbacks = {}
        self._session_factory = session_factory
        self._initial_session_callback = initial_session_callback
        self.accept_data = self._initial_accept_data

    def register(self, session_id, id_, item):
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
        closeCb = lambda _, __: self._done(session_id, id_)

        if 'status' not in item:
            item['status'] = {'done': closeCb}
        elif 'done' not in item['status']:
            item['status']['done'] = closeCb
        else:
            oldDone = item['status']['done']
            def newDone(s, id_):
                oldDone(s, id_)
                closeCb(s, id_)
            item['status']['done'] = newDone

        self._registerDeque.appendleft({'session-id': session_id, 'id': id_, 'callbacks': item})

    def _done(self, session_id, id_):
        logger.debug('status is done for id {0} and session-id {1}'.format(id_, session_id))
        self._idCallbacks[session_id].pop(id_)

    def _read_registerQueue(self):
        '''reads out all callbacks sent from the invoking threading
        before trying to handle any callbacks for results'''
        while True:
            try:
                item = self._registerDeque.pop()
                session_id = item['session-id']
                id_ = item['id']
                callbacks = item['callbacks']

                if not session_id in self._idCallbacks:
                    self._idCallbacks[session_id] = {}
                self._idCallbacks[session_id][id_] = callbacks
            except IndexError:
                break

    def _initial_accept_data(self, data):
        id_ = data['id']
        session_id = data['session']

        if self._initial_session_callback is None:
            raise AssertionError('this can only be invoked the first time for accepted data')

        self._initial_session_callback(self._session_factory(session_id), data)
        self._initial_session_callback = None

        # change future invocations of self.accept_data to go somewhere else
        self.accept_data = self._subsequent_accept_data

    def _subsequent_accept_data(self, data):
        id_ = data['id']
        session_id = data['session']

        self._read_registerQueue()

        if not session_id in self._idCallbacks:
            raise IndexError('session {0} not registered'.format(session_id))

        if not id_ in self._idCallbacks[session_id]:
            raise IndexError('{0} not registered as an id in the session {1}'.format(id_, session_id))

        cbitem = self._idCallbacks[session_id, id_]
        for op in cbitem.keys():
            # 'status' is special because it's a list of callbacks
            # instead of a single callback
            if op == "status":
                continue

            # anything else is assumed to be a function
            # that takes three values, the session, the id 
            # and the value in the data dict
            if op in data:
                cbitem[op](self._session_factory(session_id), id_, data[op])

        # the status callbacks only take the session and the id
        datastatus = data["status"] if "status" in data else []
        for s in datastatus:
            if s in cbitem['status']:
                cbitem['status'][s](self._session_factory(session_id), id_)