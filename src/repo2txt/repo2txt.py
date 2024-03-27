#!/usr/bin/env python

import os
import argparse
import json


def load_config(file_path):
    """
    Load configuration from a JSON file.

    Args:
        file_path (str): The path to the JSON configuration file.

    Returns:
        dict: A dictionary containing the configuration settings.
    """
    with open(file_path, "r") as file:
        return json.load(file)


# Usage
config = load_config("config.json")
IMAGE_EXTENSIONS = config["image_extensions"]
VIDEO_EXTENSIONS = config["video_extensions"]
AUDIO_EXTENSIONS = config["audio_extensions"]
DOCUMENT_EXTENSIONS = config["document_extensions"]
EXECUTABLE_EXTENSIONS = config["executable_extensions"]
SETTINGS_EXTENSIONS = config["settings_extensions"]
ADDITIONAL_IGNORE_TYPES = config["additional_ignore_types"]
DEFAULT_OUTPUT_FILE = config["default_output_file"]


def parse_args():
    """
    Parse command-line arguments for the script.

    Returns:
        argparse.Namespace: An object containing the parsed command-line arguments.
    """

    parser = argparse.ArgumentParser(
        description="Document the structure of a GitHub repository.",
        epilog=(
            "Example usage:\n"
            "Direct script invocation:\n"
            "  python repo2txt.py -r /path/to/repo -o output.txt\n"
            "When installed with pip as a command-line tool:\n"
            "  repo2txt -r /path/to/repo -o output.txt\n\n"
            "Note: The output will be saved in a text file (.txt)."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "-r",
        "--repo_path",
        default=os.getcwd(),
        help="Path to the directory to process (ie., cloned repo). if no path is specified defaults to the current directory.",
    )
    parser.add_argument(
        "-o",
        "--output_file",
        default=DEFAULT_OUTPUT_FILE,
        help='Name for the output text file. Defaults to "output.txt".',
    )
    parser.add_argument(
        "--ignore-files",
        nargs="*",
        default=[],
        help="List of file names to ignore. Omit this argument to ignore no file names.",
    )
    parser.add_argument(
        "--ignore-types",
        nargs="*",
        default=IMAGE_EXTENSIONS
        + VIDEO_EXTENSIONS
        + AUDIO_EXTENSIONS
        + DOCUMENT_EXTENSIONS
        + EXECUTABLE_EXTENSIONS,
        help="List of file extensions to ignore. Defaults to list in config.json. Omit this argument to ignore no types.",
    )
    parser.add_argument(
        "--exclude-dir",
        nargs="*",
        default=[],
        help='List of directory names to exclude or "none" for no directories.',
    )
    parser.add_argument(
        "--ignore-settings",
        action="store_true",
        help="Flag to ignore common settings files.",
    )
    parser.add_argument(
        "--include-dir",
        nargs="?",
        default=None,
        help="Specific directory to include. Only contents of this directory will be documented.",
    )
    parser.add_argument(
        "--use-gitignore",
        action="store_true",
        help="Flag to use .gitignore file patterns to exclude files and directories.",
    )
    return parser.parse_args()


def should_ignore(item, args, output_file_path, gitignore_patterns):
    """
    Determine if a given item should be ignored based on the script's arguments.

    Args:
        item (str): The path of the item (file or directory) to check.
        args (argparse.Namespace): Parsed command-line arguments.
        output_file_path (str): The path of the output file being written to.
        gitignore_patterns (list): List of patterns from .gitignore file.

    Returns:
        bool: True if the item should be ignored, False otherwise.
    """

    item_name = os.path.basename(item)
    file_ext = os.path.splitext(item_name)[1].lower()

    # Ensure the comparison is between path strings
    if os.path.abspath(item) == os.path.abspath(output_file_path):
        return True

    if os.path.isdir(item) and args.exclude_dir and item_name in args.exclude_dir:
        return True

    if args.include_dir and not os.path.abspath(item).startswith(
        os.path.abspath(args.include_dir)
    ):
        return True

    if os.path.isfile(item) and (
        item_name in args.ignore_files or file_ext in args.ignore_types
    ):
        return True

    if args.ignore_settings and file_ext in SETTINGS_EXTENSIONS:
        return True

    if args.use_gitignore:
        for pattern in gitignore_patterns:
            if os.path.relpath(item, start=args.repo_path).startswith(
                tuple(pattern.split("/"))
            ):
                return True

    return False


def load_gitignore_patterns(repo_path):
    """
    Load .gitignore patterns from the specified repository path.

    Args:
        repo_path (str): Path to the repository directory.

    Returns:
        list: List of patterns from the .gitignore file.
    """
    gitignore_path = os.path.join(repo_path, ".gitignore")
    patterns = []

    if os.path.exists(gitignore_path):
        with open(gitignore_path, "r", encoding="utf-8") as gitignore_file:
            patterns = [
                pattern.strip()
                for pattern in gitignore_file.readlines()
                if pattern.strip() and not pattern.strip().startswith("#")
            ]

    return patterns


def write_tree(
    dir_path,
    output_file,
    args,
    gitignore_patterns,
    prefix="",
    is_last=True,
    is_root=True,
):
    """
    Recursively write the directory tree to the output file, including the root directory name.

    Args:
        dir_path (str): The path of the directory to document.
        output_file (file object): The file object to write to.
        args (argparse.Namespace): Parsed command-line arguments.
        gitignore_patterns (list): List of patterns from .gitignore file.
        prefix (str): Prefix string for line indentation and structure. Defaults to "".
        is_last (bool): Flag to indicate if the item is the last in its level. Defaults to True.
        is_root (bool): Flag to indicate if the current directory is the root. Defaults to True.
    """

    if is_root:
        output_file.write(f"{os.path.basename(dir_path)}/\n")
        is_root = False

    items = os.listdir(dir_path)
    items.sort()  # Optional: Sort the items for consistent order
    num_items = len(items)

    for index, item in enumerate(items):
        item_path = os.path.join(dir_path, item)

        if should_ignore(item_path, args, args.output_file, gitignore_patterns):
            continue

        is_last_item = index == num_items - 1
        new_prefix = "└── " if is_last_item else "├── "
        child_prefix = "    " if is_last_item else "│   "

        output_file.write(f"{prefix}{new_prefix}{os.path.basename(item)}\n")

        if os.path.isdir(item_path):
            next_prefix = prefix + child_prefix
            write_tree(
                item_path,
                output_file,
                args,
                gitignore_patterns,
                next_prefix,
                is_last_item,
                is_root=False,
            )


def write_file_content(file_path, output_file, depth):
    """
    Write the contents of a given file to the output file with proper indentation.

    Args:
        file_path (str): Path of the file to read.
        output_file (file object): The file object to write the contents to.
        depth (int): Current depth in the directory tree for indentation.
    """
    indentation = "  " * depth
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as file:
            for line in file:
                # Indent each line of the file content
                output_file.write(f"{indentation}{line}")
    except Exception as e:
        output_file.write(f"{indentation}Error reading file: {e}\n")


def write_file_contents_in_order(
    dir_path, output_file, args, gitignore_patterns, depth=0
):
    """
    Recursively document the contents of files in the order they appear in the directory tree.

    Args:
        dir_path (str): The path of the directory to start documenting from.
        output_file (file object): The file object to write the contents to.
        args (argparse.Namespace): Parsed command-line arguments.
        gitignore_patterns (list): List of patterns from .gitignore file.
        depth (int): Current depth in the directory tree. Defaults to 0.
    """
    items = sorted(
        item
        for item in os.listdir(dir_path)
        if not should_ignore(
            os.path.join(dir_path, item), args, args.output_file, gitignore_patterns
        )
    )

    for item in items:
        item_path = os.path.join(dir_path, item)
        relative_path = os.path.relpath(item_path, start=args.repo_path)

        if os.path.isdir(item_path):
            write_file_contents_in_order(
                item_path, output_file, args, gitignore_patterns, depth + 1
            )
        elif os.path.isfile(item_path):
            output_file.write("  " * depth + f"[File Begins] {relative_path}\n")
            write_file_content(item_path, output_file, depth)
            output_file.write("\n" + "  " * depth + f"[File Ends] {relative_path}\n\n")


def main():
    """
    Main function to execute the script logic.
    """
    args = parse_args()

    # Convert 'none' keyword to empty list
    args.ignore_files = [] if args.ignore_files == ["none"] else args.ignore_files
    args.ignore_types = (
        []
        if args.ignore_types == ["none"]
        else IMAGE_EXTENSIONS
        + VIDEO_EXTENSIONS
        + AUDIO_EXTENSIONS
        + DOCUMENT_EXTENSIONS
        + EXECUTABLE_EXTENSIONS
        + ADDITIONAL_IGNORE_TYPES
    )
    args.exclude_dir = [] if args.exclude_dir == ["none"] else args.exclude_dir

    # Load .gitignore patterns
    gitignore_patterns = (
        load_gitignore_patterns(args.repo_path) if args.use_gitignore else []
    )

    # Check if the provided directory path is valid
    if not os.path.isdir(args.repo_path):
        print(
            f"Error: The specified directory does not exist, path is wrong or is not a directory: {args.repo_path}"
        )
        return  # Exit the script

    with open(args.output_file, "w") as output_file:
        output_file.write("Repository Documentation\n")
        output_file.write(
            "This document provides a comprehensive overview of the repository's structure and contents.\n"
            "The first section, titled 'Directory/File Tree', displays the repository's hierarchy in a tree format.\n"
            "In this section, directories and files are listed using tree branches to indicate their structure and relationships.\n"
            "Following the tree representation, the 'File Content' section details the contents of each file in the repository.\n"
            "Each file's content is introduced with a '[File Begins]' marker followed by the file's relative path,\n"
            "and the content is displayed verbatim. The end of each file's content is marked with a '[File Ends]' marker.\n"
            "This format ensures a clear and orderly presentation of both the structure and the detailed contents of the repository.\n\n"
        )

        output_file.write("Directory/File Tree Begins -->\n\n")
        write_tree(
            args.repo_path,
            output_file,
            args,
            gitignore_patterns,
            "",
            is_last=True,
            is_root=True,
        )
        output_file.write("\n<-- Directory/File Tree Ends")
        output_file.write("\n\nFile Content Begin -->\n")
        write_file_contents_in_order(
            args.repo_path, output_file, args, gitignore_patterns
        )
        output_file.write("\n<-- File Content Ends\n\n")


if __name__ == "__main__":
    main()
