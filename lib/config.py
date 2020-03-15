# Copyright 2020 Mike Iacovacci
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from colorama import Fore, Style
from os import path
from sys import platform, stderr
from yaml import parser, safe_load_all, scanner


class AxiomConfig:
    """ a collection of elements the program relies on for data validation and proper execution """

    def __init__(self, supplied_filename):
        """ creates multi-purpose, global config object used throughout program execution
              INPUT:  the filename of the YAML configuration file, typically "config.yml"
             OUTPUT:  instantiates an AxiomConfig object """

        self.config_file = str(supplied_filename)
        self.yaml_list = self.get_yaml(self.config_file)

        self.platform = self.get_platform()

        self.binary_folder = None
        self.history_folder = None
        self.inventory_folder = None
        self.ptf_folder = None
        self.get_folders()

        self.pattern_timeout = None
        self.pty_timeout = None
        self.safety_timeout = None
        self.get_timeouts()

        self.toolkits = self.get_toolkits()

        self.prompts = self.get_prompts()

        self.banner_file = self.get_banner()

        self.inputs_pattern = None
        self.input_types_list = None
        self.get_inputs()

        self.outputs = self.get_outputs()

    def get_banner(self):
        """ validates user-supplied banner filename, returns a filename (str) """

        try:
            banner = str(self.yaml_list[0]["banner_file"])

            if banner in ["", "None"]:
                print_error("ERROR: Invalid banner_file setting in configuration file")
                exit(1)

        except (AttributeError, IndexError, KeyError, TypeError, ValueError):
            print_error("ERROR: Invalid banner_file setting in configuration file")
            exit(1)

        else:
            return banner

    def get_folders(self):
        """ validates user-supplied folder names and sets global config values """

        try:
            binary_folder = str(self.yaml_list[0]["binary_folder"])
            history_folder = str(self.yaml_list[0]["history_folder"])
            inventory_folder = str(self.yaml_list[0]["inventory_folder"])
            ptf_folder = str(self.yaml_list[0]["ptf_folder"])

            if "None" in [binary_folder, history_folder, inventory_folder, ptf_folder] or \
                    "" in [binary_folder, history_folder, inventory_folder, ptf_folder]:
                print_error("ERROR: Invalid folder setting(s) in configuration file")
                exit(1)

        except (AttributeError, IndexError, KeyError, TypeError, ValueError):
            print_error("ERROR: Invalid folder setting(s) in configuration file")
            exit(1)

        else:
            self.binary_folder = binary_folder
            self.history_folder = history_folder
            self.inventory_folder = inventory_folder
            self.ptf_folder = ptf_folder

    @staticmethod
    def get_platform():
        """ queries the system for platform type, returns a platform name (str) """

        if platform == "linux":
            return "Linux"
        elif platform == "darwin":
            return "macOS"
        else:
            return "UNKNOWN PLATFORM"

    def get_inputs(self):
        """ iterates over listed input types, sets multiple values for class variables """

        input_types_list = []
        inputs_pattern = ""

        try:
            input_count = self.yaml_list[0]["input_types"].__len__()
            for i in range(input_count):
                input_name = str(self.yaml_list[0]["input_types"][i])

                if input_name == "None":
                    print_error("ERROR: Invalid input type in configuration file")
                    exit(1)

                input_types_list.append(input_name)
                inputs_pattern = inputs_pattern + "{" + input_name + "}|"
            inputs_pattern = inputs_pattern[:-1]

        except (AttributeError, IndexError, KeyError, TypeError, ValueError):
            print_error("ERROR: Configuration file error(s) near input_types section")
            exit(1)

        else:
            self.inputs_pattern = inputs_pattern
            self.input_types_list = input_types_list

    def get_outputs(self):
        """ iterates over listed output types, returns a list of two-item tuples """

        output_types = []

        try:
            output_count = self.yaml_list[0]["output_types"].__len__()
            for i in range(output_count):
                output_name = str(self.yaml_list[0]["output_types"][i])

                if output_name == "None":
                    print_error("ERROR: Invalid output type in configuration file")
                    exit(1)

                output_types.append(output_name)

        except (AttributeError, IndexError, KeyError, TypeError, ValueError):
            print_error("ERROR: Configuration file error(s) near output_types section")
            exit(1)

        else:
            return output_types

    def get_prompts(self):
        """ iterates over listed prompt types, returns a list of two-item tuples """

        prompt_types = []

        try:
            prompt_count = self.yaml_list[0]["prompt_types"].__len__()
            for i in range(prompt_count):
                prompt_name = list(self.yaml_list[0]["prompt_types"][i].keys())[0]
                prompt_pattern = str(self.yaml_list[0]["prompt_types"][i][prompt_name])

                if prompt_name != "other" and prompt_pattern == "None":
                    print_error(str("ERROR: Invalid prompt pattern for \"" + prompt_name + "\" in configuration file"))
                    exit(1)

                current_prompt = (prompt_name, prompt_pattern)
                prompt_types.append(current_prompt)

        except (AttributeError, IndexError, KeyError, TypeError, ValueError):
            print_error("ERROR: Configuration file error(s) near prompt_types section")
            exit(1)

        else:
            return prompt_types

    def get_timeouts(self):
        """ validates user-supplied timeout values and sets them in the global config """

        try:
            pattern_timeout = int(self.yaml_list[0]["pattern_timeout"])
            pty_timeout = float(self.yaml_list[0]["pty_timeout"])
            safety_timeout = int(self.yaml_list[0]["safety_timeout"])

            if pattern_timeout < 0 or \
                    pty_timeout < 0 or \
                    safety_timeout < 0:
                print_error("ERROR: Invalid timeout setting(s) in configuration file")
                exit(1)

        except (AttributeError, IndexError, KeyError, TypeError, ValueError):
            print_error("ERROR: Invalid timeout setting(s) in configuration file")
            exit(1)

        else:
            self.pattern_timeout = pattern_timeout
            self.pty_timeout = pty_timeout
            self.safety_timeout = safety_timeout

    def get_toolkits(self):
        """ iterates over listed toolkits in the YAML file, returns a list of three-item tuples """

        toolkits = []

        try:
            toolkit_count = self.yaml_list[0]["toolkits"].__len__()
            for i in range(toolkit_count):
                toolkit_name = str(list(self.yaml_list[0]["toolkits"][i].keys())[0])
                toolkit_file = str(self.yaml_list[0]["toolkits"][i][toolkit_name][0]["file"])
                toolkit_url = str(self.yaml_list[0]["toolkits"][i][toolkit_name][1]["url"])

                if (toolkit_name == "" or toolkit_name is None) or \
                        (toolkit_file == "" or toolkit_file is None) or \
                        (toolkit_url == "" or toolkit_url is None):
                    print_error("ERROR: Undefined toolkit in configuration file")
                    exit(1)
                else:
                    if self.yaml_list[0]["toolkits"][i][toolkit_name].__len__() == 2:
                        current_toolkit = (toolkit_name, toolkit_file, toolkit_url)
                        toolkits.append(current_toolkit)
                    else:
                        print_error("ERROR: Invalid toolkit in configuration file")
                        exit(1)

        except (AttributeError, IndexError, KeyError, TypeError, ValueError):
            print_error("ERROR: Configuration file error(s) near toolkits section")
            exit(1)

        else:
            return toolkits

    @staticmethod
    def get_yaml(config_file):
        """ extracts YAML content from specified file, returns a list object """

        try:
            if not path.exists(config_file):
                print_error("ERROR: Missing configuration file")
                exit(1)

            with open(config_file, 'r') as open_file:
                yaml_list = list(safe_load_all(open_file))

        except IOError:
            print_error("ERROR: Failed to open configuration file")
            exit(1)
        except (parser.ParserError, scanner.ScannerError):
            print_error("ERROR: Invalid configuration file")
            exit(1)
        else:
            return yaml_list


def print_error(message):
    """ SUMMARY:  prints stylized error text to STDERR
          INPUT:  error message (str)
         OUTPUT:  no return value, prints to STDERR """

    stderr.write(Fore.RED + message + Style.RESET_ALL + "\n")


axiom = AxiomConfig("config.yml")
