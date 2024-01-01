from __future__ import annotations

import argparse
import configparser
import importlib
import inspect
import json
import os
import pathlib
import shlex
import sys
import unittest
from typing import Union, Optional, Iterable, List

_ = pathlib.Path  # prevent pycharm from removing the import


def parse_options(parser, options):
    """Parse the options"""
    if isinstance(options, str):
        specs = json.loads(options)
    elif isinstance(options, list):
        specs = options
    elif options is None:
        specs = []
    else:
        raise TypeError(f"json_specs must be a string or list, not {type(options)}")
    for arg_spec in specs:
        # Add the argument to the parser
        flag = arg_spec.pop('flag')
        # fixme: convert string types to actual types
        if 'type' in arg_spec:
            arg_spec['type'] = eval(arg_spec['type'])
        parser.add_argument(*flag, **arg_spec)


def parse_groups(parser, groups):
    """Parse the groups"""
    if isinstance(groups, str):
        specs = json.loads(groups)
    elif isinstance(groups, list):
        specs = groups
    elif groups is None:
        specs = []
    else:
        raise TypeError(f"json_specs must be a string or list, not {type(groups)}")
    groups = dict()
    for group_spec in specs:
        options = group_spec.pop('options')
        # Add the group to the parser
        groups[group_spec['title']] = parser.add_argument_group(**group_spec)
        parse_options(groups[group_spec['title']], options)
    return groups


def parse_mutually_exclusive_groups(parser, mutex_groups):
    """Parse the mutually exclusive mutex_groups"""
    if isinstance(mutex_groups, str):
        specs = json.loads(mutex_groups)
    elif isinstance(mutex_groups, list):
        specs = mutex_groups
    elif mutex_groups is None:
        specs = []
    else:
        raise TypeError(f"json_specs must be a string or list, not {type(mutex_groups)}")
    mutex_groups = dict()
    for group_spec in specs:
        title = group_spec.pop('title')
        options = group_spec.pop('options')
        # Add the group to the parser
        mutex_groups[title] = parser.add_mutually_exclusive_group(**group_spec)
        parse_options(mutex_groups[title], options)
    return mutex_groups


def parse_parents(parent_parsers_spec) -> Dict[argparse.ArgumentParser]:
    """Parse the parent parsers"""
    if isinstance(parent_parsers_spec, str):
        specs = json.loads(parent_parsers_spec)
    elif isinstance(parent_parsers_spec, list):
        specs = parent_parsers_spec
    elif parent_parsers_spec is None:
        specs = []
    else:
        raise TypeError(f"json_specs must be None, a string or list, not {type(parent_parsers_spec)}")
    parent_parsers = dict()
    for parent_spec in specs:
        name = parent_spec['prog']
        options = parent_spec.pop('options')
        # Add the group to the parser
        parent_parsers[name] = argparse.ArgumentParser(**parent_spec)
        parse_options(parent_parsers[name], options)
    return parent_parsers


class CLIParser(argparse.ArgumentParser):

    def __init__(self, parser_spec: dict):
        self._parser_spec = parser_spec.get('parser')
        self._parent_parsers_spec = self._parser_spec.pop('parent_parsers', None)
        self._subparsers_spec = self._parser_spec.pop('subparsers', None)
        self._options = self._parser_spec.pop('options', None)
        self._groups_spec = self._parser_spec.pop('groups', None)
        self._mutually_exclusive_groups_spec = self._parser_spec.pop('mutually_exclusive_groups', None)
        super().__init__(**self._parser_spec)
        # if none of the subparsers are required then we can add the options
        self.managers = dict()
        # self.subparsers = CLISubParsers(self, **self._subparsers_spec)
        # what do I want from the subparsers?
        # 2. add a subparser to the subparser to some maximum depth
        # 3. add the commands to the subparser
        self.parent_parsers = parse_parents(self._parent_parsers_spec)
        self.subparsers = self._parse_subparsers(self._subparsers_spec)
        # prepare the parser
        parse_options(self, self._options)
        # prepare the groups
        self.groups = parse_groups(self, self._groups_spec)
        # prepare the mutually exclusive groups
        self.mutually_exclusive_groups = parse_mutually_exclusive_groups(self, self._mutually_exclusive_groups_spec)

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
                groups = command.pop('groups', None)
                mutex_groups = command.pop('mutually_exclusive_groups', None)
                manager_string = command.pop('manager', None)
                self.managers[command['name']] = Manager(manager_string)
                _parents = command.pop('parents', None)
                if _parents is not None:
                    parents = [self.parent_parsers[parent] for parent in _parents]
                else:
                    parents = []
                command_parser = subparsers.add_parser(**command, parents=parents)
                if options is not None:
                    parse_options(command_parser, options)
                    if groups is not None:
                        parse_groups(command_parser, groups)
                    if mutex_groups is not None:
                        parse_mutually_exclusive_groups(command_parser, mutex_groups)
            return subparsers

    def __str__(self):
        return self.format_help()


class LocalConfigParser(configparser.ConfigParser):
    """A local config parser that can be used to parse a config file."""

    def __init__(self, *args, **kwargs):
        super().__init__(
            interpolation=configparser.ExtendedInterpolation(),
            converters={
                'list': self.get_list,
                'tuple': self.get_tuple,
                'python': self.get_python,
            }, *args, **kwargs)
        self._filenames = None

    @property
    def filenames(self):
        return self._filenames

    def read(self, filenames: Union[os.PathLike, Iterable[os.PathLike]], encoding: Optional[str] = None) -> List[str]:
        self._filenames = filenames
        return super().read(filenames, encoding)

    def __str__(self):
        string = ""
        for section in self.sections():
            string += f"[{section}]\n"
            for option in self[section]:
                string += f"{option} = {self.get(section, option, raw=True)}\n"
            string += "\n"
        return string

    @staticmethod
    def get_list(value):
        """Convert the option value to a list"""
        return list(map(lambda s: s.strip(), value.split(',')))

    @staticmethod
    def get_tuple(value):
        """Convert the option value to a tuple"""
        return tuple(map(lambda s: s.strip(), value.split(',')))

    @staticmethod
    def get_python(value):
        """Evaluate the option value as literal Python code"""
        return eval(value)


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
        self.parser_spec = {
            "parser": {
                "prog": "oil",
                "description": "Custom script with dynamic arguments",
                "add_help": True,
                "parent_parsers": [
                    {
                        "prog": "parent1",
                        "add_help": False,
                        "options": [
                            {
                                "flag": [
                                    "--config-file"
                                ],
                                "type": "pathlib.Path",
                                "help": "Path to the config file"
                            },
                            {
                                "flag": [
                                    "--dry-run"
                                ],
                                "help": "Dry run mode",
                                "action": "store_true"
                            }
                        ]
                    }
                ],
                "subparsers": {
                    "title": "subcommands",
                    "description": "valid subcommands",
                    "dest": "subcommand",
                    "required": True,
                    "subparsers": None,
                    "commands": [
                        {
                            "name": "command",
                            "help": "command help",
                            "parents": ["parent1"],
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
                            "mutually_exclusive_groups": [
                                {
                                    "title": "mutex_group",
                                    "required": True,
                                    "options": [
                                        {
                                            "flag": [
                                                "-f"
                                            ],
                                            "help": "Never option",
                                        },
                                        {
                                            "flag": [
                                                "-g"
                                            ],
                                            "help": "Mixed option",
                                            "action": "store_true"
                                        }
                                    ]
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
                ],
                "groups": [
                    {
                        "title": "group1",
                        "description": "group1 description",
                        "options": [
                            {
                                "flag": [
                                    "-y"
                                ],
                                "help": "Path to the output file"
                            },
                            {
                                "flag": [
                                    "-z"
                                ],
                                "help": "Enable verbose mode",
                                "action": "store_true"
                            }
                        ]
                    },
                    {
                        "title": "group2",
                        "description": "group2 description",
                        "options": [
                            {
                                "flag": [
                                    "-c"
                                ],
                                "help": "Some other option"
                            },
                            {
                                "flag": [
                                    "-b"
                                ],
                                "help": "Another option",
                                "action": "store_false"
                            }
                        ]
                    }
                ],
                "mutually_exclusive_groups": [
                    {
                        "title": "mutex_group",
                        "required": False,
                        "options": [
                            {
                                "flag": [
                                    "-n"
                                ],
                                "help": "Never option",
                            },
                            {
                                "flag": [
                                    "-m"
                                ],
                                "help": "Mixed option",
                                "action": "store_true"
                            }
                        ]
                    }
                ]
            },
            # "config": {
            #     "format": "ini",
            #     "filename": "config.ini",
            #     "location": "user",
            #     "create": True
            # }
        }

    def test_create_parser(self):
        """
        Test the example provided in the question.
        """
        # todo: there will have to be a way to prevent the wrong arguments from being passed; perhaps a schema enforced?
        sys.argv = shlex.split('script.py -x 37 -w')
        parser_spec = self.parser_spec  # json.loads(self.parser_spec)
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
        parser = CLIParser(parser_spec=self.parser_spec)
        self.assertIsInstance(parser, CLIParser)
        self.assertIsNotNone(parser.subparsers)

    def test_create_command(self):
        """Add a command to a subparser."""
        parser = CLIParser(parser_spec=self.parser_spec)
        sys.argv = shlex.split('script.py command input.txt -o output.txt --verbose')
        args = parser.parse_args()
        self.assertEqual('command', args.subcommand)
        sys.argv = shlex.split('script.py command2 input.txt -o output.txt --verbose -f nothing')
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
        parser = CLIParser(parser_spec=self.parser_spec)
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

    def test_option_groups(self):
        """Test that the option groups are added to the parser."""
        parser = CLIParser(parser_spec=self.parser_spec)
        self.assertIsInstance(parser, CLIParser)
        self.assertIsNotNone(parser.groups)
        self.assertEqual(2, len(parser.groups))
        self.assertIn('group1', parser.groups)
        self.assertIn('group2', parser.groups)
        self.assertIsInstance(parser.groups['group1'], argparse._ArgumentGroup)
        self.assertIsInstance(parser.groups['group2'], argparse._ArgumentGroup)
        self.assertIsInstance(parser.groups, dict)

    def test_mutually_exclusive_groups(self):
        """Test that the mutually exclusive groups are added to the parser."""
        parser = CLIParser(parser_spec=self.parser_spec)
        self.assertIsInstance(parser, CLIParser)
        self.assertIsNotNone(parser.mutually_exclusive_groups)
        self.assertEqual(1, len(parser.mutually_exclusive_groups))
        self.assertIn('mutex_group', parser.mutually_exclusive_groups)
        self.assertIsInstance(parser.mutually_exclusive_groups['mutex_group'], argparse._MutuallyExclusiveGroup)
        self.assertIsInstance(parser.mutually_exclusive_groups, dict)

    def test_parent_parser(self):
        """Test that the parent parser is added to the parser."""
        parser = CLIParser(parser_spec=self.parser_spec)
        self.assertIsInstance(parser.parent_parsers, dict)
        self.assertIn('parent1', parser.parent_parsers)
        self.assertIsInstance(parser.parent_parsers['parent1'], argparse.ArgumentParser)
        sys.argv = shlex.split('oil -n something command --config-file /path/to/file --dry-run'
                               ' input.txt -o output.txt --verbose')
        args = parser.parse_args()
        self.assertEqual(pathlib.Path('/path/to/file'), args.config_file)
        self.assertTrue(args.dry_run)
        self.assertEqual('input.txt', args.input_file)
        self.assertEqual('output.txt', args.o)
        self.assertTrue(args.verbose)

    # def test_config(self):
    #     """Test that we can define a config file"""
    #     parser = CLIParser(parser_spec=self.parser_spec)
    #     self.assertIsInstance(parser.configs, LocalConfigParser)


class TestOil(unittest.TestCase):
    """Test using expresscli on the oil project github.com/emdb-empiar/oil"""

    def setUp(self):
        LIMIT_COUNT = 1000
        MIN_MEMORY = 1024
        MAX_MEMORY = 128000
        # MIN_ARRAY_SIZE = 2
        # MAX_ARRAY_SIZE = 100
        self.parser_spec = {
            "parser": {
                "prog": "oil",
                "description": "process and load .map files into OMERO for the Volume Browser",
                "parent_parsers": [
                    {
                        "prog": "parent1",
                        "add_help": False,
                        "options": [
                            {
                                "flag": ["--dry-run"],
                                "help": "print out what would be done [default: False]",
                                "action": "store_true"
                            },
                            {
                                "flag": ["-c", "--config-file"],
                                "type": "pathlib.Path",
                                "help": "oil configs [default: value of OILCONF environment variable]"
                            },
                            {
                                "flag": ["-v", "--verbose"],
                                "help": "verbose output to terminal in addition to log files [default: False]",
                                "action": "store_true"
                            },
                            {
                                "flag": ["-d", "--debug"],
                                "help": "debug [False]",
                                "action": "store_true"
                            },
                            {
                                "flag": ["--no-retry"],
                                "help": "run async jobs sequentially i.e. if one fails, terminate immediately [False]",
                            },
                            {
                                "flag": ["--no-summary"],
                                "action": "store_true",
                                "help": "do not display the oil status [False]",
                            },
                            {
                                'flag': ['--lsf'],
                                'default': False,
                                'action': 'store_true',
                                'help': "run the command on the job scheduler according to the configs [False]"
                            },
                            {
                                'flag': ['--lsf-job-name'],
                                'help': f"give the job a short meaningful name [default: None]"
                            },
                            {
                                'flag': ['--lsf-memory'],
                                'type': 'int',
                                'default': 1024,
                                'help': f"run the command with this much memory requested in MiB e.g. 1024 = 1024MiB = 1GiB; valid values in range {MIN_MEMORY}-{MAX_MEMORY} [{MIN_MEMORY}]"
                            },
                            {
                                'flag': ['--lsf-depends-on'],
                                'help': f"wait for the job of the specified ID to complete first"
                            },
                            {
                                'flag': ['--lsf-array-size'],
                                'type': 'int',
                                'help': f"run builds in parallel by spawning an job array of this size [1]"
                            }
                        ]
                    }
                ],
                "subparsers": {
                    "dest": "command",
                    "title": "Tools",
                    "help": "oil utilities",
                    "required": True,
                    "commands": [
                        {
                            "name": "init",
                            "help": "initialise oil",
                            "description": "initialise an oil installation by creating resource directories",
                            "parents": ["parent1"],
                            "manager": "oil.handlers.init"
                        },
                        {
                            "name": "status",
                            "description": "print the status of oil",
                            "help": "display the status of oil",
                            "parents": ["parent1"],
                            "manager": "oil.handlers.status"
                        },
                        {
                            "name": "load",
                            "description": "prepare params, build image files and import metadata into OMERO for a single entry",
                            "help": "load the entry specified by ID",
                            "parents": ["parent1"],
                            "manager": "oil.handlers.load",
                            "options": [
                                {
                                    'flag': ['--use-ssh'],
                                    'action': 'store_true',
                                    'help': "run import through an SSH call [False]"
                                },
                                {
                                    'flag': ['--force'],
                                    'action': 'store_true',
                                    'help': "'y' by default [False]"
                                },
                                {
                                    'flag': ['--purge'],
                                    'action': "store_true",
                                    'help': "purge an existing entry before load [False]"
                                },
                                {
                                    'flag': ['--map-dir'],
                                    'help': "a comma-separated (no spaces) sequence of paths to search for files; "
                                            "by default we read the value from configs; this option overrides configs"
                                },
                                {
                                    'flag': ['-x', '--extension'],
                                    'help': "the extension use"
                                },
                                {
                                    'flag': ['--limit'],
                                    'type': 'int',
                                    'default': LIMIT_COUNT,
                                    'help': f"limit the number of entries processed at any one time; "
                                            f"to remove the limit set limit to zero [default: {LIMIT_COUNT}]"
                                },
                            ],
                            "mutually_exclusive_groups": [
                                {
                                    "title": "load_input_group",
                                    "required": False,
                                    "options": [
                                        {
                                            'flag': ['-e', '--entry-name'],
                                            'help': "name of the entry e.g. emd_1234 or empiar_12345"
                                        },
                                        {
                                            'flag': ['-p', '--entry-path'],
                                            'action': 'append',
                                            'type': 'pathlib.Path',
                                            'help': "the relative/absolute path to the entry file e.g. /path/to/emd_1234.map; "
                                                    "the file must be a canonically named file; "
                                                    "this option takes precedence over --map-dir and configs[dirs][map_dir] [default: None]"
                                        },
                                        {
                                            'flag': ['-f', '--entries-file'],
                                            'type': 'pathlib.Path',
                                            'help': "name of a file with a list of entry names"
                                        },
                                    ]
                                }
                            ]
                        },
                        {
                            "name": "prep",
                            "description": "runs the prep step which generates all build parameters",
                            "help": "prepare entry parameters for build",
                            "parents": ["parent1"],
                            "manager": "oil.handlers.prep",
                            "options": [
                                {
                                    'flag': ['--use-ssh'],
                                    'action': 'store_true',
                                    'help': "run import through an SSH call [False]"
                                },
                                {
                                    'flag': ['--map-dir'],
                                    'help': "a comma-separated (no spaces) sequence of paths to search for files; "
                                            "by default we read the value from configs; this option overrides configs"
                                },
                                {
                                    'flag': ['-x', '--extension'],
                                    'help': "the extension use"
                                },
                                {
                                    'flag': ['--limit'],
                                    'type': 'int',
                                    'default': LIMIT_COUNT,
                                    'help': f"limit the number of entries processed at any one time; "
                                            f"to remove the limit set limit to zero [default: {LIMIT_COUNT}]"
                                },
                            ],
                            "mutually_exclusive_groups": [
                                {
                                    "title": "prep_input_group",
                                    "required": False,
                                    "options": [
                                        {
                                            'flag': ['-e', '--entry-name'],
                                            'help': "name of the entry e.g. emd_1234 or empiar_12345"
                                        },
                                        {
                                            'flag': ['-p', '--entry-path'],
                                            'action': 'append',
                                            'type': 'pathlib.Path',
                                            'help': "the relative/absolute path to the entry file e.g. /path/to/emd_1234.map; "
                                                    "the file must be a canonically named file; "
                                                    "this option takes precedence over --map-dir and configs[dirs][map_dir] [default: None]"
                                        },
                                        {
                                            'flag': ['-f', '--entries-file'],
                                            'type': 'pathlib.Path',
                                            'help': "name of a file with a list of entry names"
                                        },
                                        {
                                            'flag': ['-j', '--entries-json'],
                                            'type': 'pathlib.Path',
                                            'help': "name of a JSON file with the entries in a field called 'entries' as a list"
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            }
        }
        self.parser = CLIParser(parser_spec=self.parser_spec)
        self.cli = lambda command_str: self.parser.parse_args(shlex.split(command_str))
        self.TEST_CONFIG_PATH = pathlib.Path(__file__).parent / 'test_config.ini'
        # os.environ['OILCONF'] = str(self.TEST_CONFIG_PATH)

        # def tearDown(self):
        #     del os.environ['OILCONF']

    def test_init(self):
        """Test oil initialisation"""
        args = self.cli(f'init --config-file {self.TEST_CONFIG_PATH}')
        self.assertEqual('init', args.command)
        self.assertFalse(args.dry_run)
        self.assertFalse(args.verbose)
        self.assertEqual(args.config_file, self.TEST_CONFIG_PATH)
        self.assertFalse(args.debug)

    def test_status(self):
        """Test oil status"""
        args = self.cli(f'status --config-file {self.TEST_CONFIG_PATH}')
        self.assertEqual('status', args.command)
        self.assertFalse(args.dry_run)
        self.assertFalse(args.verbose)
        self.assertEqual(args.config_file, self.TEST_CONFIG_PATH)
        self.assertFalse(args.debug)

    def test_load(self):
        """Test oil load"""
        args = self.cli(f"load -e emd_1234 --config-file {self.TEST_CONFIG_PATH}")
        self.assertEqual(args.command, 'load')
        self.assertFalse(args.dry_run)
        self.assertEqual(args.entry_name, 'emd_1234')
        self.assertFalse(args.purge)
        self.assertFalse(args.force)
        self.assertIsNone(args.map_dir)
        self.assertIsNone(args.extension)
        self.assertFalse(args.no_summary)
        self.assertEqual(args.limit, 1000)
        args = self.cli(f"load -p /path/to/emd_1234.map --config-file {self.TEST_CONFIG_PATH}")
        self.assertEqual(
            [
                pathlib.Path('/path/to/emd_1234.map'),
            ],
            args.entry_path
        )
        args = self.cli(f"load -f /path/to/entries.txt --config-file {self.TEST_CONFIG_PATH}")
        self.assertEqual(
            pathlib.Path('/path/to/entries.txt'),
            args.entries_file
        )
        args = self.cli(f"load --no-summary --config-file {self.TEST_CONFIG_PATH}")
        self.assertTrue(args.no_summary)
        args = self.cli(f"load -e emd_1234 --purge --force --config-file {self.TEST_CONFIG_PATH}")
        self.assertTrue(args.purge)
        self.assertTrue(args.force)
        args = self.cli(f"load -c {self.TEST_CONFIG_PATH} --use-ssh -e emd_1234")
        self.assertTrue(args.use_ssh)

    def test_prep(self):
        """Test oil prep"""
        args = self.cli(f"prep --config-file {self.TEST_CONFIG_PATH}")
        self.assertEqual(args.command, 'prep')
        self.assertEqual(args.limit, 1000)
        self.assertFalse(args.dry_run)
        self.assertIsNone(args.entry_name)
        self.assertIsNone(args.entries_file)
        self.assertFalse(args.verbose)
        self.assertEqual(args.config_file, self.TEST_CONFIG_PATH)
        self.assertFalse(args.debug)
        self.assertFalse(args.no_retry)
        args = self.cli(f"prep -c {self.TEST_CONFIG_PATH} --use-ssh")
        self.assertTrue(args.use_ssh)
        # self.assertTrue(args._configs.getboolean('omero', 'use_ssh'))
        # new_path = secrets.token_urlsafe(random.randint(10, 20))
        # os.mkdir(new_path)
        # args = self.cli(f"prep --map-dir {new_path}")
        # map_dir = args._configs.get('dirs', 'map_dir')
        # self.assertEqual(map_dir, os.path.join(os.path.dirname(os.path.dirname(__file__)), new_path))
        # # map_dir must be abs path
        # self.assertTrue(os.path.isabs(map_dir))
        # os.rmdir(new_path)
        # self.assertFalse(os.path.exists(new_path))

    def test_build(self):
        """Test oil build"""
        parser = CLIParser(parser_spec=self.parser_spec)
        print(parser.print_help())

    def test_import(self):
        """Test oil import"""

    def test_reset(self):
        """Test oil reset"""

    def test_clean(self):
        """Test oil clean"""

    def test_list(self):
        """Test oil list"""

    def test_search(self):
        """Test oil search"""

    def test_delete(self):
        """Test oil delete"""

    def test_purge(self):
        """Test oil purge"""

    def test_fix(self):
        """Test oil fix"""

    def test_sync(self):
        """Test oil sync"""

    def test_collate(self):
        """Test oil collate"""
