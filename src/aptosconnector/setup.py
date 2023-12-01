from aptosconnector.utils import run_cli_command
from aptosconnector.utils.aws import check_awscli, check_aws_configuration
from pathlib import Path
import os.path as osp
import os
import json
import re
import uuid
from getpass_asterisk.getpass_asterisk import getpass_asterisk as getpass

_DEFAULT_REGION = "us-east-1"
_DEFAULT_FORMAT = "json"
_DEFAULT_AWS_PROFILE = "aptos_user"


def run_setup(verbose: int = 0):
    print("Welcome to AptosConnector one-time setup wizzard.")
    print("We'll get you started in just a few simple steps!")
    print("-" * 50)
    if not check_awscli():
        print("Error: AWS CLI was not detected on your system.")
        print("Please install it and run the setup program again")
        print(
            "For install instuctions go to: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html"
        )
        exit(1)
    else:
        print("AWS CLI installation verified.")
        print("-" * 50)

    while 1:
        aptos_group_id = input("Aptos Group ID: ")
        try:
            uuid.UUID(str(aptos_group_id))
            break
        except Exception:
            print(
                "Oops... This does not look right. `Aptos Account ID` should be a valid UUID in XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX format"
            )

    while 1:
        aws_access_key = input("Aptos AWS Access Key ID: ")
        if re.match("(?<![A-Z0-9])[A-Z0-9]{20}(?![A-Z0-9])", aws_access_key):
            break
        print(
            "Oops... This does not look right. `Aptos AWS Access Key ID` should be a 20 character alpha-numerical string e.g.: BCASYP3U22NYBISXY5IL"
        )

    while 1:
        aws_secret_access_key = getpass("Aptos AWS Secret Access Key: ")
        # aws_secret_access_key   = input("Aptos AWS Secret Access Key: ")
        if re.match(
            "(?<![A-Za-z0-9/+=])[A-Za-z0-9/+=]{40}(?![A-Za-z0-9/+=])",
            aws_secret_access_key,
        ):
            break
        print(
            "Oops... This does not look right. `Aptos AWS Secret Access Key` should be a 40 character string e.g.: bul7642gBX/hCshqU48wXc5Xt8gO+SEdswOho2YM"
        )

    # configure AWS CLI
    outputs = []

    def append_fn(line):
        outputs.append(line)

    try:
        cmd = [
            "aws",
            "configure",
            "set",
            "region",
            _DEFAULT_REGION,
            "--profile",
            _DEFAULT_AWS_PROFILE,
        ]
        run_cli_command(cmd, line_parser=append_fn)
        cmd = [
            "aws",
            "configure",
            "set",
            "format",
            _DEFAULT_FORMAT,
            "--profile",
            _DEFAULT_AWS_PROFILE,
        ]
        run_cli_command(cmd, line_parser=append_fn)
        cmd = [
            "aws",
            "configure",
            "set",
            "aws_access_key_id",
            aws_access_key,
            "--profile",
            _DEFAULT_AWS_PROFILE,
        ]
        run_cli_command(cmd, line_parser=append_fn)
        cmd = [
            "aws",
            "configure",
            "set",
            "aws_secret_access_key",
            aws_secret_access_key,
            "--profile",
            _DEFAULT_AWS_PROFILE,
        ]
        run_cli_command(cmd, line_parser=append_fn)
    except Exception as e:
        print(f"AWS configuration failure: {e}")
        if verbose:
            print("\n".join(outputs))
        exit(1)

    if not check_aws_configuration(verbose):
        print("Configuration failed.")

    # create Aptos config file
    aptos_config = {"aptos_group_id": aptos_group_id}

    aptos_path = osp.join(Path.home(), ".aptos")
    os.makedirs(aptos_path, exist_ok=True)
    with open(osp.join(aptos_path, "config.json"), "w") as fp:
        json.dump(aptos_config, fp, indent=4)

    print("-" * 50)
    print("Configuration successful!")
    print("")
    print("Now you can use:")
    print(
        "\t`aptos_validate` to check your dataset for errors and verify Aptos interoperability"
    )
    print("\t`aptos_upload` to upload dataset to Aptos platform")


def setup_cli():
    run_setup(verbose=1)


if __name__ == "__main__":
    setup_cli()
