# Tests

## Requirements
- pip
- Yoda environment

## Installation
Install pip requirements for tests:
```bash
$ python -m pip install -r requirements.txt
```

To run the UI tests you need Firefox 91 ESR or later and [geckodriver 0.31.0](https://github.com/mozilla/geckodriver/releases/tag/v0.31.0).
Geckodriver should be in your path before running the UI tests:
```bash
$ export PATH=$PATH:/path/to/geckodriver
```

## Usage
Run all tests:
```bash
$ pytest
```

Use `-k` to only run API or UI tests:
```bash
$ pytest -k api
```

If Yoda is not running on development address or test users / passwords are not the default, use `--environment` to specify environment file:
```bash
$ pytest --environment <environment_file>
```

Datarequest tests are disabled by default, enable using `--datarequest`:
```bash
$ pytest -k api --datarequest
```

Deposit tests are disabled by default, enable using `--deposit`:
```bash
$ pytest -k api --deposit
```

Intake tests are disabled by default, enable using `--intake`:
```bash
$ pytest -k api --intake
```

Login OIDC tests are disabled by default, enable using `--oidc`:
```bash
$ pytest -k ui --oidc
```

## Development
- Tests are written with Pytest-BDD: https://pytest-bdd.readthedocs.io/en/latest/
- UI tests use Splinter to automate browser actions: https://splinter.readthedocs.io/en/latest/index.html
