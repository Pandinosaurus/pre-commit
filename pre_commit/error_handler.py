import contextlib
import functools
import os.path
import sys
import traceback
from typing import Generator

import pre_commit.constants as C
from pre_commit import output
from pre_commit.errors import FatalError
from pre_commit.store import Store
from pre_commit.util import cmd_output_b
from pre_commit.util import force_bytes


def _log_and_exit(
    msg: str,
    ret_code: int,
    exc: BaseException,
    formatted: str,
) -> None:
    error_msg = f'{msg}: {type(exc).__name__}: '.encode() + force_bytes(exc)
    output.write_line_b(error_msg)

    _, git_version_b, _ = cmd_output_b('git', '--version', retcode=None)
    git_version = git_version_b.decode(errors='backslashreplace').rstrip()

    storedir = Store().directory
    log_path = os.path.join(storedir, 'pre-commit.log')
    with contextlib.ExitStack() as ctx:
        if os.access(storedir, os.W_OK):
            output.write_line(f'Check the log at {log_path}')
            log = ctx.enter_context(open(log_path, 'wb'))
        else:  # pragma: win32 no cover
            output.write_line(f'Failed to write to log at {log_path}')
            log = sys.stdout.buffer

        _log_line = functools.partial(output.write_line, stream=log)
        _log_line_b = functools.partial(output.write_line_b, stream=log)

        _log_line('### version information')
        _log_line()
        _log_line('```')
        _log_line(f'pre-commit version: {C.VERSION}')
        _log_line(f'git --version: {git_version}')
        _log_line('sys.version:')
        for line in sys.version.splitlines():
            _log_line(f'    {line}')
        _log_line(f'sys.executable: {sys.executable}')
        _log_line(f'os.name: {os.name}')
        _log_line(f'sys.platform: {sys.platform}')
        _log_line('```')
        _log_line()

        _log_line('### error information')
        _log_line()
        _log_line('```')
        _log_line_b(error_msg)
        _log_line('```')
        _log_line()
        _log_line('```')
        _log_line(formatted.rstrip())
        _log_line('```')
    raise SystemExit(ret_code)


@contextlib.contextmanager
def error_handler() -> Generator[None, None, None]:
    try:
        yield
    except (Exception, KeyboardInterrupt) as e:
        if isinstance(e, FatalError):
            msg, ret_code = 'An error has occurred', 1
        elif isinstance(e, KeyboardInterrupt):
            msg, ret_code = 'Interrupted (^C)', 130
        else:
            msg, ret_code = 'An unexpected error has occurred', 3
        _log_and_exit(msg, ret_code, e, traceback.format_exc())
