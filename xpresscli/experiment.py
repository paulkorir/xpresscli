import argparse
import importlib
import inspect
import json
import shlex
import sys
import unittest


def parse_options(parser, options):
    """Parse the options"""
    if isinstance(options, str):
        specs = json.loads(options)
    elif isinstance(options, list):
        specs = options
    else:
        raise TypeError(f"json_specs must be a string or list, not {type(options)}")
    for arg_spec in specs:
        # Add the argument to the parser
        flag = arg_spec.pop('flag')
        parser.add_argument(*flag, **arg_spec)


class CLIParser(argparse.ArgumentParser):

    def __init__(self, parser_spec: dict):
        self._parser_spec = parser_spec.get('parser')
        self._subparsers_spec = self._parser_spec.pop('subparsers', None)
        self._options = self._parser_spec.pop('options', None)
        super().__init__(**self._parser_spec)
        # if none of the subparsers are required then we can add the options
        self.managers = dict()
        # self.subparsers = CLISubParsers(self, **self._subparsers_spec)
        # what do I want from the subparsers?
        # 2. add a subparser to the subparser to some maximum depth
        # 3. add the commands to the subparser
        self.subparsers = self._parse_subparsers(self._subparsers_spec)
        # prepare the parser
        parse_options(self, self._options)

    def _parse_subparsers(self, subparsers_spec):
        if subparsers_spec is not None:
            commands = subparsers_spec.pop('commands', None)
            # todo: make it possible for a subparser to have a subparser
            _subparser = subparsers_spec.pop('subparsers', None)
            subparsers = self.add_subparsers(
                **subparsers_spec,
                parser_class=argparse.ArgumentParser
            )
            # add the commands
            for command in commands:
                options = command.pop('options', None)
                manager_string = command.pop('manager', None)
                self.managers[command['name']] = Manager(manager_string)
                command_parser = subparsers.add_parser(**command)
                if options is not None:
                    parse_options(command_parser, options)
            return subparsers

    def __str__(self):
        return self.format_help()


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

    def __str__(self):
        return f"{self._module}.{self._function}"


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
        self.parser_spec = """
{
  "parser": {
    "prog": "test",
    "description": "Custom script with dynamic arguments",
    "add_help": true,
    "subparsers": {
      "title": "subcommands",
      "description": "valid subcommands",
      "dest": "subcommand",
      "required": true,
      "subparsers": null,
      "commands": [
        {
          "name": "command",
          "help": "command help",
          "options": [
            {
              "flag": [
                "input_file"
              ],
              "help": "Path to the input file"
            },
            {
              "flag": [
                "-o"
              ],
              "help": "Path to the output file"
            },
            {
              "flag": [
                "--verbose"
              ],
              "help": "Enable verbose mode",
              "action": "store_true"
            }
          ],
          "manager": "experiment.command_manager"
        },
        {
          "name": "command2",
          "help": "command2 help",
          "options": [
            {
              "flag": [
                "input_file"
              ],
              "help": "Path to the input file"
            },
            {
              "flag": [
                "-o"
              ],
              "help": "Path to the output file"
            },
            {
              "flag": [
                "--verbose"
              ],
              "help": "Enable verbose mode",
              "action": "store_true"
            }
          ],
          "manager": "experiment.command2_manager"
        }
      ]
    },
    "options": [
      {
        "flag": [
          "-x"
        ],
        "help": "Path to the output file"
      },
      {
        "flag": [
          "-w"
        ],
        "help": "Enable verbose mode",
        "action": "store_true"
      }
    ]
  }
}
        """

    def test_create_parser(self):
        """
        Test the example provided in the question.
        """
        # todo: there will have to be a way to prevent the wrong arguments from being passed; perhaps a schema enforced?
        sys.argv = shlex.split('script.py -x 37 -w')
        parser_spec = json.loads(self.parser_spec)
        parser_spec['parser']['subparsers']['required'] = False
        parser = CLIParser(parser_spec=parser_spec)
        args = parser.parse_args()
        self.assertIsInstance(args, argparse.Namespace)
        self.assertEqual('37', args.x)
        self.assertTrue(args.w)

    def test_create_subparser(self):
        """
        Test the example provided in the question.
        """
        parser = CLIParser(parser_spec=json.loads(self.parser_spec))
        self.assertIsInstance(parser, CLIParser)
        self.assertIsNotNone(parser.subparsers)

    def test_create_command(self):
        """Add a command to a subparser."""
        parser = CLIParser(parser_spec=json.loads(self.parser_spec))
        sys.argv = shlex.split('script.py command input.txt -o output.txt --verbose')
        args = parser.parse_args()
        self.assertEqual('command', args.subcommand)
        sys.argv = shlex.split('script.py command2 input.txt -o output.txt --verbose')
        args = parser.parse_args()
        self.assertEqual('command2', args.subcommand)

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
        parser = CLIParser(parser_spec=json.loads(self.parser_spec))
        args = parser.parse_args()
        manager = parser.managers[args.subcommand]
        self.assertTrue(hasattr(manager, "module"))
        self.assertTrue(hasattr(manager, "function"))
        self.assertTrue(hasattr(manager, "__call__"))
        self.assertTrue(inspect.ismethod(getattr(manager, "__call__")))
        self.assertEqual("experiment.command_manager", str(manager))
        # trigger the manager
        exit_status = manager(args)
        self.assertEqual(0, exit_status)
