from retry import retry

from . import run_cli_command, CLICommandError
import logging as log


def check_awscli() -> bool:
    cmd = ["aws", "--version"]
    outputs = []
    try:
        run_cli_command(cmd, line_parser=lambda line: outputs.append(line))
        log.info(f'awscli version: {" ".join(outputs)}')
    except CLICommandError:
        return False

    return True


def check_aws_configuration(verbose: int = 0) -> bool:
    if check_awscli():
        log.info("awscli installation found")
    else:
        log.info(
            "`awscli` does not seem installed on the system. Please run `aptos_setup` to properly configure your machine."
        )
        return False

    cmd = ["aws", "configure", "list", "--profile", "aptos_user"]
    try:
        run_cli_command(cmd, verbose=(verbose == 2))
    except CLICommandError as e:
        log.info(str(e).strip())
        print(
            "Error locating user credentials. Please run `aptos_setup` to properly configure your Aptos access"
        )
        return False

    return True


@retry(exceptions=Exception, delay=20, tries=6, backoff=1)  # trying for 6 * 20 = 120 seconds
def check_s3_access(aptos_group_id: str, verbose: bool = False) -> None:

    cmd = [
        "aws",
        "s3",
        "ls",
        f"s3://aptos-data/account/{aptos_group_id}/",
        "--profile",
        "aptos_user",
    ]
    outputs = []
    try:
        run_cli_command(
            command=cmd,
            verbose=verbose,
            line_parser=lambda line: outputs.append(line.strip()),
        )
        print("S3 access verified")
    except CLICommandError as e:
        print(f"Cannot obtain AWS access: {e}")
        raise
