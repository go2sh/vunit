# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2015, Lars Asplund lars.anders.asplund@gmail.com

"""
Verilog parsing functionality
"""
from os.path import join, exists

from vunit.parsing.tokenizer import TokenStream, describe_location
import vunit.parsing.verilog.tokenizer as tokenizer
from vunit.parsing.verilog.tokenizer import tokenize
import logging
LOGGER = logging.getLogger(__name__)


def preprocess(tokens, defines=None, include_paths=None, included_files=None):
    """
    Pre-process tokens while filling in defines
    """
    stream = TokenStream(tokens)
    include_paths = [] if include_paths is None else include_paths
    included_files = [] if included_files is None else included_files
    defines = {} if defines is None else defines
    result = []

    while not stream.eof:
        token = stream.pop()
        if not token.kind == tokenizer.PREPROCESSOR:
            result.append(token)
            continue

        if token.value == "define":
            macro = define(token, stream)
            if macro is not None:
                defines[macro.name] = macro

        if token.value == "include":
            stream.skip_while(tokenizer.WHITESPACE)

            tok = stream.pop()
            if tok is None:
                LOGGER.debug("Broken `include eof reached")
                continue

            if tok.kind == tokenizer.PREPROCESSOR:
                if tok.value in defines:
                    macro = defines[tok.value]
                else:
                    LOGGER.debug("Broken `include has bad argument %r", tok)
                    continue

                expanded_tokens = macro.expand_from_stream(stream)

                if len(expanded_tokens) == 0:
                    LOGGER.debug("Broken `include has bad argument %r", tok)
                    continue

                if expanded_tokens[0].kind != tokenizer.STRING:
                    LOGGER.debug("Broken `include has bad argument %r", expanded_tokens[0])
                    continue

                file_name = expanded_tokens[0].value

            elif tok.kind == tokenizer.STRING:
                file_name = tok.value
            else:
                LOGGER.debug("Broken `include has bad argument %r", tok)
                continue

            full_name = None
            for include_path in include_paths:
                full_name = join(include_path, file_name)
                if exists(full_name):
                    break
            else:
                LOGGER.debug("Could not file verilog `include file %s",
                             file_name)
                continue
            included_files.append(full_name)
            with open(full_name, "r") as fptr:
                included_tokens = tokenize(fptr.read())
            result += preprocess(included_tokens, defines, include_paths, included_files)

        elif token.value in defines:
            macro = defines[token.value]
            result += macro.expand_from_stream(stream)

    return result


def define(define_token, stream):
    """
    Handle a `define directive
    """
    stream.skip_while(tokenizer.WHITESPACE)
    name_token = stream.pop()

    if name_token is None or (name_token.kind in (tokenizer.NEWLINE,)):
        LOGGER.warning("Verilog `define without argument\n%s",
                       describe_location(define_token.location))
        return None

    if name_token.kind != tokenizer.IDENTIFIER:
        LOGGER.warning("Verilog `define invalid name\n%s",
                       describe_location(name_token.location))
        return None

    name = name_token.value

    token = stream.pop()
    if token is None:
        # Empty define
        return Macro(name)

    if token.kind in (tokenizer.WHITESPACE, tokenizer.NEWLINE):
        # Define without arguments
        args = tuple()
        defaults = {}
    elif token.kind == tokenizer.LPAR:
        args = tuple()
        defaults = {}
        while token.kind != tokenizer.RPAR:
            if token.kind == tokenizer.IDENTIFIER:
                argname = token.value
                args = args + (argname,)
                token = stream.pop()
                if token is None:
                    LOGGER.debug("Broken verilog `define argument list")
                    return None
                elif token.kind == tokenizer.EQUAL:
                    token = stream.pop()
                    defaults[argname] = [token]
                    token = stream.pop()
            else:
                token = stream.pop()

            if token is None:
                LOGGER.debug("Broken verilog `define argument list")
                return None

    stream.skip_while(tokenizer.WHITESPACE)
    start = stream.idx
    end = stream.skip_until(tokenizer.NEWLINE)
    if not stream.eof:
        stream.pop()
    return Macro(name,
                 tokens=stream.slice(start, end),
                 args=args,
                 defaults=defaults)


class Macro(object):
    """
    A `define macro with zero or more arguments
    """

    def __init__(self, name, tokens=None, args=tuple(), defaults=None):
        self.name = name
        self.tokens = [] if tokens is None else tokens
        self.args = args
        self.defaults = {} if defaults is None else defaults

    @property
    def num_args(self):
        return len(self.args)

    def __repr__(self):
        return "Macro(%r, %r %r, %r)" % (self.name, self.tokens, self.args, self.defaults)

    def expand(self, values):
        """
        Expand macro with actual values, returns a list of expanded tokens
        """
        tokens = []
        for token in self.tokens:
            if token.kind == tokenizer.IDENTIFIER and token.value in self.args:
                idx = self.args.index(token.value)
                if idx >= len(values):
                    if token.value not in self.defaults:
                        LOGGER.debug("Broken verilog `define %s no default for %s",
                                     self.name,
                                     token.value)
                        return []
                    value = self.defaults[token.value]
                else:
                    value = values[idx]
                tokens += value
            else:
                tokens.append(token)
        return tokens

    def __eq__(self, other):
        return ((self.name == other.name) and
                (self.tokens == other.tokens) and
                (self.args == other.args) and
                (self.defaults == other.defaults))

    def expand_from_stream(self, stream):
        """
        Expand macro consuming arguments from the stream
        returns the expanded tokens
        """
        if self.num_args == 0:
            values = []
        else:
            values = self._parse_macro_actuals(stream)
            if values is None:
                return []
        return self.expand(values)

    @staticmethod
    def _parse_macro_actuals(stream):
        """
        Parse the actual values of macro call such as
        1 2 in `macro(1, 2)
        """
        token = stream.pop()
        if token is None:
            return None
        if token.kind != tokenizer.LPAR:
            return None
        token = stream.pop()
        if token is None:
            return None

        value = []
        values = []
        while token.kind != tokenizer.RPAR:
            if token.kind == tokenizer.COMMA:
                values.append(value)
                value = []
            else:
                value.append(token)
            token = stream.pop()
            if token is None:
                return None

        values.append(value)
        return values
