import unittest
import doctest


from pyjurer.session_container import SessionContainer
from pyjurer.funky_town import i_return_one

class Test(unittest.TestCase):
	# """Unit tests for SessionContainer"""

	# def test_doctests(self):
	# 	"""run doctests on SessionContainer"""
	# 	doctest.testmod(SessionContainer)

    def test_pieter_first_python_test(self):
        self.assertEqual(1, i_return_one())
