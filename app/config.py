"""Configuração validada antes de abrir o servidor de métricas."""
from dataclasses import dataclass
import math
from pathlib import Path
from urllib.parse import urlsplit

import yaml


@dataclass(frozen=True)
class Target:
    name: str
    url: str
    expected_status: int


@dataclass(frozen=True)
class Config:
    interval_seconds: float
    timeout_seconds: float
    targets: tuple[Target, ...]


def positive_number(value, field):
    if (isinstance(value, bool) or not isinstance(value, (int, float))
            or not math.isfinite(value) or value <= 0):
        raise ValueError(f'{field} deve ser um número finito maior que zero')
    return float(value)


def load_config(path: str | Path) -> Config:
    try:
        data = yaml.safe_load(Path(path).read_text(encoding='utf-8'))
    except (OSError, yaml.YAMLError) as exc:
        raise ValueError(f'Não foi possível ler o YAML: {exc}') from exc
    if not isinstance(data, dict):
        raise ValueError('A configuração deve ser um objeto YAML')
    interval = positive_number(data.get('interval_seconds'), 'interval_seconds')
    timeout = positive_number(data.get('timeout_seconds'), 'timeout_seconds')
    rows = data.get('targets')
    if not isinstance(rows, list) or not rows:
        raise ValueError('targets deve ser uma lista não vazia')
    names, targets = set(), []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f'targets[{index}] deve ser um objeto')
        name, url, status = (row.get(key) for key in ('name', 'url', 'expected_status'))
        if not isinstance(name, str) or not name.strip() or name in names:
            raise ValueError(f'targets[{index}].name deve ser único e não vazio')
        try:
            parsed = urlsplit(url) if isinstance(url, str) else None
            valid_url = (parsed and parsed.scheme in ('http', 'https')
                         and parsed.hostname and not parsed.username
                         and not parsed.password and not parsed.fragment
                         and not any(char.isspace() for char in url))
            if parsed:
                parsed.port  # Valida também a porta.
        except ValueError:
            valid_url = False
        if not valid_url:
            raise ValueError(f'targets[{index}].url deve ser HTTP(S), sem credenciais ou fragmento')
        if type(status) is not int or not 100 <= status <= 599:
            raise ValueError(f'targets[{index}].expected_status deve ser inteiro entre 100 e 599')
        names.add(name)
        targets.append(Target(name, url, status))
    return Config(interval, timeout, tuple(targets))
