#!/usr/bin/env python3
import platform

from argparse import ArgumentParser
from grp import getgrnam
from os import getcwd
from os.path import join
from shutil import which
from subprocess import run


def main():
    parser = ArgumentParser("Bootstrap a Runbot Docker Compose setup")
    parser.add_argument(
        "-d",
        "--domain",
        default="runbot.vauxoo.test",
        type=str,
        help="Domain name for the Runbot instance",
    )
    args = parser.parse_args()

    if not which("envsubst"):
        raise SystemExit("Required executable 'envsubst' not found in the system")

    prefix = ""
    try:
        if platform.system() == 'Linux':
            prefix = f"DOCKER_GID={getgrnam('docker').gr_gid}"
    except KeyError:
        raise SystemExit("Required group 'docker' not found in the system")

    run(
        f"{prefix} RUNBOT_NAME={args.domain} envsubst < compose.yaml.template > compose.yaml",
        cwd=join(getcwd(), ".docker"),
        shell=True,
    )

    print(
        "Success. You can now start your Runbot instance with 'docker compose -f .docker/compose.yaml up'."
        "\nTODO: Run the following command in the runbot container: 'chown runbot:runbot /var/run/docker.sock && docker login quay.io'"
    )


if __name__ == "__main__":
    main()
