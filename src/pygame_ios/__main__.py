import io
import json
import os
import shutil
import sys
import zipfile

import requests

BASE_API_PATH = "https://api.github.com/repos/seekerluke/pygame-ios-templates/releases/"
BASE_DOWNLOAD_PATH = (
    "https://github.com/seekerluke/pygame-ios-templates/releases/download/"
)
FOLDER_NAME = "pygame-ios-template"

VERSIONS_JSON_PATH = "https://raw.githubusercontent.com/seekerluke/pygame-ios-templates/refs/heads/main/patches/pygame-ce.json"


def check_args():
    result = len(sys.argv) >= 4
    if not result:
        print(
            "Usage: pygame-ios project_folder main_python_script pygame_ce_version [local_template_path]"
        )
    return result


def get_supported_pygame_versions() -> list[str]:
    try:
        response = requests.get(VERSIONS_JSON_PATH)
        response.raise_for_status()
        json_data = json.loads(response.content)
        return json_data["supportedVersions"]
    except requests.exceptions.HTTPError:
        return ["Failed to fetch supported versions."]


def get_latest_repository_version():
    response = requests.get(os.path.join(BASE_API_PATH, "latest"))
    response.raise_for_status()
    json_data = json.loads(response.content)
    return json_data["tag_name"]


def download_template(current_dir: str):
    template_dir = os.path.join(current_dir, FOLDER_NAME)
    if os.path.isdir(template_dir):
        print("pygame-ios template already exists. Skipping.")
        return

    version_number_prefixed = f"v{sys.argv[3]}"
    download_path = os.path.join(
        BASE_DOWNLOAD_PATH,
        get_latest_repository_version(),
        f"pygame-ios-template-{sys.argv[3]}.zip",
    )

    try:
        print(f"Downloading Xcode template for pygame-ce {version_number_prefixed}...")
        response = requests.get(download_path)
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        print(
            f"Xcode template for pygame-ce version {version_number_prefixed} does not exist. It might not be supported yet."
        )

        print("Supported versions:")
        for version in get_supported_pygame_versions():
            print(version)

        sys.exit(0)

    print("Extracting...")
    with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
        zf.extractall(template_dir)

    print("Xcode template downloaded successfully.")


def use_local_template(current_dir: str, local_path: str):
    template_dir = os.path.join(current_dir, FOLDER_NAME)
    if os.path.isdir(template_dir):
        print("pygame-ios template already exists. Skipping.")
        return

    print("Using local template.")
    print("Extracting...")
    with zipfile.ZipFile(local_path) as zf:
        zf.extractall(template_dir)

    print(f"Used local template from {local_path}.")


def copy_project_files(project_folder_path: str):
    dest_dir = os.path.join(
        project_folder_path, FOLDER_NAME, "pygame-ios", "app", "pygame-ios"
    )

    # remove old files first
    shutil.rmtree(dest_dir)
    shutil.copytree(
        project_folder_path,
        dest_dir,
        # don't copy the Xcode template into the Xcode template
        ignore=lambda src, names: [FOLDER_NAME],
    )

    new_main_path = os.path.join(dest_dir, sys.argv[2])
    new_main_path_name = os.path.join(dest_dir, "__main__.py")
    os.rename(new_main_path, new_main_path_name)

    print("Copied project files to Xcode template.")


def finalise():
    print(
        f'Done! Open the Xcode project under "{FOLDER_NAME}" and run the project on your chosen device or simulator.'
    )


def cli():
    if not check_args():
        return  # early exit

    project_folder_path = os.path.abspath(sys.argv[1])

    if len(sys.argv) > 4:
        local_template_path = os.path.realpath(sys.argv[4])
        use_local_template(project_folder_path, local_template_path)
    else:
        download_template(project_folder_path)

    copy_project_files(project_folder_path)
    finalise()


if __name__ == "__main__":
    cli()
