import subprocess
import argparse
import json
import yaml
import logging
import uuid
import os
from typing import Any, Optional

logging.basicConfig(level=logging.INFO)

def run_git_command(command: str) -> list:
    result = subprocess.run(command, stdout=subprocess.PIPE, text=True, shell=True)
    return result.stdout.strip().split('\n')

def set_output(name: str, value: any) -> None:
    logging.info(f"Setting output {name}")
    with open(os.environ['GITHUB_OUTPUT'], 'a') as fh:
        delimiter = uuid.uuid1()
        print(f'{name}<<{delimiter}', file=fh)
        print(value, file=fh)
        print(delimiter, file=fh)

def read_yaml(folder: str, file_name: str) -> dict:
    file_path = os.path.join(folder, file_name)
    logging.info(f"Reading YAML file {file_path}")
    try:
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        return data
    except FileNotFoundError:
        logging.info(f"File {file_path} not found")
        return {}
    except yaml.YAMLError as exc:
        logging.info(f"Error in configuration file: {exc}")
        return {}
    
def get_default_branch():
    command = "git symbolic-ref refs/remotes/origin/HEAD | sed 's@^refs/remotes/origin/@@'"
    result = subprocess.run(command, stdout=subprocess.PIPE, text=True, shell=True)
    return result.stdout.strip()

def get_latest_tag():
    command = "git describe --tags `git rev-list --tags --max-count=1`"
    result = subprocess.run(command, stdout=subprocess.PIPE, text=True, shell=True)
    return result.stdout.strip()

def get_default_remote():
    command = "git remote"
    result = subprocess.run(command, stdout=subprocess.PIPE, text=True, shell=True)
    remotes = result.stdout.strip().split('\n')
    return remotes[0] if remotes else 'origin'

def include_directories(git_diff_output, include_patterns):
    include_set = set(include_patterns.split(","))
    return [path for path in git_diff_output if any(include in path for include in include_set)]

# Use set operations to efficiently filter directories
def filter_directories(git_diff_output, exclude_patterns):
    return list(set(git_diff_output) - set(exclude_patterns.split(",")))

def read_and_filter_yaml(folder, file_name, keyword):
    yaml_data = read_yaml(folder, file_name)
    filtered_data = {key: value for key, value in yaml_data.items() if keyword.lower() in key.lower()}
    return filtered_data

def strip_folder_from_lists(folder_list, folder_path_to_strip):
    return [folder.replace(folder_path_to_strip, '') for folder in folder_list]

# Initialize metadata dictionary
metadata = {}

# Parse arguments
parser = argparse.ArgumentParser(description='Process Git diff and sort folders.')
parser.add_argument('--strip-path', type=str, help='Folder path to strip', required=False, default=None)
parser.add_argument('--meta-file-name', type=str, help='Name of the YAML metadata file', required=False, default=None)
parser.add_argument('--keyword', type=str, help='Keyword to look for in the YAML file', required=False, default=None)
group = parser.add_mutually_exclusive_group(required=True) # Use mutually exclusive group to ensure only one of the two arguments is used
group.add_argument('--comparing-branch', type=str, help='Branch to compare with', default=None)
group.add_argument('--comparing-tag', type=str, help='Tag to compare with', default=None)
group2 = parser.add_mutually_exclusive_group(required=False) # Use mutually exclusive group to ensure only one of the two arguments is used
group2.add_argument('--exclude-patterns', type=str, help='Patterns for paths to exclude from git dir', default=None)
group2.add_argument('--include-patterns', type=str, help='Patterns for paths to include in git dir', default=None)
args = parser.parse_args()

# Print the value of GITHUB_OUTPUT before any updates
initial_value = os.environ.get('GITHUB_OUTPUT', 'Not Set')
print(f"Initial value of GITHUB_OUTPUT: {initial_value}")

# Avoid repetitive YAML reads by storing data in a dictionary
yaml_cache = {}

if args.comparing_branch and args.comparing_tag:
    raise argparse.ArgumentError(None, "You can only use one of comparing_branch or comparing_tag inputs, not both.")

if args.exclude_patterns and args.include_patterns:
    raise argparse.ArgumentError(None, "You can only use one of exclude_patterns or include_patterns inputs, not both.")

# Get working directory
working_directory = os.getenv('GITHUB_WORKSPACE')
print(f"working directory: {working_directory}") 

# Get Git Diff
try:
    default_remote = get_default_remote()
    default_branch = get_default_branch()
    if args.comparing_branch:        
        if args.comparing_branch.lower() == 'main':            
            git_diff_command = f"git --git-dir={working_directory}/.git --work-tree={working_directory} diff {default_branch}"
        else:
            git_diff_command = f"git --git-dir={working_directory}/.git --work-tree={working_directory} diff remotes/{default_remote}/{args.comparing_branch}"
    elif args.comparing_tag:
        if args.comparing_tag.lower() == 'latest':
            latest_tag = get_latest_tag()
            git_diff_command = f"git --git-dir={working_directory}/.git --work-tree={working_directory} diff {latest_tag}..HEAD"
        else:
            git_diff_command = f"git --git-dir={working_directory}/.git --work-tree={working_directory} diff {args.comparing_tag}..HEAD"

    git_diff_output = run_git_command(f"{git_diff_command} --name-only")

    if args.include_patterns:
        git_diff_output = include_directories(git_diff_output, args.include_patterns)
    elif args.exclude_patterns:  # Only run exclude if include is not specified
        git_diff_output = filter_directories(git_diff_output, args.exclude_patterns)

except Exception as e:
    logging.error(f"An error occurred while running the git command: {e}")
    git_diff_output = []

# Inserted: Additional logic for excluding directories in git diff
if args.exclude_patterns:
    git_diff_output = filter_directories(git_diff_output, args.exclude_patterns)

## Extract distinct folders
#distinct_folders = list(set([os.path.dirname(path) for path in git_diff_output if path.strip()]))
#print(f"distinct_folders: {distinct_folders}")

# Extract distinct folders
distinct_folders = list(set([os.path.dirname(path) for path in git_diff_output if path]))
print(f"distinct_folders: {distinct_folders}")

# Inserted: Logic for reading and filtering YAML based on a keyword
if args.meta_file_name and args.keyword:
    filtered_yaml_data = {}
    for folder in distinct_folders:
        filtered_data = read_and_filter_yaml(folder, args.meta_file_name, args.keyword)
        if filtered_data:
            filtered_yaml_data[folder] = filtered_data
            
    # Set output for filtered YAML data
    set_output("filtered_yaml_data", json.dumps(filtered_yaml_data))

# Populate metadata dictionary by reading YAML files in each folder
folders_with_metadata = []
folders_without_metadata = []

for folder in distinct_folders:
    try:
        print(f"folder: {folder}, meta_file_name: {args.meta_file_name}, keyword: {args.keyword}")
        full_path_folder = os.path.join(working_directory, folder)
        sorting_key = read_yaml(folder, args.meta_file_name).get(args.keyword)
        if sorting_key:
            metadata[folder] = sorting_key
            folders_with_metadata.append(folder)
        else:
            folders_without_metadata.append(folder)
    except Exception as e:
        logging.error(f"An error occurred while reading YAML for folder {full_path_folder}: {e}")
        raise e


# Sort folders
folders_sorted_alpha_inc = sorted(distinct_folders)
folders_sorted_alpha_dec = sorted(distinct_folders, reverse=True)
folders_sorted_meta_inc = sorted(folders_with_metadata, key=lambda x: metadata[x])
folders_sorted_meta_dec = sorted(folders_with_metadata, key=lambda x: metadata[x], reverse=True)

# Conditionally strip folder paths
strip_path = args.strip_path
if strip_path:
    distinct_folders = strip_folder_from_lists(distinct_folders, strip_path)
    folders_with_metadata = strip_folder_from_lists(folders_with_metadata, strip_path)
    folders_without_metadata = strip_folder_from_lists(folders_without_metadata, strip_path)
    folders_sorted_alpha_inc = strip_folder_from_lists(folders_sorted_alpha_inc, strip_path)
    folders_sorted_alpha_dec = strip_folder_from_lists(folders_sorted_alpha_dec, strip_path)
    folders_sorted_meta_inc = strip_folder_from_lists(folders_sorted_meta_inc, strip_path)
    folders_sorted_meta_dec = strip_folder_from_lists(folders_sorted_meta_dec, strip_path)

# Convert lists to strings
distinct_folders_str = json.dumps(distinct_folders).replace(" ", "")
folders_with_metadata_str = json.dumps(folders_with_metadata).replace(" ", "")
folders_without_metadata_str = json.dumps(folders_without_metadata).replace(" ", "")
folders_sorted_alpha_inc_str = json.dumps(folders_sorted_alpha_inc).replace(" ", "")
folders_sorted_alpha_dec_str = json.dumps(folders_sorted_alpha_dec).replace(" ", "")
folders_sorted_meta_inc_str = json.dumps(folders_sorted_meta_inc).replace(" ", "")
folders_sorted_meta_dec_str = json.dumps(folders_sorted_meta_dec).replace(" ", "")

# Print outputs
logging.info(f"distinct_folders: {distinct_folders_str}")
logging.info(f"folders_with_metadata: {folders_with_metadata_str}")
logging.info(f"folders_without_metadata: {folders_without_metadata_str}")
logging.info(f"folders_sorted_alpha_inc: {folders_sorted_alpha_inc_str}")   
logging.info(f"folders_sorted_alpha_dec: {folders_sorted_alpha_dec_str}")   
logging.info(f"folders_sorted_meta_inc: {folders_sorted_meta_inc_str}") 
logging.info(f"folders_sorted_meta_dec: {folders_sorted_meta_dec_str}") 

# Set Outputs
set_output("distinct_folders", distinct_folders_str)
set_output("folders_with_metadata", folders_with_metadata_str)
set_output("folders_without_metadata", folders_without_metadata_str)
set_output("folders_sorted_alpha_inc", folders_sorted_alpha_inc_str)
set_output("folders_sorted_alpha_dec", folders_sorted_alpha_dec_str)
set_output("folders_sorted_meta_inc", folders_sorted_meta_inc_str)
set_output("folders_sorted_meta_dec", folders_sorted_meta_dec_str)

# Convert lists to JSON
json = json.dumps({
    "distinct_folders": distinct_folders,
    "folders_with_metadata": folders_with_metadata,
    "folders_without_metadata": folders_without_metadata,
    "folders_sorted_alpha_inc": folders_sorted_alpha_inc,
    "folders_sorted_alpha_dec": folders_sorted_alpha_dec,
    "folders_sorted_meta_inc": folders_sorted_meta_inc,
    "folders_sorted_meta_dec": folders_sorted_meta_dec
})

# Set output as JSON
set_output("json", json)

# Print the value of GITHUB_OUTPUT after all updates
final_value = os.environ.get('GITHUB_OUTPUT', 'Not Set')
print(f"Final value of GITHUB_OUTPUT: {final_value}")
