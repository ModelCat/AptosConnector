from aptosconnector.utils import run_cli_command
from aptosconnector.utils.api import AwsAccessClient, APIConfig, APTOS_URL, APIError
from aptosconnector.utils.aws import check_awscli, check_aws_configuration
from pathlib import Path
import os.path as osp
import os
import json
import re
import uuid
from getpass_asterisk.getpass_asterisk import getpass_asterisk as getpass

_DEFAULT_REGION = "us-east-2"
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
        aptos_oauth_token = getpass("Aptos OAuth Token: ")
        if re.match(r"^\d+_[a-f0-9]{40}$", aptos_oauth_token):
            break
        print(
            "Oops... This does not look right. `Aptos OAuth Token` should be an integer followed by an underscore, followed by a 40 character string e.g.: 1_1234567890abcdef1234567890abcdef12345678"
        )

    # get the AWS access key credentials
    try:
        api_config = APIConfig(
            base_url=APTOS_URL,
            oauth_token=aptos_oauth_token,
        )
        storage_token_client = AwsAccessClient(api_config)
        creds = storage_token_client.get_aws_access(aptos_group_id)

        aws_access_key = creds["access_key_id"]
        aws_secret_access_key = creds["secret_access_key"]
    except APIError as ae:
        print(f"Aptos API error: {ae}")
        exit(1)

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

    print("-" * 50)
    # checking access to S3
    print("Verifying AWS access...")
    from aptosconnector.utils.aws import check_s3_access
    if not check_s3_access(aptos_group_id, verbose=verbose > 0):
        print("Verification failed... Please check your credentials or contact customer support.")
        exit(1)
    print("Verification successful.")

    # create Aptos config file
    aptos_config = {
        "aptos_group_id": aptos_group_id,
        "aptos_oauth_token": aptos_oauth_token,
    }

    aptos_path = osp.join(Path.home(), ".aptos")
    os.makedirs(aptos_path, exist_ok=True)
    with open(osp.join(aptos_path, "config.json"), "w") as fp:
        json.dump(aptos_config, fp, indent=4)

    print("-" * 50)
    print("Configuration complete.")
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
