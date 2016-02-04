# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2016, Lars Asplund lars.anders.asplund@gmail.com

"""
Test of the general tokenizer
"""

from unittest import TestCase
from vunit.parsing.tokenizer import describe_location
from vunit.test.mock_2or3 import mock


class TestTokenizer(TestCase):
    """
    Test of the general tokenizer
    """

    def test_describes_single_char_location(self):
        self.assertEqual(
            _describe_location("""\
S
"""), """\
from filename line 1:
S
~""")

    def test_describes_single_char_location_within(self):
        self.assertEqual(
            _describe_location("""\
  S
"""), """\
from filename line 1:
  S
  ~""")

    def test_describes_multi_char_location(self):
        self.assertEqual(
            _describe_location("""\
S E
"""), """\
from filename line 1:
S E
~~~""")

    def test_describes_multi_char_location_within(self):
        self.assertEqual(
            _describe_location("""\
  S E
"""), """\
from filename line 1:
  S E
  ~~~""")

    def test_describes_multi_line_location(self):
        self.assertEqual(
            _describe_location("""\
  S____
 E
"""), """\
from filename line 1:
  S____
  ~~~~~""")


def _describe_location(code, file_name="filename"):
    """
    Helper to test describe_location
    """
    start = code.index("S")

    if "E" in code:
        end = code.index("E")
    else:
        end = start

    with mock.patch("vunit.parsing.tokenizer.read_file", autospec=True) as mock_read_file:
        with mock.patch("vunit.parsing.tokenizer.file_exists", autospec=True) as mock_file_exists:
            mock_file_exists.return_value = True
            mock_read_file.return_value = code
            retval = describe_location(location=(file_name, (start, end)))
            mock_file_exists.assert_called_once_with(file_name)
            mock_read_file.assert_called_once_with(file_name)
            return retval
