import argparse
import json
import shlex
import sys
import unittest


def create_parser(json_specs):
    """
    Create an ArgumentParser with the desired arguments.

    Returns:
        argparse.ArgumentParser: Configured argument parser.
    """
    specs = json.loads(json_specs)
    parser = argparse.ArgumentParser(**specs['parser'])
    if 'subparser' in specs:
        if specs['subparser'] is not None:
            parser.add_subparsers(**specs['subparser'])
    return parser


def create_parser_arguments(parser, json_specs):
    """
    Create an ArgumentParser based on the provided JSON specifications.

    Args:
        parser (argparse.ArgumentParser): parser to add the arguments to.
        json_specs (str): JSON string containing the argument specifications.

    Returns:
        argparse.ArgumentParser: Configured argument parser.
    """
    specs = json.loads(json_specs)

    for arg_spec in specs:
        # print(f"{arg_spec = }")
        # Add the argument to the parser
        print(f"{arg_spec['args'] = }")
        parser.add_argument(*arg_spec['args'], **arg_spec['kwargs'])
    return parser


def create_subparser(parser, json_specs):
    """
    Create an ArgumentParser with the desired arguments.

    Returns:
        argparse.ArgumentParser: Configured argument parser.
    """
    specs = json.loads(json_specs)
    subparser = parser.add_subparsers(**specs)
    print(f"{subparser = }")
    return subparser


def main():
    # Example JSON specifications
    json_argument_specs = """
    [
        {"name": "input_file", "help": "Path to the input file"},
        {"name": "-o", "help": "Path to the output file"},
        {"name": "--verbose", "help": "Enable verbose mode", "action": "store_true"}
    ]
    """

    # Create the parser using the JSON specifications
    parser = create_parser_arguments(json_argument_specs)

    # Parse the command-line arguments
    args = parser.parse_args()

    # Access the values
    input_file = args.input_file
    output_file = args.o
    verbose = args.verbose

    # Your script logic here
    print(f"Input file: {input_file}")
    print(f"Output file: {output_file}")
    print(f"Verbose mode: {verbose}")


if __name__ == '__main__':
    main()


# unittests
class Tests(unittest.TestCase):
    def test_create_parser(self):
        """
        Test the example provided in the question.
        """
        json_specs = """
        {
            "prog": "test",
            "description": "Custom script with dynamic arguments"
        }
        """
        parser = create_parser(json_specs)
        print(parser)
        args = parser.parse_args()
        self.assertIsInstance(args, argparse.Namespace)

    def test_create_parser_arguments(self):
        """
        Test the example provided in the question.
        """
        # todo: there will have to be a way to prevent the wrong arguments from being passed; perhaps a schema enforced?
        parser_specs = """
        {
            "prog": "test",
            "description": "Custom script with dynamic arguments"
        }
        """
        json_specs = """
        [
            {"args": ["input_file"], "kwargs": {"help": "Path to the input file"}},
            {"args": ["-o"], "kwargs": {"help": "Path to the output file"}},
            {"args": ["--verbose"], "kwargs": {"help": "Enable verbose mode", "action": "store_true"}}
        ]
        """
        sys.argv = shlex.split('script.py input.txt -o output.txt --verbose')
        parser = create_parser(parser_specs)
        parser = create_parser_arguments(parser, json_specs)
        print(parser)
        args = parser.parse_args()
        self.assertIsInstance(args, argparse.Namespace)
        self.assertEqual(args.input_file, 'input.txt')
        self.assertEqual(args.o, 'output.txt')
        self.assertTrue(args.verbose)

    def test_create_subparser(self):
        """
        Test the example provided in the question.
        """
        parser_specs = """
        {
            "parser": {
                "prog": "test",
                "description": "Custom script with dynamic arguments",
                "add_help": true
            },
            "subparser": {
                "title": "subcommands",
                "description": "valid subcommands",
                "dest": "subcommand",
                "required": true
            }
        }
        """
        parser = create_parser(parser_specs)
        print(f"{parser._subparsers = }")
        self.assertIsInstance(parser, argparse.ArgumentParser)
        self.assertIsNotNone(parser._subparsers)
