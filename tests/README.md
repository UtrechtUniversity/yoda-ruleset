# Tests

## Requirements
- pip
- Yoda development environments (running on https://portal.yoda.test)
- CSRF and session cookie

## Installation
    ```bash
    $ python -m pip install -r requirements.txt
    ```

## Usage
    ```bash
    $ pytest --api https://portal.yoda.test/api --csrf <csrf> --session <session>
    ```
