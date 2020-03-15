<p align="center"><img src="https://payl0ad.run/assets/images/post-8/axiom-framework-logo.png"></p>

<div align="center">
  <!-- Release -->
  <a href="https://github.com/mikeiacovacci/axiom-framework/releases">
    <img src="https://img.shields.io/github/v/release/mikeiacovacci/axiom-framework"
      alt="Release" />
  </a>
  <!-- License -->
  <a href="https://github.com/mikeiacovacci/axiom-framework/blob/master/LICENSE">
    <img src="https://img.shields.io/github/license/mikeiacovacci/axiom-framework"
      alt="License" />
  </a>
  <!-- Issues -->
  <a href="https://github.com/mikeiacovacci/axiom-framework/issues">
    <img src="https://img.shields.io/github/issues-raw/mikeiacovacci/axiom-framework?label=open%20issues"
      alt="Issues" />
  </a>
  <!-- Espresso -->
  <a href="https://payl0ad.run">
    <img src="https://img.shields.io/badge/powered%20by-espresso-blue?style=flat"
    alt="Espresso" />
  </a>
</div>

<br>

<p align="center">
AXIOM is a configurable, interactive knowledge management framework for learning, using, and experimenting with 
arbitrary command line programs.
</p>

---
AXIOM Framework lets you "bookmark" your commands so you can reference, modify, and execute them more easily.

If you know what you're doing then get started with the following:

```
git clone git@github.com:mikeiacovacci/axiom-framework.git
cd axiom-framework
pip3 install -r requirements.txt
sudo python3 ./axiom
```

Otherwise, please read the [security](#security) considerations before installing.

## Table of Contents

- [Motivation](#motivation)
- [What it Does](#what-it-does)
  - [Features](#features)
  - [Implementation](#implementation)
- [Installation](#installation)
  - [Dependencies](#dependencies)
  - [Security](#security)
- [Usage](#usage)
  - [Standard Usage](#standard-usage)
  - [Referencing](#referencing)
  - [Modifying](#modifying)
  - [Executing](#executing)
  - [Interactive Programs](#interactive-programs)
- [Configuration](#configuration)
- [Adding Commands](#adding-commands)
- [Known Limitations](#known-limitations)
- [Feedback & Support](#feedback--support)
- [License](#license)

## Motivation

Infosec professionals are expected to know how to use **hundreds** of command line software programs. New offensive and 
defensive tools get released *all the time*, and practitioners need to learn them through hands-on experience. One might 
do any of the following to get started:

- Read manual pages
- Search online
- Elicit program help/usage text
- Trial and error

Some command line programs present learning obstacles like missing documentation and poor feature discoverability. 
Furthermore, if one doesn't interact with a given CLI program for a while it's natural to forget the specific details 
(command syntax, available features, expected outputs, environmental requirements, "lesson's learned" from last time, 
etc.) needed to use the tool effectively. When this happens, one can **repeat** the above steps with the addition of two 
more:

- Revisit terminal history
- Refer to any personal notes

These approaches definitely help with recall, but rereading one's notes (unstructured text, handwriting, etc.) or 
searching one's terminal history (if it exists on the current system) then copying/pasting, modifying, or retyping 
command text is an *annoying* distraction from the task at hand and wastes one's time and limited capacity to focus.

Even when recall isn't a problem infosec professionals still need to *maximize* their **learning** while *also* 
improving their **routine tool use** by *minimizing* time-wasting activities (repetitive typing, manually installing 
tools, etc.) at the command line.

## What it Does

### Features

- Presents an interactive, keystroke-conserving, and discoverability-oriented interface
- Uses a prompt-driven, wizard-like menu system for creating, modifying, and running commands
- Auto-suggests type-specific command inputs based on history
- Executes commands via local subprocesses or by transmitting text to interactive prompts
- Supports any interactive CLI program that outputs a prompt with a detectable pattern
- Supports single- and multi-line standalone and interactive commands
- Supports single-line "autonomous" commands (i.e. shell commands that use pipes)
- Generates single- and multi-line non-executable text (e.g. injectable payloads)
- Installs missing programs automatically via [The PenTesters Framework (PTF)](https://github.com/trustedsec/ptf)
- Integrates command data from multiple "toolkits" hosted anywhere
- Supports user-defined prompts, prompt patterns, and input data types
- Supports deploying a custom config at first execution via URL parameter
- Runs on Linux (Debian, Ubuntu, and ArchLinux) with partial macOS support
- Utilizes a human-readable data format

### Implementation

AXIOM Framework relies on YAML files that contain data about CLI programs, their commands, and details about those 
commands. Generally, each program is represented as a `.yml` file that specifies the program's name, a description, the 
operating system on which the program runs, and a PTF module if applicable.

These YAML files can contain an infinite number of listed command entries that, in turn, specify the command's name 
(i.e. a brief description or "nickname"), prompt and execution types, text with any placeholder values, input 
descriptions, outputs, and any notes for the end user.

AXIOM Framework integrates all the data at runtime by 

1. searching the `inventory folder` (specified in the configuration file) for sub-folders ("toolkits") containing YAML 
files
2. merging the data from an infinite number of said YAML files into a unified structure.

The program generally interacts with user-provided data in a read-only capacity, but it's built to fetch ZIP-compressed 
toolkits from any HTTP(S) URL to encourage the user to keep data separated (e.g. in a version control system) for 
improved loss-prevention and collaboration.

## Installation

Install AXIOM Framework by cloning this repository or downloading and extracting the ZIP file in 
[Releases](https://github.com/mikeiacovacci/axiom-framework/releases).

### Dependencies

- POSIX platform (Debian, Ubuntu, or ArchLinux for full compatibility)
- Python 3 (including modules listed in `requirements.txt`)
- `bash`
- `which`

Know that `axiom` utilizes a shebang of `#!/usr/bin/env python3` which may not work for a given `python3` installation. 
The end user can override it by supplying the `axiom` file as an argument to the Python 3 interpreter.

### Security

End users are strongly advised to run AXIOM Framework on disposable, *untrusted* infrastructure after downloading the 
ZIP file in [Releases](https://github.com/mikeiacovacci/axiom-framework/releases) and verifying the PGP signature. **Do 
not run the framework on critical systems**, and don't use it *at all* if you don't trust me or my code :)

Furthermore, know that a "good signature" only indicates the ZIP file contents were signed by the corresponding private 
PGP key and this does not validate the authenticity of any dependencies like third-party libraries/modules or toolkit 
datasets. AXIOM Framework downloads, extracts, installs, and executes third-party software and other content. **Do not 
use the framework if you don't trust any of those third parties.**

Users should regard toolkit data as executable content since AXIOM Framework uses it 

1. to execute shell commands
2. to spawn local subprocesses 
3. as input transmitted to other programs

Additionally, even before the one chooses to execute anything, the data is deserialized into Python objects, and 
malformed YAML input could hypothetically abuse program logic or execute arbitrary code. **Do not use toolkits from 
untrusted sources.**

AXIOM Framework requires root privileges for many modes of operation. Whoever controls the hosting infrastructure for 
the toolkit data or any optional, custom config file could hypothetically achieve code execution as root on your 
machine.

Lastly, the framework does not distinguish secret from non-secret user input. Any passwords, keys, or other sensitive 
inputs will be displayed on the screen and stored on disk, in plaintext, in the `history folder` (specified in the 
configuration file) within one or more `.axiom` history files.

## Usage

### Standard Usage

To interact with AXIOM Framework run `./axiom` and follow the prompts by

1. entering the name of a tool
2. selecting a command by number
3. confirming execution
4. entering any required inputs

![AXIOM Framework executing nmap](https://payl0ad.run/assets/images/post-8/axiom-framework-nmap.gif "Executing a simple command interactively")

This interface is useful for executing [interactive programs](#interactive-programs) and when switching between multiple 
tools. To select a different tool enter `back` at the command selection prompt. Entering `exit` at either the command or 
tool selection prompt will terminate the program.

Users interested in a specific, non-interactive tool can supply the tool name as a command line argument. Tool names 
are case sensitive. A tool name that contains spaces must be passed as a singular argument by enclosing the entire name 
in quotes or backslash-escaping the space characters.

### Referencing

To view information about a tool enter `./axiom show [TOOL]` supplying the tool name. AXIOM Framework will display the 
tool's PTF module (if any), notes, and an alphabetized list of the available commands.

![AXIOM Framework showing sqlmap](https://payl0ad.run/assets/images/post-8/axiom-framework-sqlmap.gif "AXIOM Framework listing a tool's commands")

To see more details about a specific command enter `./axiom show [TOOL] [NUM]` providing the tool name *and* the command 
number. This prints the command's name, execution and prompt types, notes, and text showing the placeholder values.

![AXIOM Framework showing hashcat command](https://payl0ad.run/assets/images/post-8/axiom-framework-hashcat.gif "AXIOM Framework showing command details")

### Modifying

To enter input values (i.e. to replace a command's placeholders) and print executable, "finalized" command text to the 
screen (e.g. to copy/paste into a script or another prompt) run `./axiom build [TOOL] [NUM]` with the tool name and 
command number and follow the prompts. If a command does not require user-supplied values then the text will simply be 
displayed on the screen.

![AXIOM Framework generating PowerShell text](https://payl0ad.run/assets/images/post-8/axiom-framework-powershell.gif "Building command text interactively")

### Executing

Users can execute non-interactive commands locally via AXIOM Framework by running `./axiom run [TOOL] [NUM]` supplying 
the tool name and command number as CLI arguments.

![AXIOM Framework executing lsof](https://payl0ad.run/assets/images/post-8/axiom-framework-lsof.gif "Executing a standalone action non-interactively")

If the command requires input values, the user will be prompted to enter them. Otherwise, the command will simply 
execute. Additionally, non-executable commands will merely print command text to the screen.

![AXIOM Framework running Python](https://payl0ad.run/assets/images/post-8/axiom-framework-python.gif "Outputting command text")

### Interactive Programs

AXIOM Framework supports executing interactive subprograms by:

1. transmitting command text to pseudo-terminal subprocesses
2. detecting subprogram input prompts in STDOUT via regex pattern matching
3. observing user-configurable timeouts to reduce false positives

When the user runs an interactive command, AXIOM Framework transmits the command text as subprogram input and prints the 
subprogram's STDOUT to the screen until the expected prompt pattern is detected.

![AXIOM Framework interacting with msfconsole](https://payl0ad.run/assets/images/post-8/axiom-framework-msfconsole.gif "A simple interactive program")

Executing interactive commands can result in prompt changes, so 
[AXIOM Framework maintains state](https://payl0ad.run/assets/images/post-8/axiom-framework-multiple-prompts.gif) 
to ensure command text is transmitted to the correct pseudo-terminal. It also prevents the user from creating runtime 
ambiguities by blocking commands that result in more than one subprocess having identical prompt types.

When running any executable command, AXIOM Framework **always** attempts to transmit command text (i.e. instead of 
executing commands locally) when the current runtime includes a pseudo-terminal subprocess with a matching prompt type. 

## Configuration

AXIOM Framework expects a file named `config.yml` in the top-level folder that modifies the program's interaction with 
the filesystem, subprocesses, toolkit data, and the end user.

Launching `axiom` for the first time (without any command line arguments) initializes the framework with settings from 
the default `config.yml` file after creating any missing folders and downloading/extracting any missing content.

To manually initialize (to reinstall PTF, re-download toolkits, etc.) run `./axiom init`. Initializing can result in 
data loss, because the folders listed in `config.yml` will be deleted and replaced. Folder settings can hypothetically 
reference directories outside of the top-level folder, so verify the settings are correct before executing.

To manually initialize with a *custom* configuration run `./axiom init [URL]` specifying an HTTP(S) URL hosting the new 
configuration file. AXIOM Framework will

1. ignore the existing `config.yml` file
2. download the new file (replacing the existing one)
3. initialize with the new settings

![Customizing AXIOM Framework](https://payl0ad.run/assets/images/post-8/axiom-framework-custom-config.gif "Configuring AXIOM Framework with custom settings")

Again, initializing can result in data loss, because the folders listed in the *new* configuration file will be deleted 
and replaced. Only deploy config files created by trusted parties and hosted on trusted infrastructure.

To integrate any changes to the *local* YAML data (e.g. while learning and experimenting) run `./axiom reload`. AXIOM 
Framework will reprocess all the YAML files which could take a few additional seconds. Know that modifications to local 
YAML data will be *lost* if initialization occurs, so ensure that *permanent* changes are saved at the data source. 
Additionally, a tool's commands are always listed in alphabetical order, and modifying a command's name can change its 
ID number and command list ordering without warning.

Worth noting is that neither initializing nor reloading causes AXIOM Framework to delete its `.axiom` history files. The 
end user can manually delete specific history files or the whole `history folder` to reset input auto-suggestion.

## Adding Commands

AXIOM Framework is not merely the sum of any existing toolkit datasets. It's designed to be built upon by end users. 
Certainly toolkits can be shared, but users intending to create and use *their own custom toolkits* can write new YAML 
data "from scratch" with the help of two approaches:

1. Learn and borrow from more than **1,000** [examples](https://github.com/mikeiacovacci/axiom-data-demo-x) 
[available](https://github.com/mikeiacovacci/axiom-data-demo-y) 
[online](https://github.com/mikeiacovacci/axiom-data-demo-z).
2. Run `./axiom new` for an interactive "wizard" mode that generates valid YAML.

![AXIOM Framework generating YAML](https://payl0ad.run/assets/images/post-8/axiom-framework-new-command.gif "Generating new toolkit data interactively")

Be aware of the following ideas, constraints, and best practices when creating custom toolkit data:

- A tool can be represented via multiple, separate YAML files across more than one toolkit.
- A tool with more than one YAML file must have matching `name`, `description`, `os`, and `ptf_module` values to merge.
- A tool's `os` value affects if AXIOM Framework will attempt local execution.
- A software suite is best represented as multiple, smaller tools instead of only one tool with dozens of commands.
- Command names must be "tool-unique" across all YAML files within the `inventory folder`.
- Concise but sufficiently-detailed command names, input names, and notes greatly improve the user experience. 
- Multi-line commands are not recommended as a substitute for writing real scripts in typical formats.

## Known Limitations

- Doesn't set subprogram environment variables on its own
- Doesn't do *anything* with non-STDOUT or non-PROMPT outputs
- Doesn't track depth level for multiple interactive subprogram prompt changes
- Doesn't clean up `bash` subprocesses after exiting interactive subprograms
- Doesn't work well for subprograms that only exit upon receiving an interrupt
- Doesn't work well for long-running, interactive subprograms with infrequent output
- Fails to install PTF tools when the installation process requires user input
- Fails to detect PTF tools not installed using organizational directories (not default)
- Fails when running interactive "exit" commands in the wrong runtime context
- Input placeholder text could hypothetically collide with some subprogram's syntax

## Feedback & Support

Feel free to [open an issue](https://github.com/mikeiacovacci/axiom-framework/issues/new/choose) in any of the following 
scenarios:

1. [Bug](https://github.com/mikeiacovacci/axiom-framework/issues/new?assignees=&filename=bug.md&labels=&title=%5BBUG%5D)
2. [Security weakness](https://github.com/mikeiacovacci/axiom-framework/issues/new?assignees=&filename=security-weakness.md&labels=&title=%5BSECURITY%5D) 
not addressed [above](#security)
3. Significant [UI/UX problem](https://github.com/mikeiacovacci/axiom-framework/issues/new?assignees=&filename=ui-ux-problem.md&labels=&title=%5BUI%2FUX%5D)
4. Missing or inaccurate [documentation](https://github.com/mikeiacovacci/axiom-framework/issues/new?assignees=&filename=documentation.md&labels=&title=%5BDOCUMENTATION%5D)
5. [Inefficiency](https://github.com/mikeiacovacci/axiom-framework/issues/new?assignees=&filename=inefficiency.md&labels=&title=%5BINEFFICIENCY%5D) 
(e.g. algorithmic)
6. Request for a reasonable [new feature](https://github.com/mikeiacovacci/axiom-framework/issues/new?assignees=&filename=feature-request.md&labels=&title=%5BFEATURE%5D)

Please **do not** open any issues in the following scenarios:

1. Incorrect, inaccurate, or outdated toolkit data
2. Command execution failure due to toolkit data only
3. PTF issue unrelated to AXIOM Framework
4. A [known limitation](#known-limitations) (without proposing a solution)
5. Request for feature that broadly expands the project scope
6. Request for feature that harms end user security or privacy
7. Request for feature antithetical to the project ethos

## License

AXIOM Framework is made available under the [Apache 2.0 License](https://www.apache.org/licenses/LICENSE-2.0).
