# creactivate virtual env
python -m venv .venv
source .venv/bin/activate

# Resolve py depdendencies
pip install --trusted-host pypi.org --trusted-host files.pythonhosted.org --upgrade pip
pip install pygame
