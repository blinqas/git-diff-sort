# Git Diff Sort

## Overview
`Git Diff Sort` is a GitHub Action designed to provide various Git diff outputs, enhancing CI/CD pipelines and aiding in code reviews. It's very useful for Terraform plan and apply workflows where you have different terraform processing in different folders and you need to process them in a specific order. The option to have a yaml meta data file to define the order of the folders is very useful in this case.

## Features
- **Distinct Folders and Files**: Outputs distinct folders and files affected by a Git diff.
- **Alphabetical Sorting**: Provides alphabetically sorted lists of folders.
- **Metadata-based Sorting**: Sorts folders based on metadata defined in a YAML file.
- **Fallback Branch**: Dynamically determines the repository's default branch for comparison.

## Prerequisites
- GitHub Actions enabled on your repository.
- A codebase to run this action on.

## Inputs
| Name                  | Description                                               | Default            | Required |
|-----------------------|-----------------------------------------------------------|--------------------|----------|
| `meta_file_name`      | Name of the YAML file containing metadata. If it exist in the diff folder, it will be sorted in the outputs based on metadata | None               | No       |
| `keyword`             | Keyword to look for in the YAML file.                     | None               | No       |
| `comparing_branch`    | Branch to compare with. You can also use the word `default` to compare with the default branch. | None | No       |
| `comparing_tag`    | Tag to compare with. You can also use the word `latest` to compare with the latest tag.  | None | No       |
| `exclude_pattern`  | A pattern to exclude from the diff. Can't be used in combination with `include_pattern` | None | No       |
| `include_pattern`  | A pattern to include in the diff. Can't be used in combination with `exclude_pattern` | None | No       |
| `strip_pat`        | A pattern to strip from the diff path. | None | No       |

## Outputs

| Name                        | Description                                                                                     |
|-----------------------------|-------------------------------------------------------------------------------------------------|
| `distinct_folders`          | A list of distinct folders affected by the Git diff.                                            |
| `folders_without_metadata`  | A list of distinct folders that do not contain the specified metadata file.                     |
| `folders_sorted_alpha_inc`  | A list of distinct folders sorted alphabetically in an ascending order.                         |
| `folders_sorted_alpha_dec`  | A list of distinct folders sorted alphabetically in a descending order.                         |
| `folders_sorted_meta_inc`   | A list of distinct folders sorted based on metadata in ascending order.                         |
| `folders_sorted_meta_dec`   | A list of distinct folders sorted based on metadata in descending order.                        |
| `json`               | All outputs above json converted.                                                               |

## Usage

```yaml
- name: Run Git Diff
  uses: blinqas/git-diff-sort@v1
  with:
    meta_file_name: 'metadata.yaml'
    keyword: 'execution_order'
    comparing_tag: 'latest'
    include_pattern: 'terraform/'
    # comparing_branch: 'main'(you can only use comparing_branch or comparing_tag, not both)
  env:
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

## Version v1 (Default Version)
Users can specify v1 to use the latest v1 version of this action.

## Example Workflow
### Key Points:
Assumes the action runs from the repo root.

```yaml
name: Git Diff CI

on:
  pull_request:
    paths:
      - '**/*'

jobs:
  git-diff:
    runs-on: ubuntu-latest

    steps:
    - name: Checkout code
      uses: actions/checkout@v3

    - name: Run Git Diff Sort
      id: git-diff-sort
      uses: blinqas/git-diff-sort@v1
      with:
        yaml_meta_file_name: 'metadata.yaml'
        keyword: 'execution_order'
        comparing_branch: 'main'
      env:
        GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}

    - name: Use the output in the next steps
      run: |
        echo "Distinct folders: ${{ steps.git-diff-sort.outputs.distinct_folders }}"
        echo "Folders without metadata: ${{ steps.git-diff-sort.outputs.folders_without_metadata }}"
        echo "Folders sorted alphabetically in ascending order: ${{ steps.git-diff-sort.outputs.folders_sorted_alpha_inc }}"
        echo "Folders sorted alphabetically in descending order: ${{ steps.git-diff-sort.outputs.folders_sorted_alpha_dec }}"
        echo "Folders sorted based on metadata in ascending order: ${{ steps.git-diff-sort.outputs.folders_sorted_meta_inc }}"
        echo "Folders sorted based on metadata in descending order: ${{ steps.git-diff-sort.outputs.folders_sorted_meta_dec }}"

```

## Contributing
See CONTRIBUTING.md for contribution guidelines.

## License
Licensed under MIT. See LICENSE.md for details.
