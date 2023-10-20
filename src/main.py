import subprocess
import argparse
import json
import yaml
import logging
import uuid
import os

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
    try:
        with open(file_path, 'r') as f:
            data = yaml.safe_load(f)
        return data
    except FileNotFoundError:
        logging.error(f"File {file_path} not found")
        return {}
    except yaml.YAMLError as exc:
        logging.error(f"Error in configuration file: {exc}")
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


# Initialize metadata dictionary
metadata = {}

# Parse arguments
parser = argparse.ArgumentParser(description='Process Git diff and sort folders.')
parser.add_argument('--meta_file_name', type=str, help='Name of the YAML metadata file', default=None)
parser.add_argument('--keyword', type=str, help='Keyword to look for in the YAML file', default=None)
parser.add_argument('--comparing_branch', type=str, help='Branch to compare with', default=None)
parser.add_argument('--comparing_tag', type=str, help='Tag to compare with', default=None)
parser.add_argument('--exclude_patterns', type=str, help='Patterns for paths to exclude from git dir', default=None)

args = parser.parse_args()

if args.comparing_branch and args.comparing_tag:
    raise argparse.ArgumentError(None, "You can only use one of comparing_branch or comparing_tag inputs, not both.")


# Get Git Diff
try:
    working_directory = os.getenv('GITHUB_WORKSPACE')
    print(f"working directory: {working_directory}")    

    default_remote = get_default_remote()
    default_branch = get_default_branch()
    if args.comparing_branch:        
        if args.comparing_branch.lower() == 'default':            
            git_diff_command = f"git --git-dir={working_directory}/.git --work-tree={working_directory} diff {default_branch} --name-only"
        else:
            git_diff_command = f"git --git-dir={working_directory}/.git --work-tree={working_directory} diff remotes/{default_remote}/{args.comparing_branch} --name-only"
    elif args.comparing_tag:
        if args.comparing_tag.lower() == 'latest':
            latest_tag = get_latest_tag()
            git_diff_command = f"git --git-dir={working_directory}/.git --work-tree={working_directory} diff {latest_tag} --name-only"
        else:
            git_diff_command = f"git --git-dir={working_directory}/.git --work-tree={working_directory} diff {args.comparing_tag} --name-only"

    git_diff_output = run_git_command(f"{git_diff_command} --name-only {args.exclude_patterns}")
    print(f"git diff output: {git_diff_output}")
except Exception as e:
    logging.error(f"An error occurred while running the git command: {e}")
    git_diff_output = []

# Extract distinct folders
distinct_folders = list(set([os.path.dirname(path) for path in git_diff_output if path.strip()]))
print(f"distinct_folders: {distinct_folders}")

# Populate metadata dictionary by reading YAML files in each folder
folders_with_metadata = []
folders_without_metadata = []

for folder in distinct_folders:
    try:
        sorting_key = read_yaml(folder, args.meta_file_name).get(args.keyword)
        if sorting_key:
            metadata[folder] = sorting_key
            folders_with_metadata.append(folder)
        else:
            folders_without_metadata.append(folder)
    except Exception as e:
        logging.error(f"An error occurred while reading YAML for folder {folder}: {e}")


# Sort folders
folders_sorted_alpha_inc = sorted(distinct_folders)
folders_sorted_alpha_dec = sorted(distinct_folders, reverse=True)
folders_sorted_meta_inc = sorted(folders_with_metadata, key=lambda x: metadata[x])
folders_sorted_meta_dec = sorted(folders_with_metadata, key=lambda x: metadata[x], reverse=True)

distinct_folders_str = json.dumps(distinct_folders).replace(" ", "")
folders_with_metadata_str = json.dumps(folders_with_metadata).replace(" ", "")
folders_without_metadata_str = json.dumps(folders_without_metadata).replace(" ", "")
folders_sorted_alpha_inc_str = json.dumps(folders_sorted_alpha_inc).replace(" ", "")
folders_sorted_alpha_dec_str = json.dumps(folders_sorted_alpha_dec).replace(" ", "")
folders_sorted_meta_inc_str = json.dumps(folders_sorted_meta_inc).replace(" ", "")
folders_sorted_meta_dec_str = json.dumps(folders_sorted_meta_dec).replace(" ", "")

print(f"distinct_folders: {distinct_folders_str}")
print(f"folders_with_metadata: {folders_with_metadata_str}")
print(f"folders_without_metadata: {folders_without_metadata_str}")
print(f"folders_sorted_alpha_inc: {folders_sorted_alpha_inc_str}")
print(f"folders_sorted_alpha_dec: {folders_sorted_alpha_dec_str}")
print(f"folders_sorted_meta_inc: {folders_sorted_meta_inc_str}")
print(f"folders_sorted_meta_dec: {folders_sorted_meta_dec_str}")

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
