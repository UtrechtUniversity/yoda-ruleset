# Tests

## Requirements
- pip
- Yoda environment (running on https://portal.yoda.test)

## Installation
Install pip requirements for tests:
```bash
$ python -m pip install -r requirements.txt
```

To run the UI tests you need Firefox ESR 78.x and [geckodriver 0.26](https://github.com/mozilla/geckodriver/releases/tag/v0.26.0).
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

If Yoda is not running on development address or test password is not the default, use `--url` and `--password` to specify:
```bash
$ pytest --url <url> --password <password>
```

Datarequest tests are disabled by default, enable using `--datarequest`:
```bash
$ pytest -k api --datarequest
```
