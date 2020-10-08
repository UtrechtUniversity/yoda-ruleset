# Tests

## Requirements
- pip
- Yoda development environments (running on https://portal.yoda.test)
- Yoda CSRF and session cookie

## Installation
Install pip requirements for tests:
```bash
$ python -m pip install -r requirements.txt
```

## Usage
Run tests, replace <csrf> and <session> with Yoda CSRF and session cookie:
```bash
$ pytest --api https://portal.yoda.test/api --csrf <csrf> --session <session>
```
