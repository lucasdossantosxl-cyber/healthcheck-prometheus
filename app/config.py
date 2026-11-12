"""Configuração validada antes de abrir o servidor de métricas."""
from dataclasses import dataclass
import math
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import yaml


class UniqueKeyLoader(yaml.SafeLoader):
    def construct_mapping(self, node, deep=False):
        self.flatten_mapping(node)
        keys = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if not isinstance(key, str):
                raise yaml.YAMLError('Os nomes dos campos YAML devem ser texto')
            if key in keys:
                raise yaml.YAMLError(f'Chave YAML duplicada: {key}')
            keys.add(key)
        return super().construct_mapping(node, deep=deep)


def validate_fields(data, allowed, location):
    unknown = data.keys() - allowed
    if unknown:
        raise ValueError(f'{location} contém campos desconhecidos: {", ".join(sorted(unknown))}')


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
    message = f'{field} deve ser um número finito maior que zero'
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(message)
    try:
        result = float(value)
    except OverflowError as exc:
        raise ValueError(message) from exc
    if not math.isfinite(result) or result <= 0:
        raise ValueError(message)
    return result


def valid_http_url(url):
    if not isinstance(url, str) or '\\' in url or any(char.isspace() for char in url):
        return False
    try:
        parsed = urlsplit(url)
        client_url = httpx.URL(url)
        return bool(
            parsed.scheme in ('http', 'https')
            and parsed.hostname and client_url.host
            and parsed.username is None and parsed.password is None
            and '#' not in url
            and (parsed.port is None or 1 <= parsed.port <= 65535)
            and ('%' not in parsed.hostname or ':' in parsed.hostname)
        )
    except (ValueError, httpx.InvalidURL):
        return False


def load_config(path: str | Path) -> Config:
    try:
        data = yaml.load(Path(path).read_text(encoding='utf-8'), Loader=UniqueKeyLoader)
    except (OSError, UnicodeError, yaml.YAMLError) as exc:
        raise ValueError(f'Não foi possível ler o YAML: {exc}') from exc
    if not isinstance(data, dict):
        raise ValueError('A configuração deve ser um objeto YAML')
    validate_fields(data, {'interval_seconds', 'timeout_seconds', 'targets'}, 'configuração')
    interval = positive_number(data.get('interval_seconds'), 'interval_seconds')
    timeout = positive_number(data.get('timeout_seconds'), 'timeout_seconds')
    rows = data.get('targets')
    if not isinstance(rows, list) or not rows:
        raise ValueError('targets deve ser uma lista não vazia')
    names, targets = set(), []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise ValueError(f'targets[{index}] deve ser um objeto')
        validate_fields(row, {'name', 'url', 'expected_status'}, f'targets[{index}]')
        name, url, status = (row.get(key) for key in ('name', 'url', 'expected_status'))
        if not isinstance(name, str) or not name.strip() or name in names:
            raise ValueError(f'targets[{index}].name deve ser único e não vazio')
        if not valid_http_url(url):
            raise ValueError(f'targets[{index}].url deve ser HTTP(S), sem credenciais ou fragmento')
        if type(status) is not int or not 100 <= status <= 599:
            raise ValueError(f'targets[{index}].expected_status deve ser inteiro entre 100 e 599')
        names.add(name)
        targets.append(Target(name, url, status))
    return Config(interval, timeout, tuple(targets))
