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

from lib.classes import *

from colorama import Fore, Style
from io import BytesIO
from os import geteuid, listdir, mkdir, path, rename, remove
from pickle import dump, load, PickleError
from prompt_toolkit import prompt
from prompt_toolkit.completion import FuzzyCompleter, WordCompleter
from prompt_toolkit.styles import Style as ptkStyle
from re import split
from shutil import rmtree
from sys import argv
from requests import get, RequestException
from yaml import safe_load_all, parser, scanner
from zipfile import BadZipFile, LargeZipFile, ZipFile


def able_to_merge(current_tool, tool_id, tools):
    """ SUMMARY:  determines if merging YAML data from 2 files is possible without data loss
          INPUT:  1) an AxiomTool object, a tool ID value (int), and 2) a list of AxiomTool objects
         OUTPUT:  True or False  """

    if tool_id < 0:
        return False

    match = tools[tool_id]
    temp_list = []
    new_list = []

    if current_tool[0]["ptf_module"] != match.ptf_module:
        return False
    if current_tool[0]["description"] != match.description:
        return False

    action_count = 0
    while action_count < match.action_list.__len__():
        temp_list.append(match.action_list[action_count].name)
        action_count += 1

    command_count = 0
    while command_count < match.command_list.__len__():
        temp_list.append(match.command_list[command_count].name)
        command_count += 1

    new_count = 0
    while new_count < current_tool[1]["commands"].__len__():
        new_list.append(list(current_tool[1]["commands"][new_count].keys())[0])
        new_count += 1

    for command_name in new_list:
        if command_name in temp_list:
            return False

    return True


def axiom_help():
    """ SUMMARY:  displays helpful CLI usage details with examples
          INPUT:  none
         OUTPUT:  none, only prints to the screen """

    print("\n" + "Standard usage: ./axiom [MODE] [TOOL] [NUM]"
          "\n" + "" +
          "\n" + "  ./axiom show nmap" +
          "\n" + "  ./axiom show mimikatz 1" +
          "\n" + "  ./axiom build powershell 4" +
          "\n" + "  ./axiom run hashcat 3" +
          "\n" + "" +
          "\n" + "Configuration management: ./axiom [MODE] [URL]" +
          "\n" + "" +
          "\n" + "  ./axiom new" +
          "\n" + "  ./axiom reload" +
          "\n" + "  ./axiom init" +
          "\n" + "  ./axiom init https://example.com/config.yml" +
          "\n")


def axiom_prompt(tool_list, tool_names, tools):
    """ SUMMARY:  main interactive prompt loop of the program, handles multiple tool selection loops
          INPUT:  1) list of two-item tuples (name, platform), 2) set of tool names, and 3) list of AxiomTool objects
         OUTPUT:  exit value (int) to be immediately passed to exit() in __main__ """

    exit_code = 1

    while exit_code > 0:
        exit_code = tool_selection_prompt(tool_list, tool_names, tools)

    return exit_code


def branch(settings, tool_list, tools):
    """ SUMMARY:  changes program flow based on user-supplied settings
          INPUT:  1) a three-item dictionary, 2) a de-duplicated list of tuples, and 3) list of AxiomTool objects
         OUTPUT:  no return value, may exit the entire program """

    if settings.get("mode") in [None, "reload", "init"]:
        return

    if settings.get("mode") == "new":
        new_generate_command()

    if settings.get("num") == -1:
        print_error("ERROR: Invalid command ID")
        exit(1)

    text = settings.get("tool")
    tool_id = disambiguate_tool_name(text, tool_list, tools)

    if tool_id < 0:
        print_error("ERROR: Invalid tool")
        exit(1)

    tool = tools[tool_id]

    if settings.get("mode") == "show":
        if settings.get("num") is None:
            tool.show()
            print()
            exit(0)
        elif int(settings.get("num") - 1) not in range(tool.combined_list.__len__()):
            print_error("ERROR: Invalid command specified")
            exit(1)
        else:
            number = int(settings.get("num") - 1)
            command_type, id_value = tool.resolve_command(number)
            if command_type == "action":
                tool.action_list[id_value].show()
                print()
            elif command_type == "command":
                tool.command_list[id_value].show()
                print()
        exit(0)

    if settings.get("mode") == "run":
        if settings.get("num") is None:
            print_error("ERROR: No command specified")
            exit(1)
        elif int(settings.get("num") - 1) not in range(tool.combined_list.__len__()):
            print_error("ERROR: Invalid command specified")
            exit(1)
        else:
            number = int(settings.get("num") - 1)
            command_type, id_value = tool.resolve_command(number)
            if command_type == "action":
                if tool.action_list[id_value].execution_type in ["standalone", "autonomous", "NX"]:
                    tool.action_list[id_value].run(tool)
                else:
                    print_error("ERROR: Selected action must be executed via interactive AXIOM prompt")
                    exit(1)
            elif command_type == "command":
                if tool.command_list[id_value].execution_type in ["standalone", "autonomous", "NX"]:
                    tool.command_list[id_value].run(tool)
                else:
                    print_error("ERROR: Selected command must be executed via interactive AXIOM prompt")
                    exit(1)
            exit(0)

    if settings.get("mode") == "build":
        if settings.get("num") is None:
            print_error("ERROR: No command specified")
            exit(1)
        elif int(settings.get("num") - 1) not in range(tool.combined_list.__len__()):
            print_error("ERROR: Invalid command specified")
            exit(1)
        else:
            number = int(settings.get("num") - 1)
            command_type, id_value = tool.resolve_command(number)
            if command_type == "action":
                tool.action_list[id_value].cli_print()
            elif command_type == "command":
                tool.command_list[id_value].cli_print()
            exit(0)


def command_selection_prompt(tool):
    """ SUMMARY:  prompts user to select a listed command/action for the current tool and calls the execution function
          INPUT:  an AxiomTool object
         OUTPUT:  none """

    while True:
        tool.show()
        number = prompt('\n[AXIOM] Select command: ')

        if number == "back":
            return
        if number == "exit" or number == "quit":
            print("Exiting...")
            exit(0)

        if number == "":
            continue

        try:
            number = int(number)
            number -= 1
        except (ValueError, TypeError):
            number = -1

        if number not in range(tool.combined_list.__len__()):
            print_error("\nERROR: Invalid command specified")
        else:
            command_type, id_value = tool.resolve_command(number)

            if command_type == "action":
                confirmed = tool.action_list[id_value].confirm_and_execute(tool)
            elif command_type == "command":
                confirmed = tool.command_list[id_value].confirm_and_execute(tool)
            else:
                confirmed = False

            if confirmed:
                dispatch.continue_trigger.wait(timeout=None)
                dispatch.continue_trigger.clear()
                print()
                input("[AXIOM] Press ENTER to continue ")


def create_missing_folder(folder):
    """ SUMMARY:  checks if specified folder exists, creates it if it does not exist
          INPUT:  a string specifying a folder on the filesystem
         OUTPUT:  none, creates necessary folder if it does not exist """

    if path.exists(folder):
        return
    else:
        try:
            mkdir(folder)
        except OSError:
            print_error(str("ERROR: Cannot create folder \"" + folder + "\""))
            exit(1)


def delete_and_recreate_folder(folder):
    """ SUMMARY:  deletes specified folder, if it exists, and (re)creates it on the filesystem
          INPUT:  a string specifying a folder on the filesystem
         OUTPUT:  none, deletes files from the filesystem and/or creates necessary folders """

    if path.exists(folder):
        try:
            rmtree(folder)
        except OSError:
            print_error(str("ERROR: Cannot delete folder \"" + folder + "\""))
            exit(1)

    create_missing_folder(folder)


def disambiguate_tool_name(text, tool_list, tools):
    """ SUMMARY:  finds the user-intended tool ID for multi-platform tool names prompting the user as needed
          INPUT:  1) supplied tool name (str), 2) de-duplicated list of tuples, and 3) list of AxiomTool objects
         OUTPUT:  tool ID value (int) or -1 if invalid number of platforms or no matching tool found """

    platform_list = []
    for x in tool_list:
        if x[0] == text:
            platform_list.append(x[1])

    platform_list = sorted(platform_list, key=str.casefold)

    potential_tool = []
    if platform_list.__len__() == 0:
        return -1
    elif platform_list.__len__() == 1:
        potential_tool.append(text)
        potential_tool.append(platform_list[0])
    else:
        selection = 0
        while selection == 0:
            print("\nPlatforms\n")
            i = 0
            while i < platform_list.__len__():
                print("  " + str(i + 1) + "\t" + platform_list[i])
                i += 1
            platform = prompt('\n[AXIOM] Select platform: ')

            try:
                number = int(platform)
            except (ValueError, TypeError):
                number = 0

            if number > 0:
                if number <= platform_list.__len__():
                    potential_tool.append(text)
                    potential_tool.append(platform_list[number - 1])
                    selection = 1

    return resolve_tool_id(potential_tool, tools)


def download_and_extract_zip(zip_url, extracted_folder, destination_folder, human_name):
    """ SUMMARY:  prepares the filesystem, downloads a ZIP file, and extracts it to a folder with a specified name
          INPUT:  ZIP file URL, temporary folder name, destination folder name, and human-friendly name (all strings)
         OUTPUT:  no return values, modifies the filesystem """

    if path.exists(destination_folder):
        try:
            rmtree(destination_folder)
        except OSError:
            print_error(str("ERROR: Cannot prepare extraction location \"" + destination_folder + "\""))
            exit(1)

    print("Downloading " + human_name + "...")

    try:
        request = get(zip_url)

    except RequestException:
        print_error(str("ERROR: Cannot download \"" + human_name + "\" from " + zip_url))
        exit(1)

    else:
        if request.status_code == 200:

            try:
                zipfile = ZipFile(BytesIO(request.content))
                zipfile.extractall(".")
                rename(extracted_folder, destination_folder)

            except (BadZipFile, LargeZipFile, OSError):
                print_error(str("ERROR: Cannot extract \"" + extracted_folder + "\""))
                exit(1)

        else:
            print_error(str("ERROR: Failed to download \"" + human_name + "\""))
            exit(1)


def get_args():
    """ SUMMARY:  processes command-line arguments to modify overall program execution flow
          INPUT:  none, checks argv for arguments supplied via CLI
         OUTPUT:  three-item dictionary containing the mode type, tool name, and command/action number """

    if argv.__len__() < 2:
        return {"mode": None, "tool": None, "num": None}

    elif argv.__len__() > 4:
        axiom_help()
        exit(1)

    elif argv.__len__() == 2:

        if argv[1] == "init":
            return {"mode": "init", "tool": None, "num": None}
        if argv[1] == "reload":
            return {"mode": "reload", "tool": None, "num": None}
        if argv[1] in ["n", "ne", "new", "-n", "--new"]:
            return {"mode": "new", "tool": None, "num": None}
        else:
            axiom_help()
            exit(1)

    elif argv.__len__() == 3 or 4:

        if argv[1] == "init":
            return {"mode": "init", "tool": str(argv[2]), "num": None}
        if argv[1] in ["s", "sh", "sho", "show", "-s", "--show"]:
            if argv.__len__() == 3:
                return {"mode": "show", "tool": str(argv[2]), "num": None}
            if argv.__len__() == 4:
                try:
                    number = int(argv[3])
                except (ValueError, TypeError):
                    number = -1
                return {"mode": "show", "tool": str(argv[2]), "num": number}

        if argv[1] in ["r", "ru", "run", "-r", "--run"]:
            if argv.__len__() == 3:
                return {"mode": "run", "tool": str(argv[2]), "num": None}
            if argv.__len__() == 4:
                try:
                    number = int(argv[3])
                except (ValueError, TypeError):
                    number = -1
                return {"mode": "run", "tool": str(argv[2]), "num": number}

        if argv[1] in ["b", "bu", "bui", "buil", "build", "-b", "--build"]:
            if argv.__len__() == 3:
                return {"mode": "build", "tool": str(argv[2]), "num": None}
            if argv.__len__() == 4:
                try:
                    number = int(argv[3])
                except (ValueError, TypeError):
                    number = -1
                return {"mode": "build", "tool": str(argv[2]), "num": number}

        else:
            axiom_help()
            exit(1)

    else:
        axiom_help()
        exit(1)


def get_input_types(input_types_list, text):
    """ SUMMARY:  parses placeholder text to determine the type of input required for command/action execution
          INPUT:  1) list of all possible input types (strings), and 2) the command text (list or str)
         OUTPUT:  a list of strings """

    if isinstance(text, list):
        temporary_string = ""
        line_count = 0
        while line_count < text.__len__():
            temporary_string += text[line_count]
            line_count += 1
        text = temporary_string

    used_input_types = []
    end = text.__len__()
    indices = [i for i in range(end) if text.startswith("{", i)]
    hit_count = 0

    while hit_count < indices.__len__():
        min_beginning = indices[hit_count]
        if min_beginning + 10 > end:
            max_ending = end
        else:
            max_ending = min_beginning + 10

        target = text[min_beginning:max_ending]

        for entry in input_types_list:
            if str(entry + "}") in target:
                used_input_types.append(entry)
                break

        hit_count += 1

    return used_input_types


def get_tool_names(tool_list):
    """ SUMMARY:  creates a list (set) of unique tool names for searching, auto-suggestion, etc.
          INPUT:  a list of two-item tuple (tool, platform)
         OUTPUT:  a de-duplicated list (set) of tool names """

    tool_names = []
    for x in tool_list:
        tool_names.append(x[0])

    return set(tool_names)


def initialize(settings):
    """ SUMMARY:  installs PTF + toolkits, optionally downloads/loads user-supplied config file (overwriting existing)
          INPUT:  three-item settings dictionary
         OUTPUT:  no return values, modifies the filesystem and global config variable """

    print("Initializing...")

    if isinstance(settings.get("tool"), str):
        config_yaml_url = str(settings.get("tool"))

        print("Downloading configuration file...")

        try:
            request = get(config_yaml_url)

        except RequestException:
            print_error(str("ERROR: Cannot download configuration file from " + config_yaml_url))
            exit(1)

        else:
            if request.status_code == 200:
                try:
                    remove(config.axiom.config_file)
                    with open(config.axiom.config_file, 'wb') as config_file:
                        config_file.write(request.content)

                except OSError:
                    print_error("ERROR: Cannot replace existing configuration file")
                    exit(1)

                else:
                    config.axiom = config.AxiomConfig(config.axiom.config_file)
                    setup_ptf()
                    setup_toolkits()

            else:
                print_error("ERROR: Configuration file download failure")
                exit(1)

    elif settings.get("tool") is None:
        setup_ptf()
        setup_toolkits()

    else:
        print_error("ERROR: Invalid configuration file URL")
        exit(1)


def load_commands(yam, inputs_pattern, input_types_list):
    """ SUMMARY:  creates all command and action objects for a given tool file's YAML data
          INPUT:  1) a list of 2 dicts from the source YAML file, 2) a regex pattern (str), and 3) a list of strings
         OUTPUT:  a two-item tuple of 1) a list of AxiomCommand objects and 2) a list of AxiomAction objects """

    total = yam[1]['commands'].__len__()
    command_list = []
    action_list = []
    tool_string = ""

    i = 0
    while i < total:
        current_cmd = yam[1]['commands'][i]
        name = str(list(current_cmd.keys())[0])

        for x in command_list:
            if x.name == name:
                tool_string = str(yam[0]["name"] + " (" + yam[0]["os"] + ") ")
                print_error(str("ERROR: " + tool_string + "contains non-unique command name \"" + name + "\""))
                exit(1)

        for y in action_list:
            if y.name == name:
                tool_string = str(yam[0]["name"] + " (" + yam[0]["os"] + ") ")
                print_error(str("ERROR: " + tool_string + "contains non-unique action name \"" + name + "\""))
                exit(1)

        prompt_type = str(list(list(current_cmd.values())[0][0].values())[0][0])
        execution_type = str(list(list(current_cmd.values())[0][0].values())[0][1])
        text = list(list(current_cmd.values())[0][1].values())[0]
        note = str(list(list(current_cmd.values())[0][4].values())[0])

        raw_output_list = list(list(current_cmd.values())[0][3].values())[0]
        output_list = None
        if raw_output_list:
            output_list = load_outputs(raw_output_list, tool_string)

        raw_input_list = list(list(current_cmd.values())[0][2].values())[0]
        if raw_input_list:

            tokens, input_list = load_text_and_inputs(text, inputs_pattern, input_types_list, raw_input_list)
            command_list.append(AxiomCommand(name, prompt_type, execution_type, tokens, output_list, note, input_list))

        else:
            action_list.append(AxiomAction(name, prompt_type, execution_type, text, output_list, note))

        i += 1

    return command_list, action_list


def load_inventory():
    """ SUMMARY:  instantiates the runtime toolkits that organize all tools and their commands/actions
          INPUT:  none
         OUTPUT:  a list of AxiomToolkit objects """

    loadable_inventory_file = str(config.axiom.binary_folder + "/inventory.axiom")
    if path.exists(loadable_inventory_file):
        try:
            with open(loadable_inventory_file, 'rb') as inventory_dump:
                toolkits = load(inventory_dump)

        except (OSError, PickleError):
            print_error(str("ERROR: Failed to load inventory binary file " + loadable_inventory_file))
            exit(1)
        else:
            return toolkits

    folders = []
    if path.exists(config.axiom.inventory_folder):
        folders = listdir(config.axiom.inventory_folder)
    else:
        print_error(str("ERROR: Inventory folder " + config.axiom.inventory_folder + " not found"))
        exit(1)

    toolkits = []

    for i in range(folders.__len__()):
        kit_name = folders[i]
        kit_folder = str(config.axiom.inventory_folder + "/" + kit_name)
        tool_list = []

        for filename in listdir(kit_folder):
            current_file = str(kit_folder + "/" + filename)
            if current_file.endswith(".yml"):
                try:
                    with open(current_file, 'r') as tool_file:
                        tool_yaml = list(safe_load_all(tool_file))[0]
                        tool_name = tool_yaml["name"]
                        tool_platform = tool_yaml["os"]
                        tool_list.append((tool_name, tool_platform))

                except (OSError, parser.ParserError, scanner.ScannerError):
                    print_error(str("ERROR: Failed to load " + current_file))
                    exit(1)

        tool_list = set(tool_list)
        toolkits.append(AxiomToolkit(kit_name, kit_folder, tool_list))

    try:
        with open(loadable_inventory_file, 'wb') as inventory:
            dump(toolkits, inventory)

    except (OSError, PickleError):
        print_error(str("ERROR: Failed to save inventory binary file " + loadable_inventory_file))
        exit(1)

    return toolkits


def load_outputs(raw_output_list, tool):
    """ SUMMARY:  retrieves a list of values representing each command/action output
          INPUT:  1) a list of outputs (str) taken directly from a YAML file 2) the target tool (str)
         OUTPUT:  a list of two-item tuples """

    output_list = []

    output_count = 0

    try:
        while output_count < raw_output_list.__len__():
            current_output = raw_output_list[output_count]

            if isinstance(current_output, dict):

                if list(current_output)[0] == "FILE":

                    if list(list(current_output.values())[0].keys())[0] == "input":
                        output_list.append(("F_INPUT", int(list(list(current_output.values())[0].values())[0])))

                    elif list(list(current_output.values())[0].keys())[0] == "string":
                        output_list.append(("F_STRING", str(list(list(current_output.values())[0].values())[0])))

                    elif list(list(current_output.values())[0].keys())[0] == "prefix":
                        input_number = int(list(list(current_output.values())[0].values())[0][0])

                        if isinstance(list(list(current_output.values())[0].values())[0][1], str):  # single extension
                            extension_string = str(list(list(current_output.values())[0].values())[0][1])
                            output_list.append(("F_PREFIX", (input_number, extension_string)))

                        elif isinstance(list(list(current_output.values())[0].values())[0][1], list):  # >1 extensions
                            prefix_count = 0
                            while prefix_count <= list(list(current_output.values())[0].values())[0][0]:
                                extension_string = str(list(list(
                                    current_output.values())[0].values())[0][1][prefix_count])
                                output_list.append(("F_PREFIX", (input_number, extension_string)))
                                prefix_count += 1

                elif list(current_output)[0] == "PROMPT":
                    output_list.append(("PROMPT", str(list(current_output.values())[0])))

            else:
                output_list.append(str(current_output))

            output_count += 1

    except (AttributeError, IndexError, KeyError, TypeError, ValueError):
        print_error(str("ERROR: Invalid outputs defined for " + tool))
        exit(1)

    return output_list


def load_text_and_inputs(text, inputs_pattern, input_types_list, raw_input_list):
    """ SUMMARY:  retrieves executable command/action text (tokens) and the inputs required at execution
          INPUT:  1) command text (str), 2) regex pattern (str), 3) list of types (list), and 4) list of inputs (list)
         OUTPUT:  a two-item tuple containing 1) a list of strings and 2) a list of 2-item or 3-item tuples """

    used_input_types = get_input_types(input_types_list, text)
    tokens = []

    if isinstance(text, str):
        tokens = list(split(inputs_pattern, text))
    elif isinstance(text, list):
        line_count = 0
        while line_count < text.__len__():
            current_line = text[line_count]
            tokens.append(list(split(inputs_pattern, current_line)))
            line_count += 1

    input_list = []
    input_count = 0
    while input_count < raw_input_list.__len__():
        current_input = raw_input_list[input_count]
        current_type = used_input_types[input_count]
        if isinstance(current_input, str):
            input_list.append(tuple((current_input, current_type)))
        elif isinstance(current_input, dict):
            current_name = list(current_input.keys())[0]
            current_options = list(current_input.values())[0]
            input_list.append(tuple((current_name, current_type, current_options)))

        input_count += 1

    return tokens, input_list


def load_tool_list(inventory):
    """ SUMMARY:  creates a de-duplicated list of all tools present in all toolkits
          INPUT:  a list of AxiomToolkit objects
         OUTPUT:  a list of two-item tuples (tool, platform) """

    loadable_list_file = str(config.axiom.binary_folder + '/tool_list.axiom')
    if path.exists(loadable_list_file):
        try:
            with open(loadable_list_file, 'rb') as list_dump:
                loaded_list = load(list_dump)

        except (OSError, PickleError):
            print_error(str("ERROR: Failed to load tool list binary file " + loadable_list_file))
            exit(1)

        else:
            return loaded_list

    master_tool_list = []

    for i in range(inventory.__len__()):
        for x in inventory[i].tool_name_list:
            master_tool_list.append(x)

    master_tool_list = set(master_tool_list)

    try:
        with open(loadable_list_file, 'wb') as tool_list:
            dump(list(master_tool_list), tool_list)

    except (OSError, PickleError):
        print_error(str("ERROR: Failed to save tool list binary file " + loadable_list_file))
        exit(1)

    return list(master_tool_list)


def load_tools(inventory, unloaded_tools):
    """ SUMMARY:  imports all tool data from all YAML files from all inventory folders
          INPUT:  1) a list of AxiomToolkit objects, and 2) a list of two-item tuples (tool, platform)
         OUTPUT:  a list of AxiomTool objects """

    loadable_tools_file = str(config.axiom.binary_folder + "/tools.axiom")
    if path.exists(loadable_tools_file):
        try:
            with open(loadable_tools_file, 'rb') as tools_dump:
                loaded_tools = load(tools_dump)

        except (OSError, PickleError):
            print_error(str("ERROR: Failed to load tools binary file " + loadable_tools_file))
            exit(1)

        else:
            return loaded_tools

    tools = []

    for i in range(len(inventory)):
        folder = inventory[i].location

        for filename in listdir(folder):
            current_file = str(folder + "/" + filename)

            if current_file.endswith(".yml"):
                try:
                    with open(current_file, 'r') as tool_file:
                        tool = list(safe_load_all(tool_file))
                        current_tool = (tool[0]["name"], tool[0]["os"])

                        if current_tool in unloaded_tools:
                            command_list, action_list = load_commands(tool, config.axiom.inputs_pattern,
                                                                      config.axiom.input_types_list)
                            tools.append(AxiomTool(tool[0]["name"], tool[0]["os"], tool[0]["ptf_module"],
                                                   tool[0]["description"], action_list, command_list))
                            unloaded_tools.remove(current_tool)
                        else:
                            tool_id = resolve_tool_id(current_tool, tools)
                            if able_to_merge(tool, tool_id, tools):
                                if merge(tool, tool_id, tools, config.axiom.inputs_pattern,
                                         config.axiom.input_types_list):
                                    continue
                                else:
                                    print_error(str("ERROR: Merge failure for " + str(tool[0]["name"]) + " from " +
                                                    str(current_file)))
                                    exit(1)
                            else:
                                print_error(str("ERROR: Unable to merge " + str(tool[0]["name"]) + " from " +
                                                str(current_file)))
                                exit(1)

                except (AttributeError, IndexError, KeyError, OSError, TypeError, ValueError):
                    print_error(str("ERROR: Failed to load " + current_file))
                    exit(1)

    for item in tools:
        item.initialize_combined_list()

    try:
        with open(loadable_tools_file, 'wb') as axiom:
            dump(tools, axiom)

    except (OSError, PickleError):
        print_error(str("ERROR: Failed to save tools binary file " + loadable_tools_file))
        exit(1)

    return tools


def merge(tool, tool_id, tools, inputs_pattern, input_types_list):
    """ SUMMARY:  merges new commands/actions into existing AxiomTool objects
          INPUT:  1) list of two dictionaries 2) tool ID value (int) 3) list of AxiomTool objects
                  4) regex pattern (str) and 5) list of strings
         OUTPUT:  Returns True after completing merge procedure """

    command_list, action_list = load_commands(tool, inputs_pattern, input_types_list)
    action_count = 0
    command_count = 0

    if action_list.__len__() > 0:
        while action_count < action_list.__len__():
            tools[tool_id].action_list.append(action_list[action_count])
            action_count += 1

    if command_list.__len__() > 0:
        while command_count < command_list.__len__():
            tools[tool_id].command_list.append(command_list[command_count])
            command_count += 1

    return True


def new_generate_command():
    """ SUMMARY:  prompts user with data entry questions and prints a complete and valid YAML snippet to the screen
          INPUT:  none
         OUTPUT:  none, prints to the screen and exits """

    name = prompt("[AXIOM] Enter command name: ")

    prompt_selection = new_get_prompt_selection()
    execution_type = new_get_execution_type(prompt_selection)
    text = new_get_text()
    inputs = new_get_inputs(text)
    outputs = new_get_outputs(execution_type, text)

    note = prompt("[AXIOM] Enter command note: ")

    name = new_get_escaped_text(name)
    note = new_get_escaped_text(note)

    new_print_finalized_command_text(name, prompt_selection, execution_type, text, inputs, outputs, note)

    exit(0)


def new_get_escaped_text(text):
    """ SUMMARY:  replaces any backslash and double-quote characters with backslash-escaped character sequences
          INPUT:  command text line(s) (list or str)
         OUTPUT:  returns backslash-escaped command text (list or str) """

    if isinstance(text, list):
        new_list = []
        for line in range(text.__len__()):
            new_list.append(text[line].replace("\\", "\\\\").replace("\"", "\\\""))
        return new_list

    else:
        return text.replace("\\", "\\\\").replace("\"", "\\\"")


def new_get_execution_type(prompt_selection):
    """ SUMMARY:  prompts user to enter the command execution type
          INPUT:  the current command's prompt type (str)
         OUTPUT:  returns the execution type name (str) """

    if prompt_selection == "other":
        return "NX"

    print("\nExecution Types\n")

    print("  1\tstandalone")
    print("  2\tautonomous")
    print("  3\tinteractive")
    print("  4\tNX")

    number = prompt("\n[AXIOM] Select an option: ")

    try:
        number = int(number)
        if number == 1:
            return "standalone"
        elif number == 2:
            return "autonomous"
        elif number == 3:
            return "interactive"
        elif number == 4:
            return "NX"
        else:
            print_error("ERROR: Invalid execution type selection")
            exit(1)

    except (ValueError, TypeError):
        print_error("ERROR: Invalid execution type selection")
        exit(1)


def new_get_inputs(text):
    """ SUMMARY:  prompts user to enter input descriptions and related data
          INPUT:  the command text (list or str)
         OUTPUT:  returns the inputs text line (str) """

    inputs = "["

    used_input_types = get_input_types(config.axiom.input_types_list, text)
    input_count = used_input_types.__len__()

    for i in range(input_count):
        description = prompt(str("[AXIOM] Enter name for input " +
                                 str("(" + str(i + 1) + "/" + str(input_count) + ")") +
                                 " {" + used_input_types[i] + "}: "))
        description = new_get_escaped_text(description)

        if used_input_types[i] in ["INTMENU", "STRMENU"]:
            option_count = prompt(str("[AXIOM] Enter number of \"" + description + "\" options: "))
            try:
                option_count = int(option_count)
                if option_count <= 0:
                    print_error("ERROR: Invalid number of options")
                    exit(1)
                option_text = "["
            except (ValueError, TypeError):
                print_error("ERROR: Invalid number of options")
                exit(1)

            if used_input_types[i] == "INTMENU":
                for x in range(option_count):
                    single_option = prompt(str("[AXIOM] Enter \"" + description + "\" option (" +
                                               str(x + 1) + "/" + str(option_count) + ") {INT}: "))
                    try:
                        single_option = int(single_option)
                    except (ValueError, TypeError):
                        print_error("ERROR: Invalid integer option")
                        exit(1)

                    option_text = str(option_text + str(single_option) + ",")
                option_text = str(option_text[:-1] + "]")

            elif used_input_types[i] == "STRMENU":
                for x in range(option_count):
                    single_option = prompt(str("[AXIOM] Enter \"" + description + "\" option (" +
                                               str(x + 1) + "/" + str(option_count) + ") {STR}: "))
                    single_option = new_get_escaped_text(single_option)

                    option_text = str(option_text + "\"" + str(single_option) + "\"" + ",")
                option_text = str(option_text[:-1] + "]")

            inputs = str(inputs + "{\"" + description + "\":" + option_text + "},")

        else:

            inputs = str(inputs + "\"" + description + "\",")

    if inputs == "[":
        return "null"
    else:
        inputs = str(inputs[:-1] + "]")
        return inputs


def new_get_output_details(input_count, current_output_index, output_count):
    """ SUMMARY:  prompts user to select output type and enter type-specific details
          INPUT:  1) number of total inputs (int) 2) current output number (int) 3) total number of outputs (int)
         OUTPUT:  returns the outputs text line (str) """

    print(str("[AXIOM] Select output type for remaining output (" +
              str(current_output_index + 1) + "/" + str(output_count) + "): "))
    print("\nOutput Types\n")

    print("  1\tFile (input)\tfilename is entirely user-controlled command input")
    print("  2\tFile (prefix)\tfilename prefix is command input, file extension(s) hardcoded")
    print("  3\tFile (string)\tfilename is entirely hardcoded")
    print("  4\tSTDERR\t\tstandard error")

    number = prompt("\n[AXIOM] Select an option: ")

    try:
        number = int(number)
        if number == 1:
            if input_count <= 0:
                print_error("ERROR: Output type requires at least one command input")
                exit(1)
            input_number = prompt("[AXIOM] Enter the corresponding input number: ")
            input_number = int(input_number)
            if int(input_number - 1) in range(input_count):
                return str("{\"FILE\":{\"input\":" + str(input_number) + "}}")
            else:
                print_error("ERROR: Invalid input number")
                exit(1)

        elif number == 2:
            if input_count <= 0:
                print_error("ERROR: Output type requires at least one command input")
                exit(1)
            extensions = ""
            entry = prompt("[AXIOM] Enter the corresponding input number: ")
            entry = int(entry)
            if int(entry - 1) in range(input_count):
                extension_count = prompt("[AXIOM] Enter number of file extensions: ")
                extension_count = int(extension_count)
                if extension_count > 0:
                    for e in range(extension_count):
                        current_ext = prompt("[AXIOM] Enter file extension (" +
                                             str(e + 1) + "/" + str(extension_count) + "): ")
                        current_ext = new_get_escaped_text(current_ext)
                        extensions = str(extensions + "\"" + current_ext + "\",")
                    extensions = extensions[:-1]
                    return str("{\"FILE\":{\"prefix\":[" + str(entry) + "," + extensions + "]}}")
                else:
                    print_error("ERROR: Invalid number of file extensions")
                    exit(1)
            else:
                print_error("ERROR: Invalid input number")
                exit(1)

        elif number == 3:
            filename = prompt("[AXIOM] Enter the output filename: ")
            filename = new_get_escaped_text(filename)
            return str("{\"FILE\":{\"string\":\"" + str(filename) + "\"}}")

        elif number == 4:
            return "\"STDERR\""

        else:
            print_error("ERROR: Invalid output type selection")
            exit(1)

    except (ValueError, TypeError):
        print_error("ERROR: Invalid number entered")
        exit(1)


def new_get_outputs(execution_type, text):
    """ SUMMARY:  prompts user to enter output data
          INPUT:  1) command execution type name (str) 2) command text (list or str)
         OUTPUT:  returns completed outputs text line (str) """

    input_count = get_input_types(config.axiom.input_types_list, text).__len__()
    outputs = "["

    answer = prompt("[AXIOM] Does command output to STDOUT? [Y/n] ")
    if answer not in ["Y", "y", "Yes", "yes"]:
        pass
    else:
        outputs = "[\"STDOUT\","

    if execution_type == "interactive":
        print("[AXIOM] Select prompt type emitted by interactive command: ")
        prompt_type = new_get_prompt_selection()
        if outputs == "[\"STDOUT\",":
            outputs = str("[\"STDOUT\"," + "{\"PROMPT\":\"" + prompt_type + "\"},")
        else:
            outputs = str("[{\"PROMPT\":\"" + prompt_type + "\"},")

    output_count = prompt("[AXIOM] Enter number of remaining outputs: ")

    try:
        output_count = int(output_count)

    except (ValueError, TypeError):
        print_error("ERROR: Invalid number of outputs")
        exit(1)

    if output_count <= 0:
        if outputs == "[":
            return "null"
        else:
            return str(outputs[:-1] + "]")

    for y in range(output_count):
        outputs = str(outputs + new_get_output_details(input_count, y, output_count) + ",")

    return str(outputs[:-1] + "]")


def new_get_prompt_selection():
    """ SUMMARY:  prompts user to select command prompt type
          INPUT:  none, gets input from user
         OUTPUT:  returns a prompt name from the global config (str) """

    print("\nPrompts\n")

    for i in range(config.axiom.prompts.__len__()):
        print("  " + str(i + 1) + "\t" + str(config.axiom.prompts[i][0]))

    number = prompt("\n[AXIOM] Select an option: ")

    try:
        number = int(number)
        if int(number - 1) in range(config.axiom.prompts.__len__()):
            return config.axiom.prompts[number - 1][0]

        else:
            print_error("ERROR: Invalid prompt selection")
            exit(1)

    except (ValueError, TypeError):
        print_error("ERROR: Invalid prompt selection")
        exit(1)


def new_get_text():
    """ SUMMARY:  prompts user for number of command text lines and the line contents
          INPUT:  none, gets input from the user
         OUTPUT:  returns completed and sanitized command text (list or str) """

    line_count = prompt("[AXIOM] Enter number of text input lines: ")

    try:
        line_count = int(line_count)
    except (ValueError, TypeError):
        print_error("ERROR: Invalid number of lines")
        exit(1)

    if line_count <= 0:
        print_error("ERROR: Invalid number of lines")
        exit(1)

    elif line_count == 1:
        text = prompt("[AXIOM] Enter command text: ")

    else:
        text = []
        for i in range(line_count):
            text.append(prompt(str("[AXIOM] Enter command text (line " + str(i + 1) + "): ")))

    return new_get_escaped_text(text)


def new_print_finalized_command_text(name, prompt_selection, execution_type, text, inputs, outputs, note):
    """ SUMMARY:  prints newly-generated YAML text to the screen
          INPUT:  seven variables generated by related functions, all are strings but "text" can also be a list
         OUTPUT:  none, only prints to the screen """

    print()

    print("  - \"" + name + "\":")
    print("    - type: [\"" + prompt_selection + "\",\"" + execution_type + "\"]")

    if isinstance(text, str):
        print("    - text: \"" + text + "\"")
    else:
        print("    - text:")
        for i in range(text.__len__()):
            print("      - \"" + text[i] + "\"")

    print("    - input: " + inputs + "")
    print("    - output: " + outputs + "")
    print("    - note: \"" + note + "\"")

    print()


def print_banner(banner_file):
    """ SUMMARY:  displays ASCII art from file and other introductory info
          INPUT:  filename (str) of text file on filesystem
         OUTPUT:  none, only prints to screen """

    try:
        with open(banner_file, 'r') as file:
            data = file.readlines()
            for line in data:
                print(Fore.RED + line.replace('\n', ''))

        print(Style.RESET_ALL, end='')

    except OSError:
        print_error(str("ERROR: Unable to access banner file " + banner_file))
        exit(1)

    else:
        print("   C9EE FD5E 15DA 9C02 1B0C  603C A397 0118 D56B 2E35   ")
        print()
        print("    Created by Mike Iacovacci    https://payl0ad.run     ")
        print()
        print()


def print_stats(inventory, tool_list, tools):
    """ SUMMARY:  displays counts of loaded tools, commands/actions, and toolkits
          INPUT:  1) list of AxiomToolkit objects objects 2) de-deplicated list of tuples 3) list of AxiomTool objects
         OUTPUT:  none, only prints to the screen """

    action_count = 0
    command_count = 0
    for tool in tools:
        current_actions = tool.action_list.__len__()
        current_commands = tool.command_list.__len__()
        action_count = action_count + current_actions
        command_count = command_count + current_commands

    combined_count = str(action_count + command_count)

    tool_count = str(tool_list.__len__())
    toolkit_count = str(inventory.__len__())

    print("\n" + "Loaded " +
          combined_count + " commands for " +
          tool_count + " unique tools from " +
          toolkit_count + " toolkits."
                          "\n")


def reload():
    """ SUMMARY:  deletes and recreates binary folder causing all YAML tool files to be deserialized again
          INPUT:  none
         OUTPUT:  none """

    print("Reloading...")

    delete_and_recreate_folder(config.axiom.binary_folder)


def resolve_tool_id(potential_tool, tools):
    """ SUMMARY:  searches for a tool's ID number using a user-supplied tool name string
          INPUT:  1) a tool name (str), and 2) a list of AxiomTool objects
         OUTPUT:  a tool ID value (int) or -1 if no match is found """

    tool_id = 0
    while tool_id < tools.__len__():
        if tools[tool_id].name == potential_tool[0] and tools[tool_id].platform == potential_tool[1]:
            return tool_id
        tool_id += 1

    return -1


def set_user_expectations(settings):
    """ SUMMARY:  prints a message so the user expects to wait while the YAML is deserialized
          INPUT:  three-item settings dictionary
         OUTPUT:  no return value, only prints to the screen conditionally """

    if path.exists(str(config.axiom.binary_folder + "/inventory.axiom")) and \
            path.exists(str(config.axiom.binary_folder + "/tool_list.axiom")) and \
            path.exists(str(config.axiom.binary_folder + "/tools.axiom")) or \
            settings.get("mode") in ["init", "reload"]:
        return
    else:
        print("Initializing...")


def setup_folders(settings):
    """ SUMMARY:  initializes folders for history/binary files and installs PTF if missing
          INPUT:  three-item settings dictionary
         OUTPUT:  none, causes filesystem modifications within user-defined locations """

    set_user_expectations(settings)

    create_missing_folder(config.axiom.history_folder)
    create_missing_folder(config.axiom.binary_folder)

    if not path.exists(config.axiom.ptf_folder):
        setup_ptf()
    if not path.exists(config.axiom.inventory_folder):
        setup_toolkits()


def setup_ptf():
    """ SUMMARY:  deletes existing PTF folder and downloads/installs the latest version from GitHub master branch
          INPUT:  none
         OUTPUT:  no return values, modifies the filesystem """

    download_and_extract_zip("https://github.com/trustedsec/ptf/archive/master.zip",
                             "ptf-master",
                             config.axiom.ptf_folder,
                             "The PenTesters Framework (PTF)")


def setup_toolkits():
    """ SUMMARY:  deletes existing inventory folder, downloads all listed toolkits, and reloads the binary data
          INPUT:  none
         OUTPUT:  no return values, modifies the filesystem """

    delete_and_recreate_folder(config.axiom.inventory_folder)

    for toolkit in config.axiom.toolkits:
        download_and_extract_zip(toolkit[2],
                                 toolkit[1],
                                 str(config.axiom.inventory_folder + "/" + toolkit[0]),
                                 toolkit[0])

    reload()


def tool_selection_prompt(tool_list, tool_names, tools):
    """ SUMMARY:  prompts user to select a tool, provides a fuzzy word completer interface
          INPUT:  1) list of two-item tuples (name, platform), 2) set of tool names, and 3) list of AxiomTool objects
         OUTPUT:  exit value (int) """

    tool_names = FuzzyCompleter(WordCompleter(tool_names))

    completer_style = ptkStyle.from_dict({
        "completion-menu": "bg:#111111",
        "scrollbar.background": "bg:#111111",
        "scrollbar.button": "bg:#999999",
        "completion-menu.completion.current": "nobold bg:ansired",
        "completion-menu.completion fuzzymatch.outside": "nobold fg:#AAAAAA",
        "completion-menu.completion fuzzymatch.inside": "nobold fg:ansired",
        "completion-menu.completion fuzzymatch.inside.character": "nobold nounderline fg:ansired",
        "completion-menu.completion.current fuzzymatch.outside": "nobold fg:#AAAAAA",
        "completion-menu.completion.current fuzzymatch.inside": "nobold fg:#AAAAAA",
        "completion-menu.completion.current fuzzymatch.inside.character": "nobold nounderline fg:#AAAAAA"})

    while True:
        text = prompt('[AXIOM] Enter tool: ', completer=tool_names, complete_while_typing=True, style=completer_style)

        if text == "exit" or text == "quit":
            return 0
        if text == "":
            continue

        tool_id = disambiguate_tool_name(text, tool_list, tools)
        if tool_id < 0:
            print_error("ERROR: Invalid tool name")
        else:
            tool = tools[tool_id]
            command_selection_prompt(tool)

    return 1


def validate_privileges(mode):
    """ SUMMARY:  confirms effective root privilege level if writing to the filesystem or spawning a subprocess
          INPUT:  program mode type (str)
         OUTPUT:  none """

    if mode not in ["show", "new"]:
        if geteuid() != 0:
            print_error("ERROR: AXIOM requires root privileges")
            exit(1)
