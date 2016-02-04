# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this file,
# You can obtain one at http://mozilla.org/MPL/2.0/.
#
# Copyright (c) 2015, Lars Asplund lars.anders.asplund@gmail.com

# pylint: disable=too-many-public-methods

"""
Test of the Verilog preprocessor
"""

from os.path import join, dirname, exists
import os
from vunit.ostools import renew_path

from unittest import TestCase
from vunit.parsing.verilog.preprocess import preprocess, Macro
from vunit.parsing.verilog.tokenizer import tokenize
from vunit.test.mock_2or3 import mock


class TestVerilogPreprocessor(TestCase):
    """
    Test of the Verilog preprocessor
    """

    def setUp(self):
        self.output_path = join(dirname(__file__), "test_verilog_preprocessor_out")
        renew_path(self.output_path)

    def test_non_preprocess_tokens_are_kept(self):
        defines = {}
        tokens = tokenize('"hello"ident/*comment*///comment')
        pp_tokens = preprocess(tokenize('"hello"ident/*comment*///comment'), defines)
        self.assertEqual(pp_tokens, tokens)
        self.assertEqual(defines, {})

    def test_preprocess_define_without_value(self):
        defines = {}
        tokens = preprocess(tokenize("`define foo"), defines)
        self.assertEqual(tokens, [])
        self.assertEqual(defines, {"foo": Macro("foo")})

    @mock.patch("vunit.parsing.verilog.preprocess.LOGGER", autospec=True)
    def test_preprocess_broken_define(self, logger):
        defines = {}
        tokens = preprocess_loc("`define", defines)
        self.assertEqual(tokens, [])
        self.assertEqual(defines, {})
        logger.warning.assert_called_once_with(
            "Verilog `define without argument\n%s",
            "from fn.v line 1:\n"
            "`define\n"
            "~~~~~~~")

    @mock.patch("vunit.parsing.verilog.preprocess.LOGGER", autospec=True)
    def test_preprocess_broken_define_first_argument(self, logger):
        defines = {}
        tokens = preprocess_loc('`define "foo"', defines)
        self.assertEqual(tokens, [])
        self.assertEqual(defines, {})
        logger.warning.assert_called_once_with(
            "Verilog `define invalid name\n%s",
            "from fn.v line 1:\n"
            '`define "foo"\n'
            "        ~~~~~")

    def test_preprocess_broken_define_argument_list(self):
        defines = {}
        tokens = preprocess(tokenize('`define foo('), defines)
        self.assertEqual(tokens, [])
        self.assertEqual(defines, {})

        defines = {}
        tokens = preprocess(tokenize('`define foo(a'), defines)
        self.assertEqual(tokens, [])
        self.assertEqual(defines, {})

        defines = {}
        tokens = preprocess(tokenize('`define foo(a='), defines)
        self.assertEqual(tokens, [])
        self.assertEqual(defines, {})

        defines = {}
        tokens = preprocess(tokenize('`define foo(a=b'), defines)
        self.assertEqual(tokens, [])
        self.assertEqual(defines, {})

        defines = {}
        tokens = preprocess(tokenize('`define foo(a=)'), defines)
        self.assertEqual(tokens, [])
        self.assertEqual(defines, {})

        defines = {}
        tokens = preprocess(tokenize('`define foo("a"'), defines)
        self.assertEqual(tokens, [])
        self.assertEqual(defines, {})

        defines = {}
        tokens = preprocess(tokenize('`define foo("a"='), defines)
        self.assertEqual(tokens, [])
        self.assertEqual(defines, {})

    def test_preprocess_define_with_value(self):
        defines = {}
        tokens = preprocess(tokenize("`define foo bar \"abc\""), defines)
        self.assertEqual(tokens, [])
        self.assertEqual(defines, {"foo": Macro("foo", tokenize("bar \"abc\""))})

    def test_preprocess_define_with_lpar_value(self):
        defines = {}
        tokens = preprocess(tokenize("`define foo (bar)"), defines)
        self.assertEqual(tokens, [])
        self.assertEqual(defines, {"foo": Macro("foo", tokenize("(bar)"))})

    def test_preprocess_define_with_one_arg(self):
        defines = {}
        tokens = preprocess(tokenize("`define foo(arg)arg 123"), defines)
        self.assertEqual(tokens, [])
        self.assertEqual(defines,
                         {"foo": Macro("foo", tokenize("arg 123"), args=("arg",))})

    def test_preprocess_define_with_one_arg_ignores_initial_space(self):
        defines = {}
        tokens = preprocess(tokenize("`define foo(arg) arg 123"), defines)
        self.assertEqual(tokens, [])
        self.assertEqual(defines,
                         {"foo": Macro("foo", tokenize("arg 123"), args=("arg",))})

    def test_preprocess_define_with_multiple_args(self):
        defines = {}
        tokens = preprocess(tokenize("`define foo( arg1, arg2)arg1 arg2"), defines)
        self.assertEqual(tokens, [])
        self.assertEqual(defines,
                         {"foo": Macro("foo", tokenize("arg1 arg2"), args=("arg1", "arg2"))})

    def test_preprocess_define_with_default_values(self):
        defines = {}
        tokens = preprocess(tokenize("`define foo(arg1, arg2=default)arg1 arg2"), defines)
        self.assertEqual(tokens, [])
        self.assertEqual(defines,
                         {"foo": Macro("foo",
                                       tokenize("arg1 arg2"),
                                       args=("arg1", "arg2"),
                                       defaults={"arg2": tokenize("default")})})

    def test_preprocess_substitute_define_without_args(self):
        tokens = preprocess(tokenize("""\
`define foo bar \"abc\"
`foo"""))
        self.assertEqual(tokens, tokenize("bar \"abc\""))

    def test_preprocess_substitute_define_with_one_arg(self):
        tokens = preprocess(tokenize("""\
`define foo(arg)arg 123
`foo(hello hey)"""))
        self.assertEqual(tokens, tokenize("hello hey 123"))

    def test_preprocess_substitute_define_with_multile_args(self):
        tokens = preprocess(tokenize("""\
`define foo(arg1, arg2)arg1,arg2
`foo(1 2, hello)"""))
        self.assertEqual(tokens, tokenize("1 2, hello"))

    def test_preprocess_substitute_define_with_default_values(self):
        defines = {}
        tokens = preprocess(tokenize("""\
`define foo(arg1, arg2=default)arg1 arg2
`foo(1)"""), defines)
        self.assertEqual(tokens, tokenize("1 default"))

    def test_preprocess_substitute_define_broken_args(self):
        tokens = preprocess(tokenize("""\
`define foo(arg1, arg2)arg1,arg2
`foo(1 2)"""))
        self.assertEqual(tokens, tokenize(""))

        tokens = preprocess(tokenize("""\
`define foo(arg1, arg2)arg1,arg2
`foo"""))
        self.assertEqual(tokens, tokenize(""))

        tokens = preprocess(tokenize("""\
`define foo(arg1, arg2)arg1,arg2
`foo("""))
        self.assertEqual(tokens, tokenize(""))

        tokens = preprocess(tokenize("""\
`define foo(arg1, arg2)arg1,arg2
`foo(1"""))
        self.assertEqual(tokens, tokenize(""))

    def test_preprocess_include_directive(self):
        self.write_file("include.svh", "hello hey")
        included_files = []
        tokens = preprocess(tokenize('`include "include.svh"'),
                            include_paths=[self.output_path],
                            included_files=included_files)
        self.assertEqual(tokens, tokenize("hello hey"))
        self.assertEqual(included_files, [join(self.output_path, "include.svh")])

    def test_preprocess_include_directive_missing_file(self):
        included_files = []
        tokens = preprocess(tokenize('`include "missing.svh"'),
                            include_paths=[self.output_path],
                            included_files=included_files)
        self.assertEqual(tokens, tokenize(""))
        self.assertEqual(included_files, [])

    def test_preprocess_include_directive_missing_argument(self):
        included_files = []
        tokens = preprocess(tokenize('`include'),
                            include_paths=[self.output_path],
                            included_files=included_files)
        self.assertEqual(tokens, tokenize(""))
        self.assertEqual(included_files, [])

    def test_preprocess_include_directive_bad_argument_ignored(self):
        included_files = []
        self.write_file("include.svh", "hello hey")
        tokens = preprocess(tokenize('`include foo "include.svh"'),
                            include_paths=[self.output_path],
                            included_files=included_files)
        self.assertEqual(tokens, tokenize(' "include.svh"'))
        self.assertEqual(included_files, [])

    def test_preprocess_include_directive_from_define(self):
        included_files = []
        self.write_file("include.svh", "hello hey")
        tokens = preprocess(tokenize('''\
`define inc "include.svh"
`include `inc'''),
                            include_paths=[self.output_path],
                            included_files=included_files)
        self.assertEqual(tokens, tokenize('hello hey'))
        self.assertEqual(included_files, [join(self.output_path, "include.svh")])

    def test_preprocess_include_directive_from_define_with_args(self):
        included_files = []
        self.write_file("include.svh", "hello hey")
        tokens = preprocess(tokenize('''\
`define inc(a) a
`include `inc("include.svh")'''),
                            include_paths=[self.output_path],
                            included_files=included_files)
        self.assertEqual(tokens, tokenize('hello hey'))
        self.assertEqual(included_files, [join(self.output_path, "include.svh")])

    def test_preprocess_include_directive_from_define_broken(self):
        included_files = []
        tokens = preprocess(tokenize('''\
`define inc foo
`include `inc'''),
                            include_paths=[self.output_path],
                            included_files=included_files)
        self.assertEqual(tokens, tokenize(''))
        self.assertEqual(included_files, [])

    def write_file(self, file_name, contents):
        """
        Write file with contents into output path
        """
        full_name = join(self.output_path, file_name)
        full_path = dirname(full_name)
        if not exists(full_path):
            os.makedirs(dirname(full_path))
        with open(full_name, "w") as fptr:
            fptr.write(contents)


def preprocess_loc(code, defines, file_name="fn.v"):
    """
    Preprocess with location information
    """

    tokens = tokenize(code, file_name=file_name, create_locations=True)

    with mock.patch("vunit.parsing.tokenizer.read_file", autospec=True) as mock_read_file:
        with mock.patch("vunit.parsing.tokenizer.file_exists", autospec=True) as mock_file_exists:
            mock_file_exists.return_value = True
            mock_read_file.return_value = code
            tokens = preprocess(tokens, defines)
            mock_file_exists.assert_called_once_with(file_name)
            mock_read_file.assert_called_once_with(file_name)
            return tokens
