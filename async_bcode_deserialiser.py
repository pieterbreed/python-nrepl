#! /usr/bin/env python

# class to interpret unknown lengths of bencoded strings
# keeps remnants around until more data is received

import bcode
import unittest

class AsyncBCodeDeserialiser:


    def __init__(this):
        this._cb = []
        this._buffer = ''


    def register_cb(this, cb):
        this._cb.append(cb)


    def push_data(this, strData):
        this._buffer = this._buffer + strData
        this._perform_data_stitching()


    def _perform_data_stitching(this):
        while len(this._buffer) > 0:
            try:
                temp = bcode.bdecode(this._buffer)
            except ValueError:
                temp = None

            if temp == None:
                return
            temp_len = len(bcode.bencode(temp))
            this._buffer = this._buffer[temp_len:]
            map(lambda f: f(temp), this._cb)

class AsyncBCodeDeserialiserTest(unittest.TestCase):


    def setUp(self):        
        self.received_data = []
        self.ds = AsyncBCodeDeserialiser()
        self.ds.register_cb(self.data_received)


    def test_pushing_fragments(self):
        self.ds.push_data('4:ao')
        self.ds.push_data('oe')
        self.ds.push_data('5:3.uoe')
        self.ds.push_data('l4:aoeu3')
        self.ds.push_data(':oeue')

        self.assertEqual(['aooe', '3.uoe', ['aoeu', 'oeu']], self.received_data)
        

    def data_received(self, d):
        self.received_data.append(d)

if __name__ == '__main__':
    
    
    unittest.main()

