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

If Yoda is not running on development address, use --url to specify address:
```bash
$ pytest --url <url>
```
