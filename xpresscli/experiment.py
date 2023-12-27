import argparse
import importlib
import inspect
import json
import shlex
import sys
import unittest


class CLIParser(argparse.ArgumentParser):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subparsers = None
        self.manager = None


def create_parser(json_specs):
    """
    Create an ArgumentParser with the desired arguments.

    Returns:
        CLIParser: Configured argument parser.
    """
    specs = json.loads(json_specs)
    parser = CLIParser(**specs['parser'])
    if 'subparser' in specs:
        if specs['subparser'] is not None:
            parser.subparsers = parser.add_subparsers(**specs['subparser'])
            # process options
            if not specs['subparser']['required']:
                parser = create_parser_arguments(parser, specs['options'])
            else:
                if 'options' in specs:
                    print(f"warning: options ignored for required subparser", file=sys.stderr)
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
    if isinstance(json_specs, str):
        specs = json.loads(json_specs)
    elif isinstance(json_specs, list):
        specs = json_specs
    else:
        raise TypeError(f"json_specs must be a string or list, not {type(json_specs)}")

    for arg_spec in specs:
        # Add the argument to the parser
        flag = arg_spec.pop('flag')
        parser.add_argument(*flag, **arg_spec)
    return parser


def create_commands(parser, json_specs):
    """
    Create a command for a subparser.

    Args:
        parser (CLIParser): parser to add the arguments to.
        json_specs (str): JSON string containing the argument specifications.

    Returns:
        CLIParser: Configured argument parser.
    """
    assert parser.subparsers is not None, "Parser must have subparsers"
    specs = json.loads(json_specs)

    # we have to think of a manager as a diction of commands to callables
    # the only problem with a plain dict is that we can't do any validation
    managers = dict()
    for command_spec in specs['commands']:
        # Create the subparser
        options = command_spec.pop('options')
        manager_string = command_spec.pop('manager', None)
        managers[command_spec['name']] = Manager(manager_string)
        command_parser = parser.subparsers.add_parser(**command_spec)

        create_parser_arguments(command_parser, options)

    return managers


def command_manager(args: argparse.Namespace) -> int:
    """The manager for the 'command' command."""
    print(f"{args = }")
    return 0


def command2_manager(args: argparse.Namespace) -> int:
    """The manager for the 'command' command."""
    print(f"{args = }")
    return 0


class Manager:
    def __init__(self, manager_string):
        self._manager_string = manager_string
        self._module, self._function = self._partition_manager()

    @property
    def module(self):
        return importlib.import_module(self._module)

    @property
    def function(self):
        return getattr(self.module, self._function)

    def _partition_manager(self):
        """Partition the manager string into a module and function"""
        return self._manager_string.rsplit('.', 1)

    def __call__(self, *args, **kwargs):
        return self.function(*args, **kwargs)


class Client:
    def __init__(self, parser_file='cli.json'):
        self.parser = create_parser(parser_file)
        self.managers = create_commands(self.parser, parser_file)

    def execute(self, command=None):
        """Execute the command using the parser and manager"""
        args = self.parser.parse_args(command)
        # we need to know the name of the subcommand destination
        # manager = self.managers[self.subparser.dest]
        manager = self.managers[args.command]
        return manager(args)


def main():
    return 0


if __name__ == '__main__':
    main()


# unittests
class Tests(unittest.TestCase):
    def setUp(self):
        self.parser_specs = """
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
                "required": false
            },
            "options": [
                {"flag": ["-x"], "help": "Path to the output file"},
                {"flag": ["-w"], "help": "Enable verbose mode", "action": "store_true"}
            ],
            "commands": [
            {
                "name": "command",
                "help": "command help",
                "options": [
                    {"flag": ["input_file"], "help": "Path to the input file"},
                    {"flag": ["-o"], "help": "Path to the output file"},
                    {"flag": ["--verbose"], "help": "Enable verbose mode", "action": "store_true"}
                ],
                "manager": "experiment.command_manager"
            },
            {
                "name": "command2",
                "help": "command2 help",
                "options": [
                    {"flag": ["input_file"], "help": "Path to the input file"},
                    {"flag": ["-o"], "help": "Path to the output file"},
                    {"flag": ["--verbose"], "help": "Enable verbose mode", "action": "store_true"}
                ],
                "manager": "experiment.command2_manager"
            }
            ]
        }
        """

    def test_create_parser(self):
        """
        Test the example provided in the question.
        """
        parser = create_parser(self.parser_specs)
        sys.argv = shlex.split('script.py -x 37 -w')
        print(parser)
        args = parser.parse_args()
        self.assertIsInstance(args, argparse.Namespace)

    def test_create_parser_arguments(self):
        """
        Test the example provided in the question.
        """
        # todo: there will have to be a way to prevent the wrong arguments from being passed; perhaps a schema enforced?
        sys.argv = shlex.split('script.py -x 37 -w')
        parser = create_parser(self.parser_specs)
        args = parser.parse_args()
        self.assertIsInstance(args, argparse.Namespace)
        self.assertEqual('37', args.x)
        self.assertTrue(args.w)

    def test_create_subparser(self):
        """
        Test the example provided in the question.
        """
        parser = create_parser(self.parser_specs)
        print(f"{parser.subparsers = }")
        self.assertIsInstance(parser, CLIParser)
        self.assertIsNotNone(parser.subparsers)

    def test_create_command(self):
        """Add a command to a subparser."""
        parser = create_parser(self.parser_specs)
        print(f"{parser._subparsers = }")
        managers = create_commands(parser, self.parser_specs)
        print(f"{managers = }")
        sys.argv = shlex.split('script.py command input.txt -o output.txt --verbose')
        args = parser.parse_args()
        print(f"{args = }")
        sys.argv = shlex.split('script.py command2 input.txt -o output.txt --verbose')
        args = parser.parse_args()
        print(f"{args = }")

    def test_manager_class(self):
        """Test that the manager attribute can be fired
         and an appropriate error is raised if it is not.
         """
        # todo: what should a manager do?
        # 1. it should take a string
        # 2. it should partition the string into the module and function
        # 3. it should import the module
        # 4. it should call the function
        # 5. it should return the exit status
        # manager = Manager("experiment.command_manager")
        # exit_status = manager(args)
        sys.argv = shlex.split('script.py command input.txt -o output.txt --verbose')
        manager = Manager("experiment.command_manager")
        self.assertTrue(hasattr(manager, "module"))
        self.assertTrue(hasattr(manager, "function"))
        self.assertTrue(hasattr(manager, "__call__"))
        self.assertTrue(inspect.ismethod(getattr(manager, "__call__")))
