import pytest
import yaml

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


@pytest.mark.parametrize('text, field', [
    (VALID + 'interval_seconds: 30\n', 'interval_seconds'),
    (VALID.replace('    expected_status: 200', '    expected_status: 200\n    expected_status: 503'), 'expected_status'),
    (VALID.replace('    url: http://demo-app:8080', '    url: http://demo-app:8080\n    url: https://example.com'), 'url'),
])
def test_duplicate_keys_are_not_silently_overwritten(tmp_path, text, field):
    path = tmp_path / 'config.yaml'
    path.write_text(text)
    with pytest.raises(ValueError, match=f'Chave YAML duplicada: {field}'):
        load_config(path)


@pytest.mark.parametrize('text, field', [
    (VALID + 'retry_attempts: 3\n', 'retry_attempts'),
    (VALID.replace('interval_seconds:', 'interval_second:'), 'interval_second'),
    (VALID.replace('    expected_status:', '    expected_staus:'), 'expected_staus'),
    (VALID.replace('    expected_status: 200', '    expected_status: 200\n    retry_attempts: 3'), 'retry_attempts'),
])
def test_unknown_fields_report_the_mistyped_key(tmp_path, text, field):
    path = tmp_path / 'config.yaml'
    path.write_text(text)
    with pytest.raises(ValueError, match=f'campos desconhecidos: {field}'):
        load_config(path)


@pytest.mark.parametrize('url', [
    'http://demo-app:8080',
    'http://[::1]:8080/status',
    'https://münich.example/status?check=1',
    'https://example.com/path%20with%20spaces',
])
def test_supported_http_urls_remain_valid(tmp_path, url):
    data = yaml.safe_load(VALID)
    data['targets'][0]['url'] = url
    path = tmp_path / 'config.yaml'
    path.write_text(yaml.safe_dump(data), encoding='utf-8')
    assert load_config(path).targets[0].url == url


@pytest.mark.parametrize('url', [
    'https://☃.example',
    'https://xn--invalid-.example',
    'http://example.com/\x00',
    'http://example.com\x7f',
    'http://example.com:0',
    'http://example.com:65536',
    'http://example.com#',
    'http://@example.com',
    'http://exa\\mple.com',
    'http://exa%mple.com',
])
def test_malformed_urls_fail_before_startup(tmp_path, url):
    data = yaml.safe_load(VALID)
    data['targets'][0]['url'] = url
    path = tmp_path / 'config.yaml'
    path.write_text(yaml.safe_dump(data), encoding='utf-8')
    with pytest.raises(ValueError, match=r'targets\[0\]\.url'):
        load_config(path)


def test_huge_interval_reports_validation_error(tmp_path):
    path = tmp_path / 'config.yaml'
    path.write_text(VALID.replace('interval_seconds: 15', 'interval_seconds: ' + '1' + '0' * 400))
    with pytest.raises(ValueError, match='interval_seconds deve ser um número finito'):
        load_config(path)


def test_non_text_yaml_keys_report_validation_error(tmp_path):
    path = tmp_path / 'config.yaml'
    path.write_text(VALID + '123: value\n')
    with pytest.raises(ValueError, match='nomes dos campos YAML devem ser texto'):
        load_config(path)


def test_invalid_utf8_reports_config_error(tmp_path):
    path = tmp_path / 'config.yaml'
    path.write_bytes(b'\xff\xfe')
    with pytest.raises(ValueError, match='ler o YAML'):
        load_config(path)
