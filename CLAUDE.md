# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Purpose

`jslog4kube` is a small Python library that configures JSON-to-stdout logging for applications running in Kubernetes pods. It injects Kubernetes pod metadata (from downward-API volume files and prefixed env vars) into every log record, and provides a drop-in `GunicornLogger` replacement that applies the same JSON configuration to Gunicorn's error and access logs.

## Architecture

The library bootstraps in two phases that happen at **import time**:

1. **`jslog4kube/kube/bootstrap.py`** (imported as `jslog4kube/bootstrap.py` via the package `__init__`) — runs immediately on import. It reads:
   - Env vars prefixed by `KUBE_META_ENV_PREFIX` (default `X`) → lowercased into `LOG_ADDS`
   - `$KUBE_META/annotations` file → parsed `key=value` pairs (strips `kubernetes.io` entries) → merged into `LOG_ADDS`
   - `$KUBE_META/labels` file → parsed `key=value` pairs → merged into `LOG_ADDS`

   It then builds `format_str`, a space-separated `%(key)s` string covering the standard Python `LogRecord` fields plus all keys in `LOG_ADDS`. This string drives all formatters.

2. **`jslog4kube/kube/log_config.py`** — constructs the `LOGGING` dict (standard Python logging `dictConfig` format) using `format_str`. It defines:
   - `json` formatter → `pythonjsonlogger.jsonlogger.JsonFormatter`
   - `json-access` formatter → same, with `%(access)` appended for Gunicorn access logs
   - `KubeMetaInject` filter applied to all handlers
   - `json-stdout` handler → `StreamHandler` to `sys.stdout`

3. **`jslog4kube/kube/metadata_injector.py`** — `KubeMetaInject(logging.Filter)` is the runtime filter. Its `filter()` method stamps every `LogRecord` with the `LOG_ADDS` key/value pairs. For `gunicorn.access` records it also parses the `!`-and-`|`-delimited access log format string into a nested `record.access` dict.

4. **`jslog4kube/gunicorn/dictconfig_logger.py`** — `GunicornLogger` subclasses Gunicorn's built-in `Logger`. Its `setup()` configures the gunicorn error/access log handlers normally, then calls `dictConfig(LOGGING)` at the end to apply the JSON configuration across the whole logging system.

`GunicornLogger` is imported lazily in `__init__.py`; if `gunicorn` is not installed the import silently sets `HAS_GUNICORN = False`.

## Environment Variables

| Variable | Default | Effect |
|---|---|---|
| `KUBE_META` | `/etc/meta` | Directory where Kubernetes downward-API files (`labels`, `annotations`) are mounted |
| `KUBE_META_ENV_PREFIX` | `X` | Only env vars starting with `<PREFIX>_` are injected into log records |

## Installation

```bash
pip install .
# or in editable/dev mode:
pip install -e .
```

The only runtime dependency is `python-json-logger==2.0.7`. `gunicorn` is an optional dependency.

## Usage

### Plain Python / Django

```python
from logging.config import dictConfig
from jslog4kube import LOGGING

dictConfig(LOGGING)   # or assign directly as Django's LOGGING setting
```

Extend with your own loggers by updating `LOGGING['loggers']` before calling `dictConfig`.

### Gunicorn

In `gunicorn.conf`:
```python
access_log_format = 'remote!%({X-Forwarded-For}i)s|method!%(m)s|url-path!%(U)s|query!%(q)s|username!%(u)s|protocol!%(H)s|status!%(s)s|response-length!%(b)s|referrer!%(f)s|user-agent!%(a)s|request-time!%(L)s'
accesslog = '-'
logger_class = 'jslog4kube.GunicornLogger'
```

The access log format uses `!` as `=` and `|` as the field delimiter; `KubeMetaInject` parses this into a nested `access` dict in the JSON output.
