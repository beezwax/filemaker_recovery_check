#!/usr/bin/python3

#	FileMaker Recovery Check tool
#
#	Created: 2025-06-03 Simon Brown


import argparse, os, sys, subprocess

# USAGE
#	filemaker_recovery_check directoryPath filePattern [-n | --newest] [-p | --passphrase]

FIND_COMMAND = '/usr/bin/find'
FMDT_COMMAND = 'FMDeveloperTool'

ARGPARSER: argparse = None


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
		capture_output=True
	)
	
	return output.stdout.decode("utf-8").split('\n')


def find_newest_dir (parent_dir: str) -> str:

	"""
	Of the directories in the parent directory, determine the newest directory
	and returns its path. Does not descend into sub-directories.
	"""
	
	from pathlib import Path

	parent = Path(parent_dir)
	path_newest = None
	
	# assume we'll find dir at least as old as parent
	mtime: float = Path.stat(p).st_mtime

	# Iterate over all enclosed files or dirs,
	# tracking the newest directory we see.
	
	for f in parent.iterdir():
		cur_mtime = f.stat().st_mtime
		
		if f.is_dir() and cur_mtime >= mtime:
		   mtime = f.stat().st_mtime
    
	return path_newest


def find_newest_files (parent_dir: str, file_pattern: str, recursive=False):

	"""
	Return the path & time data for the files with the file with the most recent modification timestamp
	and that also matches the given pattern.
	"""
	
	exec_param = ''
	
	#match sys.platform:
	#	case 'darwin':
	#		exec_param = """-exec stat -t "%Y %m %d %H %M %S" -f "%SB %N" {} \; | sort -nr -k1 -k2 -k3 -k4 -k5 -k6 | head -1"""
	#	case 'linux':
	#		exec_param = """-maxdepth 0 -exec stat -t %Y %m %d %H %M %S" -f %SB %N" {} \; | sort -nr -k1 -k2 -k3 -k4 -k5 -k6 | head -1"""
		
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
	ARGPARSER.add_argument('-p', '--passphrase', action="store_true", help='EAR passphrase')
	
	return True

#
#	r e c o v e r _ f i l e
#

def recover_file (file_path: str, passphrase: str) -> bool:
	
	"""
	Recover a single using the FMDeveloperTool. Before running, the
	Recover.log file will be removed if present, the recover will be
	attempted, and the resulting recovered file deleted.
	"""
	# --recover <source_filename> [-target_filename | -t <path>] [-encryption_key | -e <key>] [-generate | -g <rebuild | datablocks | asis>] [-skipSchema | -r] [-skipStructure | -l] [-rebuildIndex | -i <now | later | false>] [-keepCaches | -k] [-bypass | -b] [-username | -u <username>] [-password | -p <password>]

	file_name = os.path.basename (file_path)
	file_dir = os.path.dirname (file_path)
	
	if file_name [-4:] != '.fmp12':
		print ('Warning: "' + file_name + '"' + ' may not be a FileMaker file and is being skipped' )
		return None
	
	# TODO: use RE here instead so we only replace at end of string.
	file_path_out = file_path.replace ('.fmp12', '_recovered.fmp12', 1)
	
	#try:
	#	os.remove (file_dir + "Recover.log")
	#except OSError as e:
	#	pass

	if passphrase == None:
		output = subprocess.run (
			[FMDT_COMMAND,
			parent_dir, 
			'--recover', file_path,
			'-target_filename', file_path_out],
			capture_output=True
		)
	else:
		# Passphrase will be ignored for any files that don't need it.
		output = subprocess.run (
			[FMDT_COMMAND,
			parent_dir, 
			'--recover', file_path,
			'-target_filename', file_path_out,
			'-encryption_key', passphrase],
			capture_output=True
		)
	
	print()
	print (output.stdout)
	print
	
	try:
		os.remove (file_path_out)
	except OSError as e:
		print ('Error: no output file created for "' + file_name + '"')
		return False

	if output.returncode == 0:
		# NO ACTION CURRENTLY
		pass

#
#	M A I N
#

if __name__ == "__main__":

	return_code = 0;
	
	create_argparser()
	
	arguments = ARGPARSER.parse_args()
	
	print (arguments.path)
	print (arguments.filepattern)
	print (arguments.newest)
	print (arguments.passphrase)
	
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

	
	for file in file_list:
		if recover_file (file, arguments.passphrase) == False:
			return_code = -2
			break

	sys.exit (return_code)






