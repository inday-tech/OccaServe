# How to Run Project Scripts

Since the project scripts have been moved to the `scripts/` directory, you need to ensure the root directory is in your `PYTHONPATH` so that the scripts can find the `app` module.

### Windows (PowerShell)
```powershell
$env:PYTHONPATH = ".;$env:PYTHONPATH"
python scripts/utils/check_db.py
```

### Windows (CMD)
```cmd
set PYTHONPATH=.
python scripts/utils/check_db.py
```

## Directory Structure Overview

- `scripts/migrations/`: Database schema, migrations, resets, and seed data.
- `scripts/debug/`: Scripts for debugging login and admin functions.
- `scripts/utils/`: General utilities like database checks and admin creation.
