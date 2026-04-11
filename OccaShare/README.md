# OccaShare

A small FastAPI-based application.

## Running the server

`uvicorn` must be able to import the `app` package. Depending on your
current working directory this may fail with `ModuleNotFoundError: No
module named 'app'`. To avoid that:

1. **Use the helper script** (recommended):

    ```bash
    # from the repository root
    python run.py
    ```

    `run.py` adds the repository root to `sys.path` and then calls
    `uvicorn.run("app.main:app", ...)`. No manual PYTHONPATH tweaks are
    required.

2. **Or launch uvicorn directly:**

    ```bash
    cd OccaShare               # or otherwise ensure this folder is on PYTHONPATH
    uvicorn app.main:app --reload
    # or, from the repo root:
    # PYTHONPATH=./OccaShare uvicorn app.main:app --reload
    # or, reference the full package path:
    # uvicorn OccaShare.app.main:app --reload
    ```

    The key point is that the parent directory containing `app` must be
    in Python's module search path.

3. **Install the project** in editable mode if you plan to run it from
   anywhere:

    ```bash
    pip install -e .
    ```

   (requires a `setup.py` or `pyproject.toml` describing the package.)

With one of the above approaches the `ModuleNotFoundError` disappears and
`uvicorn` will import `app.main:app` correctly.