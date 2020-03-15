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

import lib.config as config
from lib.config import print_error

from os import devnull, path
from pexpect import exceptions, pty_spawn
from prompt_toolkit import prompt, PromptSession
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.history import FileHistory
from queue import Queue
from re import search
from shlex import split
from subprocess import call, PIPE, Popen, STDOUT
from threading import Event
from time import sleep


class AxiomAction:
    """ A fully-completed, ready-to-execute tool command requiring no user input """

    def __init__(self, name, prompt_type, execution_type, text, output_list, note):
        self.execution_type = execution_type
        self.name = name
        self.note = note
        self.output_list = output_list
        self.prompt_type = prompt_type
        self.text = text

    def cli_print(self):
        """ SUMMARY:  displays the executable action text to the user, not stylized
              INPUT:  none, reads values from self
             OUTPUT:  none, only prints to the screen """

        print()

        if isinstance(self.text, str):
            print(self.text)
        elif isinstance(self.text, list):
            line = 0
            while line < self.text.__len__():
                print(self.text[line])
                line += 1

        print()

    def confirm_and_execute(self, tool):
        """ SUMMARY:  asks user to confirm execution of the command/action before proceeding
              INPUT:  AxiomTool object
             OUTPUT:  False if not confirmed, True if confirmed, after command/action executes """

        self.show()
        response = input("\n[AXIOM] Execute? [Y/n] ")

        if response not in ["Y", "y", "Yes", "yes"]:
            return False
        else:
            self.run(tool)
            return True

    def existing_subprocess(self):
        """ SUMMARY:  checks dispatch for existing subprocess with matching prompt type
              INPUT:  none, reads values from self
             OUTPUT:  True or False """

        i = 0
        while i < dispatch.subprocesses.__len__():
            if self.prompt_type == dispatch.subprocesses[i].current_prompt:
                return True
            i += 1

        return False

    def extract_ending_prompt(self):
        """ SUMMARY:  determines the ending prompt of interactive command/action by processing output_list items
              INPUT:  none, reads values from self
             OUTPUT:  string containing prompt name, empty string if not found, or False if not interactive """

        ending_prompt = str()

        if self.execution_type != "interactive":
            return False

        for x in self.output_list:
            if isinstance(x, tuple):
                if x[0] == "PROMPT":
                    ending_prompt = x[1]
                    break

        return ending_prompt

    def print_text(self):
        """ SUMMARY:  displays the executable action text to the user, stylized
              INPUT:  none, reads values from self
             OUTPUT:  none, only prints to the screen """

        if isinstance(self.text, str):
            print("\n  TEXT:  " + self.text)
        elif isinstance(self.text, list):
            print("\n  TEXT:  ", end="")
            print(self.text[0])
            line = 1
            while line < self.text.__len__():
                print("         " + self.text[line])
                line += 1

    def run(self, tool):
        """ SUMMARY:  checks if tool is compatible/installed and calls execution function for matching execution type
              INPUT:  AxiomTool object
             OUTPUT:  none """

        if self.prompt_type == "bash" and not self.existing_subprocess():

            if not tool.platform_matches():
                print_error(str("\nERROR: Cannot execute " + tool.name + " (" + tool.platform + ") on " +
                                config.axiom.platform))
                dispatch.continue_trigger.set()
                return

            if tool.is_installed():
                pass
            else:
                if tool.install():
                    self.show()
                    print()
                else:
                    if tool.proceed_despite_uninstalled():
                        pass
                    else:
                        dispatch.continue_trigger.set()
                        return

        elif self.prompt_type != "other" and not self.existing_subprocess():
            print_error("\nERROR: Prompt type incompatible with current runtime")
            dispatch.continue_trigger.set()
            return

        multiple_lines = False

        if isinstance(self, AxiomCommand):
            if isinstance(self.text[0], list):
                multiple_lines = True
        elif isinstance(self, AxiomAction):
            if isinstance(self.text, list):
                multiple_lines = True

        if self.execution_type == "standalone":
            if multiple_lines:
                self.run_multiline_standalone()
            else:
                self.run_standalone()
        elif self.execution_type == "autonomous":
            if multiple_lines:
                print_error("ERROR: Autonomous multi-line commands are unsupported")
            else:
                self.run_autonomous()
        elif self.execution_type == "interactive":
            self.run_interactive()
        elif self.execution_type == "NX":
            if multiple_lines:
                self.run_multiline_nx()
            else:
                self.run_nx()

    def run_autonomous(self):
        """ SUMMARY:  executes autonomous action as subprocess (blocking) or queues action as a task (if interactive)
              INPUT:  none, reads values from self
             OUTPUT:  no return values """

        if self.prompt_type == "bash" and not self.existing_subprocess():
            try:
                print()
                call(self.text, shell=True)

            except OSError:
                print_error("ERROR: Failed to execute via call()")

        else:
            dispatch.tasking.put(AxiomInteractiveTask(self.text, self.prompt_type, self.prompt_type))
            dispatch.monitor_task_queue()

        dispatch.continue_trigger.set()

    def run_interactive(self):
        """ SUMMARY:  creates and queues an AxiomInteractiveTask object for execution
              INPUT:  none, reads values from self
             OUTPUT:  no return values """

        ending_prompt = self.extract_ending_prompt()
        if ending_prompt is not False:
            dispatch.tasking.put(AxiomInteractiveTask(self.text, self.prompt_type, ending_prompt))
            dispatch.monitor_task_queue()

        dispatch.continue_trigger.set()

    def run_multiline_nx(self):
        """ SUMMARY:  prints multi-line action text to the screen
              INPUT:  none, reads values from self
             OUTPUT:  no return values, only prints to screen """

        print()
        line = 0
        while line < self.text.__len__():
            print(self.text[line])
            line += 1
        dispatch.continue_trigger.set()

    def run_multiline_standalone(self):
        """ SUMMARY:  executes multi-line action as subprocess or queues action execution as a task (if interactive)
              INPUT:  none, reads values from self
             OUTPUT:  none """

        if self.prompt_type == "bash" and not self.existing_subprocess():
            try:
                print()
                proc = Popen(["bash", "-i"], shell=True, stdin=PIPE, stdout=PIPE)

                i = 0
                while proc.returncode is None:
                    if i < self.text.__len__():
                        proc.stdin.write(self.text[i].encode())
                        proc.stdin.write("\n".encode())
                        proc.stdin.flush()
                        i += 1
                    else:
                        proc.stdin.close()

                    proc.poll()

            except OSError:
                print_error("ERROR: Failed to execute via Popen()")

        else:
            dispatch.tasking.put(AxiomInteractiveTask(self.text, self.prompt_type, self.prompt_type))
            dispatch.monitor_task_queue()

        dispatch.continue_trigger.set()

    def run_nx(self):
        """ SUMMARY:  prints single-line action text to the screen
              INPUT:  none, reads values from self
             OUTPUT:  no return values, only prints to screen """

        print()
        print(self.text)
        print()
        dispatch.continue_trigger.set()

    def run_standalone(self):
        """ SUMMARY:  executes action as a subprocess (blocking) or queues action execution as a task (if interactive)
              INPUT:  none, reads values from self
             OUTPUT:  none """

        if self.prompt_type == "bash" and not self.existing_subprocess():
            try:
                print()
                call(split(self.text))

            except OSError:
                print_error("ERROR: Failed to execute via call()")

        else:
            dispatch.tasking.put(AxiomInteractiveTask(self.text, self.prompt_type, self.prompt_type))
            dispatch.monitor_task_queue()

        dispatch.continue_trigger.set()

    def show(self):
        """ SUMMARY:  displays detailed information about the action to the user
              INPUT:  none, reads values from self
             OUTPUT:  none, only prints to the screen """

        print("\n  NAME:  " + self.name +
              "\n  TYPE:  " + self.execution_type + " action (" + self.prompt_type + ")"
              "\n  NOTE:  " + self.note)

        self.print_text()


class AxiomCommand(AxiomAction):
    """ The general syntax, including data-type placeholders, for an instruction to execute """

    def __init__(self, name, prompt_type, execution_type, text, output_list, note, input_list):
        """ SUMMARY:  creates AxiomCommand objects, inherits from AxiomAction class
              INPUT:  multiples values at instantiation
             OUTPUT:  none, instantiates AxiomCommand object """

        super().__init__(name, prompt_type, execution_type, text, output_list, note)
        self.input_list = input_list

    def build(self):
        """ SUMMARY:  interactively prompts user, possibly more than once, to enter/select all command input values
              INPUT:  none, reads values from self
             OUTPUT:  returns finalized command text, either a string or list of strings """

        input_count = 0

        if isinstance(self.text[0], str):
            token_count = 0
            built_text = str()
            while token_count < self.text.__len__() or input_count < self.input_list.__len__():
                if token_count < self.text.__len__():
                    built_text += self.text[token_count]
                    token_count += 1
                if input_count < self.input_list.__len__():
                    built_text += self.input_build_prompt(input_count)
                    input_count += 1
        else:
            built_text = []
            current_line = 0
            while current_line < self.text.__len__():
                line_tokens = self.text[current_line].__len__()
                current_token = 0
                line_inputs = line_tokens - 1
                current_input = 0
                built_line = str()
                while current_token < line_tokens or current_input < line_inputs:
                    if current_token < line_tokens:
                        built_line += self.text[current_line][current_token]
                        current_token += 1
                    if current_input < line_inputs:
                        built_line += self.input_build_prompt(input_count)
                        current_input += 1
                        input_count += 1
                built_text.append(built_line)
                current_line += 1

        return built_text

    def build_with_placeholders(self):
        """ SUMMARY:  creates command text containing placeholders for user preview before confirming execution
              INPUT:  none, reads values from self
             OUTPUT:  returns string or list of strings containing placeholders character sequences """

        input_count = 0

        if isinstance(self.text[0], str):
            token_count = 0
            built_text = str()
            while token_count < self.text.__len__() or input_count < self.input_list.__len__():
                if token_count < self.text.__len__():
                    built_text += self.text[token_count]
                    token_count += 1
                if input_count < self.input_list.__len__():
                    built_text += str("{" + self.input_list[input_count][1] + "}")
                    input_count += 1
        else:
            built_text = []
            current_line = 0
            while current_line < self.text.__len__():
                line_tokens = self.text[current_line].__len__()
                current_token = 0
                line_inputs = line_tokens - 1
                current_input = 0
                built_line = str()
                while current_token < line_tokens or current_input < line_inputs:
                    if current_token < line_tokens:
                        built_line += self.text[current_line][current_token]
                        current_token += 1
                    if current_input < line_inputs:
                        built_line += str("{" + self.input_list[input_count][1] + "}")
                        current_input += 1
                        input_count += 1
                built_text.append(built_line)
                current_line += 1

        return built_text

    def cli_print(self):
        """ SUMMARY:  prints command text to the screen (not stylized), overrides inherited AxiomAction function
              INPUT:  none, reads values from self
             OUTPUT:  none, only prints to the screen """

        text = self.build()

        print()

        if isinstance(text, str):
            print(text)
        elif isinstance(text, list):
            line = 0
            while line < text.__len__():
                print(text[line])
                line += 1

        print()

    def input_build_prompt(self, input_count):
        """ SUMMARY:  prompts user to enter, and auto-suggests, command inputs to replace placeholder values
              INPUT:  current command input number (int), also reads values from self
             OUTPUT:  returns a user-supplied or user-selected string value """

        input_type = self.input_list[input_count][1]
        prompt_text = str("[AXIOM] Enter " + self.input_list[input_count][0] + ": ")

        if input_type in ["STRMENU", "INTMENU"]:
            option_name = self.input_list[input_count][0]
            option_list = self.input_list[input_count][2]
            response = self.option_prompt(option_name, option_list)
            return response
        elif input_type in ["STR", "INT", "IPV4", "IPV6", "IPV4RNGE", "IPV6RNGE", "IPV4CIDR", "IPV6CIDR", "MAC", "FILE",
                            "RLATVPTH", "FULLPATH", "DOMAIN", "HTTPURL", "HTTPSURL", "WEBURL"]:

            if input_type == "HTTPSURL":
                history_file = str(config.axiom.history_folder + "/WEBURL" + ".axiom")
            else:
                history_file = str(config.axiom.history_folder + "/" + input_type + ".axiom")

            session = PromptSession(history=FileHistory(history_file))
            response = session.prompt(prompt_text, auto_suggest=AutoSuggestFromHistory())
            return response
        else:
            response = prompt(prompt_text)
            return response

    @staticmethod
    def option_prompt(option_name, option_list):
        """ SUMMARY:  infinite loop prompting user to select a listed STRMENU or INTMENU option
              INPUT:  option_name (str) and option_list (list) variables created from input_list values
             OUTPUT:  string value from the option corresponding to the user's selection """

        while True:
            print("\n" + option_name + "\n")

            count = 0
            while count < option_list.__len__():
                print("  " + str(count + 1) + "\t" + str(option_list[count]))
                count += 1

            number = prompt("\n[AXIOM] Select an option: ")

            try:
                number = int(number)
                number -= 1
            except (ValueError, TypeError):
                number = -1

            if 0 <= number < option_list.__len__():
                return option_list[number]

    def print_text(self):
        """ SUMMARY:  prints command text to the screen (stylized), overrides inherited AxiomAction function
              INPUT:  none, reads values from self
             OUTPUT:  none, only prints to the screen """

        text_with_placeholders = self.build_with_placeholders()
        if isinstance(text_with_placeholders, str):
            print("\n  TEXT:  " + text_with_placeholders)
        elif isinstance(text_with_placeholders, list):
            print("\n  TEXT:  ", end="")
            print(text_with_placeholders[0])
            line = 1
            while line < text_with_placeholders.__len__():
                print("         " + text_with_placeholders[line])
                line += 1

    def run_autonomous(self):
        """ SUMMARY:  builds and runs command as subprocess (blocking) or queues task for interactive execution
                      overrides inherited AxiomAction function
              INPUT:  none, reads values from self
             OUTPUT:  none """

        text = self.build()
        if self.prompt_type == "bash" and not self.existing_subprocess():
            try:
                print()
                call(text, shell=True)

            except OSError:
                print_error("ERROR: Failed to execute via call()")

        else:
            dispatch.tasking.put(AxiomInteractiveTask(text, self.prompt_type, self.prompt_type))
            dispatch.monitor_task_queue()

        dispatch.continue_trigger.set()

    def run_interactive(self):
        """ SUMMARY:  builds command text and builds/queues interactive execution task
                      overrides inherited AxiomAction function
              INPUT:  none, reads values from self
             OUTPUT:  none """

        text = self.build()
        ending_prompt = self.extract_ending_prompt()
        if ending_prompt is not False:
            dispatch.tasking.put(AxiomInteractiveTask(text, self.prompt_type, ending_prompt))
            dispatch.monitor_task_queue()

        dispatch.continue_trigger.set()

    def run_multiline_nx(self):
        """ SUMMARY:  builds and prints multi-line command text to screen, overrides inherited AxiomAction function
              INPUT:  none, reads values from self
             OUTPUT:  no return values, only prints to screen """

        text = self.build()
        print()
        line = 0
        while line < self.text.__len__():
            print(text[line])
            line += 1
        dispatch.continue_trigger.set()

    def run_multiline_standalone(self):
        """ SUMMARY:  builds and executes command as subprocess or queues task for interactive execution
                      overrides inherited AxiomAction function
              INPUT:  none, reads values from self
             OUTPUT:  no return values """

        text = self.build()
        if self.prompt_type == "bash" and not self.existing_subprocess():
            try:
                print()
                proc = Popen(["bash", "-i"], shell=True, stdin=PIPE, stdout=PIPE)

                i = 0
                while proc.returncode is None:
                    if i < text.__len__():
                        proc.stdin.write(text[i].encode())
                        proc.stdin.write("\n".encode())
                        proc.stdin.flush()
                        i += 1
                    else:
                        proc.stdin.close()

                    proc.poll()

            except OSError:
                print_error("ERROR: Failed to execute via Popen()")
        else:
            dispatch.tasking.put(AxiomInteractiveTask(text, self.prompt_type, self.prompt_type))
            dispatch.monitor_task_queue()

        dispatch.continue_trigger.set()

    def run_nx(self):
        """ SUMMARY:  builds and displays command text to screen, overrides inherited AxiomAction function
              INPUT:  none, reads values from self
             OUTPUT:  no return values, only prints to the screen """

        text = self.build()
        print()
        print(text)
        print()
        dispatch.continue_trigger.set()

    def run_standalone(self):
        """ SUMMARY:  builds and executes command as subprocess (blocking) or queues interactive task for execution
                      overrides inherited AxiomAction function
              INPUT:  none, reads values from self
             OUTPUT:  no return values """

        text = self.build()
        if self.prompt_type == "bash" and not self.existing_subprocess():
            try:
                print()
                call(split(text))

            except OSError:
                print_error("ERROR: Failed to execute via call()")
        else:
            dispatch.tasking.put(AxiomInteractiveTask(text, self.prompt_type, self.prompt_type))
            dispatch.monitor_task_queue()

        dispatch.continue_trigger.set()

    def show(self):
        """ SUMMARY:  displays detailed information about the command, overrides inherited AxiomAction function
              INPUT:  none, reads values from self
             OUTPUT:  none, only prints to the screen """

        print("\n  NAME:  " + self.name +
              "\n  TYPE:  " + self.execution_type + " command (" + self.prompt_type + ")"
                                                                                      "\n  NOTE:  " + self.note)

        self.print_text()


class AxiomDispatcher:
    """ creates, manages, and interacts with subprocesses that require interactive input """

    def __init__(self):
        self.continue_trigger = Event()
        self.subprocesses = []
        self.tasking = Queue(maxsize=0)
        self.trigger = Event()

    def check_for_ambiguous_target(self, current_task):
        """ SUMMARY:  detects existing subprocesses with prompt types that match a task's ending prompt type
              INPUT:  current_task, an AxiomInteractiveTask object from the "tasking" queue
             OUTPUT:  True or False """

        prompt_type = current_task.ending_prompt

        for x in self.subprocesses:
            if x.current_prompt == prompt_type:
                return True

        return False

    @staticmethod
    def get_subprocess_output_detect_prompt(proc, pattern):
        """ SUMMARY:  prints subprocess output to the screen while searching for an interactive prompt
              INPUT:  1) a pseudoterminal subprocess object from pty_spawn and 2) a regex prompt pattern (str)
             OUTPUT:  no return values, only prints to the screen """

        timeout = 0
        safety_timer = 0

        while True:
            try:
                print(proc.readline().decode(), end='')
            except exceptions.TIMEOUT:
                if search(pattern, proc.before.decode()):
                    if timeout >= config.axiom.pattern_timeout:
                        print(proc.before.decode())
                        break
                    else:
                        timeout += 1
                        sleep(1)
                        continue
                else:
                    safety_timer += 1
                    sleep(1)
                    if safety_timer >= config.axiom.safety_timeout:
                        proc.sendline()
                    continue
            else:
                timeout = 0
                safety_timer = 0

    def handle_new_tasks(self):
        """ SUMMARY:  gets AxiomInteractiveTask objects from queue and routes tasks based on runtime context
              INPUT:  self, gets objects from "tasking" queue
             OUTPUT:  no return value, returns when task is routed """

        if not self.tasking.empty():
            current_task = self.tasking.get()
            if self.matching_subprocess(current_task) >= 0:
                target = self.matching_subprocess(current_task)
                if current_task.prompt_change:
                    if self.check_for_ambiguous_target(current_task):
                        print_error("\nERROR: Cannot create subprocess with same prompt type as existing subprocess")
                        self.tasking.task_done()
                        return
                self.read_and_transmit(target, current_task)
                self.tasking.task_done()
                return
            elif current_task.starting_prompt == "bash":
                if self.check_for_ambiguous_target(current_task):
                    print_error("\nERROR: Cannot create subprocess with same prompt type as existing subprocess")
                    self.tasking.task_done()
                    return
                self.spawn_and_transmit(current_task)
                self.tasking.task_done()
                return
            else:
                print_error("\nERROR: Prompt type incompatible with current runtime")
                self.tasking.task_done()
                return

    def matching_subprocess(self, current_task):
        """ SUMMARY:  locates existing subprocess with identical prompt type to queued task
              INPUT:  current_task, an AxiomInteractiveTask object from the "tasking" queue
             OUTPUT:  integer, zero or positive if match found, -1 if no match """

        i = 0
        while i < self.subprocesses.__len__():
            if current_task.starting_prompt == self.subprocesses[i].current_prompt:
                return i
            else:
                i += 1

        return -1

    def monitor_task_queue(self):
        """ calls any required functions related to new tasks in the queue """

        self.handle_new_tasks()

    def read_and_transmit(self, target, current_task):
        """ SUMMARY:  prints prior program output, transmits text to existing subprocess, and updates the prompt
              INPUT:  targeted subprocess number (INT) and AxiomInteractiveTask object from "tasking" queue
             OUTPUT:  no return values """

        proc = self.subprocesses[target].process

        while True:
            try:
                print(proc.readline().decode(), end='')
            except exceptions.TIMEOUT:
                break

        self.transmit_text(current_task, proc)

        self.subprocesses[target].current_prompt = current_task.ending_prompt
        self.subprocesses[target].prompt_pattern = current_task.ending_prompt_pattern
        dispatch.continue_trigger.set()

    def spawn_and_transmit(self, current_task):
        """ SUMMARY:  creates a new subprocess, transmits a command's/action's executable text, and updates the prompt
              INPUT:  an AxiomInteractiveTask object from the "tasking" queue
             OUTPUT:  no return values """

        try:
            self.subprocesses.append(AxiomExecutingSubprocess(current_task.starting_prompt,
                                                              pty_spawn.spawn("/bin/bash -i",
                                                                              timeout=config.axiom.pty_timeout)))

        except OSError:
            print_error("ERROR: Failed to spawn /bin/bash subprocess")
            exit(1)

        else:
            target = self.matching_subprocess(current_task)
            proc = self.subprocesses[target].process

            self.transmit_text(current_task, proc)

            self.subprocesses[target].current_prompt = current_task.ending_prompt
            self.subprocesses[target].prompt_pattern = current_task.ending_prompt_pattern
            dispatch.continue_trigger.set()

    def transmit_text(self, current_task, proc):
        """ SUMMARY:  transmits line-buffered input to a subprocess and waits for & displays the subprocess's output
              INPUT:  1) an AxiomInteractiveTask object and 2) a pseudoterminal subprocess object from pty_spawn
             OUTPUT:  no return values, only prints to the screen """

        pattern = str(current_task.ending_prompt_pattern + "$")

        try:
            if isinstance(current_task.text, str):
                proc.sendline(current_task.text)
            elif isinstance(current_task.text, list):
                i = 0
                while i < current_task.text.__len__():
                    proc.sendline(current_task.text[i])
                    i += 1

        except OSError:
            print_error("ERROR: Failed to transmit command")
            exit(1)

        else:
            self.get_subprocess_output_detect_prompt(proc, pattern)


class AxiomExecutingSubprocess:
    """ structure for managing subprocesses that require interactive input """

    def __init__(self, current_prompt, process):
        self.current_prompt = current_prompt
        self.process = process
        self.prompt_pattern = None


class AxiomInteractiveTask:
    """ defines tasks sent to AxiomDispatcher queue for working with interactive subprocesses """

    def __init__(self, text, starting_prompt, ending_prompt):
        """ SUMMARY:  creates object, to be queued, for handling interactive execution tasks
              INPUT:  the finalized command/action text (str or list), and starting + ending prompt type names
             OUTPUT:  self, instantiates an AxiomInteractiveTask object  """

        self.ending_prompt = ending_prompt
        self.starting_prompt = starting_prompt
        self.text = text

        self.prompt_change = self.detect_prompt_change()

        self.ending_prompt_pattern = self.resolve_ending_prompt_pattern()

    def detect_prompt_change(self):
        """ SUMMARY:  compares two prompt type names, called by AxiomInteractiveTask init method
              INPUT:  self, two string values that represent prompt type names
             OUTPUT:  True or False based on string comparison """

        if self.starting_prompt == self.ending_prompt:
            return False
        else:
            return True

    def resolve_ending_prompt_pattern(self):
        """ SUMMARY:  extracts ending prompt pattern from global config object
              INPUT:  self and global config object
             OUTPUT:  string containing the appropriate prompt pattern """

        if self.prompt_change:
            for x in config.axiom.prompts:
                if x[0] == self.ending_prompt:
                    return x[1]
        else:
            for x in config.axiom.prompts:
                if x[0] == self.starting_prompt:
                    return x[1]


class AxiomToolkit:
    """ A collection of related tools """

    def __init__(self, name, location, tool_name_list):
        self.location = location
        self.name = name
        self.tool_name_list = tool_name_list


class AxiomTool:
    """ an executable program with related commands and actions """

    def __init__(self, name, platform, ptf_module, description, action_list, command_list):
        self.action_list = action_list
        self.combined_list = []
        self.command_list = command_list
        self.description = description
        self.name = name
        self.platform = platform
        self.ptf_module = ptf_module

    def initialize_combined_list(self):
        """ SUMMARY:  creates alphabetically-ordered list of command/action names
              INPUT:  self, reads action_list and command_list variables
             OUTPUT:  none, modifies combined_list variable """

        self.combined_list = []
        x = 0
        while x < self.action_list.__len__():
            self.combined_list.append(self.action_list[x].name)
            x += 1
        y = 0
        while y < self.command_list.__len__():
            self.combined_list.append(self.command_list[y].name)
            y += 1

        self.combined_list = sorted(self.combined_list, key=str.casefold)

    def install(self):
        """ SUMMARY:  prompts user and installs undetected tools to local system via PTF when possible
              INPUT:  none, reads values from self & conditionally prompts user for interactive input
             OUTPUT:  True or False """

        if self.ptf_module not in ["", None]:
            answer = input("[AXIOM] Install " + self.name + " via PTF? [Y/n] ")
            if answer not in ["Y", "y", "Yes", "yes"]:
                return False
            else:
                if config.axiom.platform.lower() != "linux":
                    print_error(str("ERROR: Unable to run PTF on " + config.axiom.platform))
                    return False
                else:
                    input_text = str("python3 ./ptf --no-network-connection << EOF\n" +
                                     str("use " + self.ptf_module + "\n") +
                                     "install\n" +
                                     "EOF\n")
                    try:
                        call(input_text, shell=True, cwd=config.axiom.ptf_folder)
                        return True

                    except OSError:
                        print_error("ERROR: Failed to execute PTF")
                        exit(1)
        else:
            return False

    def is_installed(self):
        """ SUMMARY:  checks local system for installed tool via 1) PTF and 2) 'which' command
              INPUT:  none. reads values from self
             OUTPUT:  True or False """

        ptf_config_file = str(config.axiom.ptf_folder + "/config/ptf.config")

        if self.ptf_module not in ["", None]:
            tool_module_file = str(config.axiom.ptf_folder + "/" + self.ptf_module + ".py")

            try:
                with open(ptf_config_file) as ptf_config:
                    for line in enumerate(ptf_config):
                        if search("^BASE_INSTALL_PATH=", line[1]):
                            install_path = line[1].split("\"")[1]
                            break

            except OSError:
                print_error(str("ERROR: Failed to extract PTF base install path from " + ptf_config_file))
                exit(1)

            else:
                try:
                    with open(tool_module_file) as module_file:
                        for line in enumerate(module_file):
                            if search("^INSTALL_LOCATION=", line[1]):
                                location = line[1].split("\"")[1]
                                break

                except OSError:
                    print_error(str("ERROR: Failed to extract PTF install location from " + tool_module_file))
                    exit(1)

                else:
                    folder = str(self.ptf_module.split("/")[1])
                    ptf_tool_folder = str(install_path + "/" + folder + "/" + location)

                    if path.exists(ptf_tool_folder):
                        return True
                    else:
                        return False

        text = str("which \"" + self.name + "\"")

        try:
            dev_null = open(devnull, 'w')
            if call(split(text), stdout=dev_null, stderr=STDOUT) == 0:
                return True
            else:
                return False

        except OSError:
            print_error(str("ERROR: Failed to run command " + text))
            exit(1)

    def platform_matches(self):
        """ SUMMARY:  compares tool platform against local platform value in global config object
              INPUT:  none, reads values from self and config
             OUTPUT:  True or False """

        if self.platform.lower() == config.axiom.platform.lower():
            return True
        else:
            return False

    def proceed_despite_uninstalled(self):
        """ SUMMARY:  prompts user to confirm it's okay to execute the tool regardless of if it was detected
              INPUT:  an AxiomTool object
             OUTPUT:  True of False """

        answer = input("[AXIOM] Unable to confirm " + self.name + " is installed. Proceed anyway? [Y/n] ")
        if answer not in ["Y", "y", "Yes", "yes"]:
            return False
        else:
            return True

    def resolve_command(self, number):
        """ SUMMARY:  determines the object's type (command or action) and finds its ID value
              INPUT:  command/action ID number integer
             OUTPUT:  two-item tuple containing 1) "command", "action", or None and 2) ID value, -1 if unresolved """

        if number >= 0 and number in range(self.combined_list.__len__()):
            command_name = self.combined_list[number]
            return self.resolve_command_name(command_name)
        else:
            return None, int(-1)

    def resolve_command_name(self, command_name):
        """ SUMMARY:  finds the ID value of the supplied command/action name
              INPUT:  command/action name string
             OUTPUT:  tuple containing string ("command" or "action") and ID value (int), -1 if not found """

        command_type = str()
        id_value = int(-1)

        x = 0
        action_count = self.action_list.__len__()
        while x < action_count:
            if self.action_list[x].name == command_name:
                command_type = "action"
                id_value = x
            x += 1

        y = 0
        command_count = self.command_list.__len__()
        while y < command_count:
            if self.command_list[y].name == command_name:
                command_type = "command"
                id_value = y
            y += 1

        return command_type, id_value

    def show(self):
        """ SUMMARY:  displays tool information on the screen for the user
              INPUT:  self, reads name, ptf_module, description, and combined_list variables
             OUTPUT:  none, only prints to the screen """

        print("\n  NAME:  " + str(self.name) + " (" + str(self.platform) + ")")

        if isinstance(self.ptf_module, str):
            print("  TOOL:  " + str(self.ptf_module))

        print("  NOTE:  " + str(self.description))

        print("\nCommands\n")
        i = 0
        while i < self.combined_list.__len__():
            print("  " + str(i + 1) + "\t" + self.combined_list[i])
            i += 1


dispatch = AxiomDispatcher()
