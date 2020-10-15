# Tests

## Requirements
- pip
- Yoda environment (running on https://portal.yoda.test)

## Installation
Install pip requirements for tests:
```bash
$ python -m pip install -r requirements.txt
```

## Usage
Run tests:
```bash
$ pytest
```

If Yoda is not running on development address or test password is not the default, use --url and --password to specify:
```bash
$ pytest --url <url> --password <password>
```
