#!/usr/bin/python3

#   FileMaker Recovery Check tool
#
#   Created: 2025-06-03 Simon Brown


import argparse, os, sys, subprocess, re
from pprint import pprint

# USAGE
#   filemaker_recovery_check directoryPath filePattern [-n | --newest] [-p | --passphrase]

FIND_COMMAND = '/usr/bin/find'
FMDT_COMMAND = 'FMDeveloperTool'

ARGPARSER: argparse = None

corrupted_file_patterns = [
    "This item changed$",
    "Adjusted item count of library .* \(.*\) by .*",
    "Calculation modified$",
    "Dropped page starts with data of type",
    "ERROR: copy or rebuild of file blocks failed; try another option in Advanced Recover Options",
    "Found .* stranded library object\(s\)",
    "File blocks: scanned and rebuilt .* block\(s\), dropped ([^0]) invalid data",
    "Item count changed from .* to .*",
    "Rebuilt value index for field .* old index is ([^0])",
    "Recovered .* stranded library object\(s\) for a total of .* byte\(s\)",
]


def find_files (parent_dir: str, file_pattern: str) -> list:

    """
    Returns paths to all files matching the file pattern in the given directory.
    """

    if parent_dir is None or parent_dir == "":
        raise ValueError ("Directory path is missing")

    if file_pattern is None or file_pattern == "":
        raise ValueError ("File pattern is missing")

    if not os.path.isdir (parent_dir):
        raise ValueError ("Directory does not exist or is not readable")

    # Use a maxdepth of 2 so that if pointed at 'Backups', it will go into
    # the `DAILY_2025-01-01_XXXX` directory for .fmp12 files, but not so
    # deep as to start digging into RC_Data_FMS directory.

    output = subprocess.run (
        [FIND_COMMAND,
        parent_dir,
        '-maxdepth', '2',
        '-name', file_pattern],
        capture_output=True,
        text=True,
    )
    # filter out the empty string that split generates
    found_files = list(filter(None, output.stdout.split('\n')))
    return found_files


def find_newest_dir (parent_directory: str) -> str:

    """
    Of the directories in the parent directory, determine the newest directory
    and returns its path. Does not descend into sub-directories.
    """

    # check for subdirectories
    subdirectories = []
    for item in os.listdir(parent_directory):
        item_path = os.path.join(parent_directory, item)
        if os.path.isdir(item_path):
            subdirectories.append(item_path)

    # if subdirectories empty, return nothing
    if not subdirectories:
        return None


    # Sort subdirectories by modification time (mtime) in descending order
    # os.path.getmtime returns the time of last modification as a float
    newest_subdirectory = max(subdirectories, key=os.path.getmtime)
    return newest_subdirectory


def find_newest_files (parent_dir: str, file_pattern: str, recursive=False):

    """
    Return the path & time data for the files with the file with the most recent modification timestamp
    and that also matches the given pattern.
    """

    exec_param = ''

    #match sys.platform:
    #   case 'darwin':
    #       exec_param = """-exec stat -t "%Y %m %d %H %M %S" -f "%SB %N" {} \; | sort -nr -k1 -k2 -k3 -k4 -k5 -k6 | head -1"""
    #   case 'linux':
    #       exec_param = """-maxdepth 0 -exec stat -t %Y %m %d %H %M %S" -f %SB %N" {} \; | sort -nr -k1 -k2 -k3 -k4 -k5 -k6 | head -1"""

    output = subprocess.run (FIND_COMMAND, parent_dir, capture_output=True)


def create_argparser () -> bool:

    global ARGPARSER

    ARGPARSER = argparse.ArgumentParser(
        prog='fm_recovery_check',
        description='Recover all files in a directory and scan the recovery log for problems.',
        usage='%(prog)s directoryPath filePattern [-n | --newest] [-p | --passphrase]')

    ARGPARSER.add_argument('path')
    ARGPARSER.add_argument('filepattern')
    ARGPARSER.add_argument('-n', '--newest', action="store_true", help='search using newest directory in path')
    ARGPARSER.add_argument('-p', '--passphrase', type=str, help='EAR passphrase')

    return True

#
#   r e c o v e r _ f i l e
#

def recover_file (file_path: str, parent_dir: str, passphrase: str) -> bool:

    """
    Recover a single using the FMDeveloperTool. Before running, the
    Recover.log file will be removed if present, the recover will be
    attempted, and the resulting recovered file deleted.
    """
    # --recover <source_filename> [-target_filename | -t <path>] [-encryption_key | -e <key>] [-generate | -g <rebuild | datablocks | asis>] [-skipSchema | -r] [-skipStructure | -l] [-rebuildIndex | -i <now | later | false>] [-keepCaches | -k] [-bypass | -b] [-username | -u <username>] [-password | -p <password>]

    file_name = os.path.basename (file_path)
    file_dir = os.path.dirname (file_path)
    file_ext = file_name.split('.')[-1]

    # ignore files without the fmp12 extension
    if file_ext != 'fmp12':
        print(file_ext)
        print ('Warning: "' + file_name + '"' + ' may not be a FileMaker file and is being skipped' )
        return None

    # TODO: use RE here instead so we only replace at end of string.
    file_path_out = file_path.replace ('.fmp12', '_recovered.fmp12', 1)


    # build fm recovery command
    fm_data_recovery_command = [
        FMDT_COMMAND,
        parent_dir,
        '--recover', f"{file_path}",
        '-target_filename', f"{file_path_out}",
    ]
    # append passphrase if we got one
    if passphrase != None:
        fm_data_recovery_command.append('--passphrase', passphrase)

    # set the recovery log file
    recovery_log_file = f'{parent_dir}/Recover.log'

    # run command
    try:
        print(f"Attempting to perform file recovery for {file_name}.\nRecovery file: {file_path_out}")
        result = subprocess.run (
            fm_data_recovery_command,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Command failed with exit code: {e.returncode}")
        print(f"Stdout: {e.stdout}")
        print(f"Stderr: {e.stderr}")

    # output log file
    print(f"Recovery Log File: {recovery_log_file}")

    # remove recovery file
    try:
        print(f"Removing recovery file at {file_path_out}")
        os.remove (file_path_out)
    except OSError as e:
        print ('Error: no output file created for "' + file_name + '"')
        return False

    if result.returncode == 0:
        return {
            "file_name": file_name,
            "file_path": file_path,
            "recovery_log_file": recovery_log_file
        }

#
# parse files for corruptions
#
def check_file_corruption(file_path: str, pattern: str):
    """
    Searches for a pattern for fms file corruption

    Args:
        file_path (str): The path to the file to search.
        pattern (str): The regular expression pattern to search for.
    """
    try:
        with open(file_path, 'r') as file:
            # Compile the regular expression for efficiency if used repeatedly
            compiled_pattern = re.compile(pattern)
            for line_number, line in enumerate(file, 1):
                if compiled_pattern.search(line):
                    print(f"Line {line_number}: {line.strip()}")
    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
    except Exception as e:
        print(f"An error occurred: {e}")


#
#   M A I N
#

if __name__ == "__main__":

    return_code = 0;

    create_argparser()

    arguments = ARGPARSER.parse_args()

    #print (arguments.path)
    #print (arguments.filepattern)
    #print (arguments.newest)

    path = arguments.path

    if arguments.newest:
        path = find_newest_dir (path)

    print ('Directory being used:', path)

    file_list = find_files (path, arguments.filepattern)

    if file_list == []:
        print ('Error: no matching files found')
        exit (-3)

    # Currently, remove an previous log. Instead, we'll accumulate the messages for
    # all files. Later versions of this script we'll scan the logs after each recovery.
    try:
        os.remove (path + "Recover.log")
    except OSError as e:
        pass

    # perform file recovery - remove recovered file, keep log file
    recovered_file_logs = []
    for file in file_list:
        recover_file_result = recover_file (file, path, arguments.passphrase)
        if recover_file_result == False:
            return_code = -2
            break
        recovered_file_logs.append(recover_file_result)

    # check through log files
    for obj in recovered_file_logs:
        # collect data
        corrupted_checks = []
        file_name = obj['file_name']
        file_path = obj['file_path']
        recovery_log_file = obj['recovery_log_file']

        # loop through patterns to check
        print(f"Reviewing recovery log for {file_path}")
        for pattern in corrupted_file_patterns:
            result = check_file_corruption(recovery_log_file, pattern)
            if result != None:
                print(f"Found possible corruption for {file_path}. Triggered by the search pattern, {pattern}")
                corrupted_checks.append(file_name)

        # alert if we found nothing
        if not corrupted_checks:
            print(f"No file corruption found for {file_path}")

    # DONE
    sys.exit (return_code)
