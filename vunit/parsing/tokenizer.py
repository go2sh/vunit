# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2015-2016, Lars Asplund lars.anders.asplund@gmail.com

"""
A general tokenizer
"""

import collections
import re
from vunit.ostools import read_file, file_exists

TokenType = collections.namedtuple("Token", ["kind", "value", "location"])


def Token(kind, value, location=None):  # pylint: disable=invalid-name
    return TokenType(kind, value, location)


def new_token_kind(name):
    """
    Create a new token kind with nice __repr__
    """
    cls = type(name, (object,), {"__repr__": lambda self: name})
    return cls()


class Tokenizer(object):
    """
    Maintain a prioritized list of token regex
    """

    def __init__(self):
        self._regexs = []
        self._assoc = {}
        self._regex = None

    def add(self, name, regex, func=None):
        """
        Add token type
        """
        key = chr(ord('a') + len(self._regexs))
        self._regexs.append((key, regex))
        kind = new_token_kind(name)
        self._assoc[key] = (kind, func)
        return kind

    def finalize(self):
        self._regex = re.compile("|".join("(?P<%s>%s)" % spec for spec in self._regexs), re.VERBOSE | re.MULTILINE)

    def tokenize(self, code, file_name=None, create_locations=False):
        """
        Tokenize the code
        """
        tokens = []
        start = 0
        while True:
            match = self._regex.search(code, pos=start)
            if match is None:
                break
            lexpos = (start, match.end() - 1)
            start = match.end()
            key = match.lastgroup
            kind, func = self._assoc[key]
            value = match.group(match.lastgroup)

            if create_locations:
                location = (file_name, lexpos)
            else:
                location = None

            token = Token(kind, value, location)
            if func is not None:
                token = func(token)

            if token is not None:
                tokens.append(token)
        return tokens


class TokenStream(object):
    """
    Helper class for traversing a stream of tokens
    """

    def __init__(self, tokens):
        self._tokens = tokens
        self._idx = 0

    def __len__(self):
        return len(self._tokens)

    def __getitem__(self, index):
        return self._tokens[index]

    @property
    def eof(self):
        return not self._idx < len(self._tokens)

    @property
    def idx(self):
        return self._idx

    @property
    def current(self):
        return self._tokens[self._idx]

    def peek(self, offset=0):
        return self._tokens[self._idx + offset]

    def skip_while(self, *kinds):
        """
        Skip forward while token kind is present
        """
        while not self.eof:
            if not any(self._tokens[self._idx].kind == kind for kind in kinds):
                break
            self._idx += 1
        return self._idx

    def skip_until(self, *kinds):
        """
        Skip forward until token kind is present
        """
        while not self.eof:
            if any(self._tokens[self._idx].kind == kind for kind in kinds):
                break
            self._idx += 1
        return self._idx

    def pop(self):
        """
        Return current token and advance stream
        """
        if self.eof:
            return None

        self._idx += 1
        return self._tokens[self._idx - 1]

    def slice(self, start, end):
        return self._tokens[start:end]


def describe_location(location):
    """
    Describe the location as a string
    """
    if location is None:
        return "Unknown location"

    file_name, (start, end) = location

    if not file_exists(file_name):
        return "Unknown location in %s" % file_name

    contents = read_file(file_name)

    retval = ""
    count = 0
    for lineno, line in enumerate(contents.splitlines()):
        lstart = count
        lend = lstart + len(line)
        if lstart <= start and start <= lend:
            retval = "from %s line %i:\n" % (file_name, lineno + 1)
            retval += line + "\n"
            retval += (" " * (start - lstart)) + ("~" * (min(lend - 1, end) - start + 1))
            return retval

        count = lend + 1
