## Example Usage

Assumptions:

- The file ``cli.toml`` exists in the current working directory; otherwise the user must specify the path to the
  configuration file and pass it to the `Client` constructor.
- The file ``cli.toml`` contains the complete CLI description consisting of:
  - general description of the CLI handler;
  - detailed description of each client command;
  - details about how each command is routed;

First, we will work out the JSON schema for the client definition.

```json
{
  "client": {
    "prog": "sff",
    "description": "The EMDB-SFF Read/Write Toolkit (sfftk-rw)",
    "options": [
      {
        "name": [
          "-V",
          "--version"
        ],
        "help": "Show the version and exit",
        "action": "store_true"
      },
      {
        "name": [
          "-c",
          "--config-file"
        ],
        "help": "The path to the configuration file",
        "type": "str",
        "required": false
      },
      {
        "name": [
          "-v",
          "--verbose"
        ],
        "help": "Show more information about the analysis",
        "action": "store_true"
      }
    ]
  },
  "config_file": {
    "format": "ini",
    "filename": "sfftk.conf",
    "location": "user",
    "create": true
  },
  "commands": [
    {
      "name": "convert",
      "description": "Perform EMDB-SFF file format interconversions",
      "manager": "sfftkrw.sffrw.handle_convert",
      "groups": {
        "output": {
          "required": true,
          "mutually_exclusive": true
        }
      },
      "options": [
        {
          "name": [
            "from_file"
          ],
          "nargs": "*",
          "help": "file to convert from",
          "validator": "sfftkrw.validators.FileExists"
        },
        {
          "name": [
            "-D",
            "--details"
          ],
          "help": "populate the <details>...</details> in the XML file"
        },
        {
          "name": [
            "-R",
            "--primary-descriptor"
          ],
          "help": "populate the <primary_descriptor>...</primary_descriptor> in the XML file",
          "validator": "sfftkrw.validators.PrimaryDescriptor"
        },
        {
          "name": [
            "-x",
            "--exclude-geometry"
          ],
          "help": "exclude geometry data from the SFF file",
          "action": "store_true"
        },
        {
          "name": [
            "--json-indent"
          ],
          "help": "indentation level for JSON output",
          "type": "int",
          "default": 4
        },
        {
          "name": [
            "--json-sort-keys"
          ],
          "help": "sort keys for JSON output",
          "action": "store_true"
        },
        {
          "name": [
            "-o', '--output"
          ],
          "help": "output file name",
          "group": "output"
        },
        {
          "name": [
            "-f",
            "--format"
          ],
          "help": "output file format",
          "choices": [
            "sff",
            "xml",
            "json"
          ],
          "group": "output"
        }
      ]
    },
    {
      "name": "view",
      "description": "View EMDB-SFF files",
      "manager": "sfftkrw.sffrw.handle_view",
      "options": [
        {
          "name": [
            "from_file"
          ],
          "nargs": "*",
          "help": "file to view",
          "validator": "sfftkrw.validators.FileExists"
        },
        {
          "name": [
            "--sff-version"
          ],
          "help": "display the SFF version",
          "action": "store_true"
        }
      ]
    }
  ]
}
```
TOML is a much better way to capture the client description because it can accommodate coments and is far more compact (no extraneous braces). The equivalent TOML file is:
```toml
[client]
prog = "sff"
description = "The EMDB-SFF Read/Write Toolkit (sfftk-rw)"

[[client.options]]
name = ["-V", "--version"]
help = "Show the version and exit"
action = "store_true"

[[client.options]]
name = ["-c", "--config-file"]
help = "The path to the configuration file"
type = "str"
required = false

[[client.options]]
name = ["-v", "--verbose"]
help = "Show more information about the analysis"
action = "store_true"

[config_file]
format = "ini"
filename = "sfftk.conf"
location = "user"
create = true

[[commands]]
name = "convert"
description = "Perform EMDB-SFF file format interconversions"
manager = "sfftkrw.sffrw.handle_convert"

[commands.groups.output]
required = true
mutually_exclusive = true

[[commands.options]]
name = ["from_file"]
nargs = "*"
help = "file to convert from"
validator = "sfftkrw.validators.FileExists"

[[commands.options]]
name = ["-D", "--details"]
help = "populate the <details>...</details> in the XML file"

[[commands.options]]

name = ["-R", "--primary-descriptor"]
help = "populate the <primary_descriptor>...</primary_descriptor> in the XML file"
validator = "sfftkrw.validators.PrimaryDescriptor"

[[commands.options]]
name = ["-x", "--exclude-geometry"]
help = "exclude geometry data from the SFF file"
action = "store_true"

[[commands.options]]
name = ["--json-indent"]
help = "indentation level for JSON output"
type = "int"
default = 4

[[commands.options]]
name = ["--json-sort-keys"]
help = "sort keys for JSON output"
action = "store_true"

[[commands.options]]
name = ["-o", "--output"]
help = "output file name"
group = "output"

[[commands.options]]
name = ["-f", "--format"]
help = "output file format"
choices = ["sff", "xml", "json"]
group = "output"

[[commands]]
name = "view"
description = "View EMDB-SFF files"
manager = "sfftkrw.sffrw.handle_view"

[[commands.options]]
name = ["from_file"]
nargs = "*"
help = "file to view"
validator = "sfftkrw.validators.FileExists"

[[commands.options]]
name = ["--sff-version"]
help = "display the SFF version"
action = "store_true"
```

```python
import sys

import xpresscli as xcli


def main():
    """Entry point for the application script"""
    with xcli.Client() as cli:
        exit_status = cli.execute()
    return exit_status


if __name__ == "__main__":
    sys.exit(main())
```