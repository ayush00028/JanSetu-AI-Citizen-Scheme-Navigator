# JanSetu — Citizen Service Navigator

JanSetu is a FastAPI web application that helps citizens discover government schemes, track service applications, maintain a profile and documents, and use a mock DigiLocker connection.

## Requirements

- Python 3.10 or newer (Python 3.12 recommended)
- Git (only needed to clone or publish the project)
- A modern browser

No external database is required for local development. By default, the app creates a SQLite database named `citizen_navigator.db` in the project directory.

## Install and run

Clone or download the project, then open a terminal in the project folder.

### macOS and Linux

```bash
git clone <repository-url>
cd JanSetuV2

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

uvicorn main:app --reload
```

Open <http://127.0.0.1:8000> in your browser. Stop the server with `Ctrl+C`. On later runs, activate the environment with `source .venv/bin/activate` before starting Uvicorn.

### Windows (PowerShell)

```powershell
git clone <repository-url>
cd JanSetuV2

py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

uvicorn main:app --reload
```

Open <http://127.0.0.1:8000> in your browser. If PowerShell blocks activation, run the following once for the current terminal, then activate the environment again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

For Command Prompt instead, activate it with:

```bat
.venv\Scripts\activate.bat
```

## Demo account

On a new local database, the server creates a demo account:

- Email: `demo@jansetu.in`
- Password: `demo123`

You can also register your own account from the app.

## Configuration

Create an optional `.env` file in the project root to override defaults:

```env
# SQLite is the local default; PostgreSQL can be used for deployment.
DATABASE_URL=sqlite:///./citizen_navigator.db

# Optional DigiLocker settings. The app uses a local mock flow when omitted.
DIGILOCKER_CLIENT_ID=your-client-id
DIGILOCKER_REDIRECT_URI=http://localhost:8000/api/digilocker/callback
```

## Tests

With the virtual environment activated:

```bash
pytest -q
```

## Publish to a new GitHub repository

1. Create a new empty repository on GitHub. Do not initialize it with a README, license, or `.gitignore`.
2. Copy its HTTPS or SSH URL, for example `https://github.com/your-name/jansetu.git`.
3. Run the platform-specific publish script below from the project root. It stages source files while excluding local databases, virtual environments, caches, and environment secrets; creates a commit if needed; then updates `origin` and pushes `main`.

macOS/Linux/Git Bash:

```bash
bash scripts/push-new-repo.sh https://github.com/your-name/jansetu.git
```

Windows PowerShell:

```powershell
.\scripts\push-new-repo.ps1 https://github.com/your-name/jansetu.git
```

The scripts stop if the Git index already contains staged changes, so review or commit those changes first. Authentication is handled by your existing Git credential manager or SSH key.

## Deployment

The repository includes `render.yaml` and a `Procfile` for deployment. Set `DATABASE_URL` to a PostgreSQL connection string in production.
# Jansetu-Gemini-assistant
