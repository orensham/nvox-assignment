# nvox-api

## Running the server locally

When running locally, the `.env` file is used automatically with sane defaults for running locally with the
infrastructure from Docker Compose.

1. Install [`uv`](https://docs.astral.sh/uv/getting-started/installation/)

    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

2. Sync the project dependencies

    ```bash
    uv sync --package nvox-api
    ```

3. Run the required infrastructure with Docker Compose

    ```bash
    docker-compose -d --profile infra up
    ```

### Via PyCharm

Create a new _FastAPI run configuration_ with the following properties:

| Setting               | Value                                                                                                                                                                      |
|-----------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| Name                  | nvox-api                                                                                                                                                                  |
| Script path           | /path/to/nvox-api/src/nvox_api/main.py                                                                                                                     |
| Uvicorn options       | `--reload --host 0.0.0.0`                                                                                                                                                  |
| Python interpreter    | (select your project's UV virtual env)                                                                                                                                     |
| Environment variables ||
| Working directory     | `$ProjectFileDir$/nvox-api/src`                                                                                                                                      |

### Via Terminal

1. Set the required environment variables
   use `export KEY=value`

2. Run the service

    ```bash
    uv run fastapi run src/nvox_api/main.py
    ```