from typing import List, Callable
import subprocess
import sys 
import logging as log

class CLICommandError(Exception):
    """Exception raised if CLI command produced error."""
    pass


def run_cli_command(
    command: List[str], 
    env = None, 
    verbose: bool = True, 
    line_parser: Callable = None
):
    log.info('Running CLI command:' + ' '.join(command))

    process = subprocess.Popen(
        command,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        universal_newlines=True,
        bufsize=1
    )
    output = []

    while True:
        line = process.stdout.readline()
        if not line:
            break
        if line_parser:
            line_parser(line)
        if verbose:
            sys.stdout.write(line.strip() + "\n")

        output.append(line.strip())

    process.wait()
    if process.poll() != 0:
        raise CLICommandError("".join(process.stderr.readlines()))

    return output
