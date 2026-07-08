# AGENTS.md

## Python Environment

- Use `uv` for Python environment management in this project.
- Create the virtual environment with `uv venv`.
- Add Python libraries with `uv add <package>`.
- Do not manually edit `pyproject.toml` or `uv.lock` when adding libraries through `uv add`; these files are updated automatically.
- Run programs and project commands through the `uv` environment.