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
