# Contributing

Thanks for your interest in our project. Contributions are always welcome!

We are committed to fostering a welcoming, respectful, and harassment-free
environment. Be kind!

If you have questions, ideas or want to report a bug, feel free to [open an
issue](issues). Or go ahead and [open a pull request](pulls) to contribute
code. In order to reduce the burden on our maintainers, please make sure that
your code follows our style guidelines outlined below.

## Developing

We recommend that you develop inside of a virtual environment. To set it up,
run the following commands in the root of your cloned repository:

```sh
python3.8 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install '.[docs,test]' pre-commit
pre-commit install
```

We additionally recommend that you set up your editor / IDE as follows.

- Indent with 4 spaces per level of indentation
- Maximum line length of 79 (add a ruler / thin line / highlighting / ...)
- *If you use Visual Studio Code*: Consider using a more open platform which
  supports third-party language servers, and continue with the next point.

  Otherwise, set up the editor to run `black`, `pylint` and `mypy` when saving.
  To enable automatic import sorting, add the following to your
  `settings.json`:

  ```json
  "[python]": {
      "editor.codeActionsOnSave": {
          "source.organizeImports": true
      }
  }
  ```

  Note that the Pylance language server is not recommended, as it occasionally
  causes false-positive errors for perfectly valid code.
- *If you do not use VSC*: Set up your editor to use the
  [`python-lsp-server`](https://github.com/python-lsp/python-lsp-server) with
  the plugins for [`mypy`](https://github.com/Richardk2n/mypy-ls),
  [`isort`](https://github.com/paradoxxxzero/pyls-isort) and
  [`black`](https://github.com/python-lsp/python-lsp-black), and make sure the
  built-in pylint plugin is enabled. This will provide as-you-type linting as
  well as automatic formatting on save. Language server clients are available
  for a wide range of editors, from Vim/Emacs to PyCharm/IDEA.

## Code style

We base our code style on a modified version of the [Google style guide for
Python code](https://google.github.io/styleguide/pyguide.html). The key
differences are:

- **Docstrings**: The [Numpy style
  guide](https://numpydoc.readthedocs.io/en/latest/format.html) applies here.
- **Linting**: Use [pylint](https://github.com/PyCQA/pylint) for static code
  analysis, and [mypy](https://github.com/python/mypy) for static type
  checking.
- **Formatting**: Use [black](https://github.com/psf/black) as code
  auto-formatter. The maximum line length is 79, as per
  [PEP-8](https://www.python.org/dev/peps/pep-0008/). This setting should be
  automatically picked up from the `pyproject.toml` file. The reason for the
  shorter line length is that it avoids wrapping and overflows in side-by-side
  split views (e.g. diffs) if there's also information displayed to the side of
  it (e.g. a tree view of the modified files).

  Be aware of the different line length of 72 for docstrings. We currently do
  not have a satisfactory solution to automatically apply or enforce this.

  Note that, while you're encouraged to do so in general, it is not a hard
  requirement to break up long strings into smaller parts. Additionally, never
  break up strings that are presented to the user in e.g. log messages, as that
  makes it significantly harder to grep for them.

  Use [isort](https://github.com/PyCQA/isort) for automatic sorting of imports.
  Its settings should automatically be picked up from the `pyproject.toml` file
  as well.
- **Typing**: We do not make an exception for `typing` imports. Instead of
  writing `from typing import SomeName`, use `import typing as t` and access
  typing related classes like `t.TypedDict`.

  Use the new syntax and classes for typing introduced with Python 3.10 and
  available using `from __future__ import annotations` since Python 3.8. Be
  aware however that this only works in the context of annotations; the code
  still needs to run on Python 3.8! This means that in some (rare) cases, you
  *must* use the old-style type hints.

  - Instead of `t.Tuple`, `t.List` etc. use the builtin classes `tuple`, `list`
    etc.
  - For classes that are not builtin (e.g. `Iterable`), `import collections.abc
    as cabc` and then use them like `cabc.Iterable`.
  - Use [PEP-604](https://www.python.org/dev/peps/pep-0604/)-style unions, e.g.
    `int | float` instead of `t.Union[int, float]`.
  - Use `... | None` (with `None` always as the last union member) instead of
    `t.Optional[...]` and always explicitly annotate where `None` is possible.
- **Python style rules**: For conflicting parts, the [Black code
  style](https://black.readthedocs.io/en/stable/the_black_code_style/current_style.html)
  wins. If you have set up `black` correctly, you don't need to worry about
  this though :)
- When working with `dict`s, consider using `t.TypedDict` instead of a more
  generic `dict[str, float|int|str]`-like annotation where possible, as the
  latter is much less precise (often requiring additional `assert`s or
  `isinstance` checks to pass) and can grow unwieldy very quickly.
- Prefer `t.NamedTuple` over `collections.namedtuple`, because the former uses
  a more convenient `class ...:` syntax and also supports type annotations.
