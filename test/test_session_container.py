import unittest
import doctest


from pyjurer.session_container import SessionContainer


class Test(unittest.TestCase):
	"""Unit tests for SessionContainer"""

	def test_doctests(self):
		"""run doctests on SessionContainer"""
		doctest.testmod(SessionContainer)


if __name__ == "__main__":
	unittest.main()
