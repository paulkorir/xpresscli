import argparse
import io
import shlex
import sys
import configparser


class Validator:
    """Class used to validate the parsed arguments"""

    def __init__(self):
        pass


# configs could be specified in INI/CONF format, XML, JSON, YAML, TOML, etc.
class Config(configparser.ConfigParser):
    """Class used to represent the configuration file"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class Parser(argparse.ArgumentParser):
    """Class used to parse command line arguments"""

    def __init__(self, client_definition: dict, config: Config = None):
        super().__init__(
            prog=client_definition['name'],
            description=client_definition['description']
        )
        self._client_definition = client_definition
        self._config = config
        # for command in client_definition['commands']:
        #     self.add_argument(command['name'], help=command['description'])
        # for option in client_definition['options']:
        #     self.add_argument(option['name'], help=option['description'])

    def parse(self, *args, **kwargs) -> argparse.Namespace:
        """Parse the arguments"""
        # todo: any pre-processing of args
        return super().parse_args(args)


class Manager:
    """Class used to manage the xpresscli"""

    def __init__(self):
        pass

    def route(self, command: argparse.Namespace) -> int:
        """Route the command to the appropriate handler"""
        exit_status = 0
        # todo: route the command
        return exit_status


class Client:
    """User facing class used to instantiate a xpresscli object"""
    # there should be only one instance of this class therefore we use a singleton pattern
    parser = Parser()
    manager = Manager()
    # client_file_parser = ClientTOMLParser

    def __init__(self, client_file='cli.toml'):
        self._client_file = client_file

    def _initialise(self):
        with open(self._client_file) as f:
            client_definition = self._parse_client_file(f)
            self._initialise_parser(client_definition)
            self._initialise_manager(client_definition)

    def _parse_client_file(self, f: io.TextIOWrapper) -> dict:
        """Parse the xpresscli file

        At the moment the xpresscli file is a TOML file but this could change in the future.
        """
        client_definition = dict()
        # todo: parse the xpresscli file
        # client_definition = self.client_file_parser.parse(f)
        return client_definition

    def _initialise_parser(self, client_definition: dict) -> None:
        # todo: initialise the parser
        self.parser(
            client_definition,
        )  # better name?

    def _initialise_manager(self, client_definition):
        # todo: initialise the manager
        self.manager.initialise(client_definition)  # better name?

    def cli(self, command_str=None) -> argparse.Namespace:
        if command_str is not None:
            sys.argv = shlex.split(command_str)
        command = self.parser.parse()
        return command
