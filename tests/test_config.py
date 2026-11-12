import pytest

from app.config import load_config


VALID = '''interval_seconds: 15
timeout_seconds: 5
targets:
  - name: demo
    url: http://demo-app:8080
    expected_status: 200
'''


def test_valid_config(tmp_path):
    path = tmp_path / 'config.yaml'
    path.write_text(VALID)
    config = load_config(path)
    assert config.interval_seconds == 15
    assert config.timeout_seconds == 5
    assert config.targets[0].name == 'demo'
    assert config.targets[0].expected_status == 200


@pytest.mark.parametrize('text, message', [
    ('[]', 'objeto YAML'),
    ('[', 'ler o YAML'),
    (VALID.replace('15', '0'), 'interval_seconds'),
    (VALID.replace('15', '.nan'), 'interval_seconds'),
    (VALID.replace('15', 'true'), 'interval_seconds'),
    (VALID.replace('timeout_seconds: 5', 'timeout_seconds: -1'), 'timeout_seconds'),
    ('interval_seconds: 1\ntimeout_seconds: 1\ntargets: []', 'lista não vazia'),
    (VALID.replace('name: demo', 'name: ""'), 'name'),
    (VALID.replace('http://demo-app:8080', 'ftp://example.com'), 'url'),
    (VALID.replace('http://demo-app:8080', 'http://user:pass@example.com'), 'url'),
    (VALID.replace('http://demo-app:8080', 'http://demo-app:invalid'), 'url'),
    (VALID.replace('expected_status: 200', 'expected_status: true'), 'expected_status'),
    (VALID.replace('expected_status: 200', 'expected_status: 600'), 'expected_status'),
    (VALID + '  - name: demo\n    url: https://example.com\n    expected_status: 200\n', 'name'),
])
def test_invalid_config(tmp_path, text, message):
    path = tmp_path / 'config.yaml'
    path.write_text(text)
    with pytest.raises(ValueError, match=message):
        load_config(path)


def test_missing_file(tmp_path):
    with pytest.raises(ValueError, match='ler o YAML'):
        load_config(tmp_path / 'missing.yaml')
