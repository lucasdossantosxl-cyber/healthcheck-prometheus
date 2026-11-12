"""Verificações reais do laboratório local; não inicia nem encerra serviços."""
import argparse
import base64
import json
import re
import socket
import time
import urllib.error
import urllib.parse
import urllib.request


def get(url, authenticated=False):
    headers = {}
    if authenticated:
        headers['Authorization'] = 'Basic ' + base64.b64encode(b'admin:admin').decode()
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=5) as response:
        return json.load(response)


def query(expression):
    params = urllib.parse.urlencode({'query': expression})
    return get('http://127.0.0.1:9090/api/v1/query?' + params)['data']['result']


def wait_for(label, predicate, timeout):
    deadline = time.monotonic() + timeout
    last_error = 'condição ainda não atendida'
    while time.monotonic() < deadline:
        try:
            if predicate():
                print(f'OK: {label}', flush=True)
                return
        except (OSError, ValueError, KeyError) as exc:
            last_error = str(exc)
        time.sleep(min(2, max(0, deadline - time.monotonic())))
    raise SystemExit(f'FALHOU: {label} após {timeout}s ({last_error})')


def metrics_ready():
    with urllib.request.urlopen('http://127.0.0.1:8000/metrics', timeout=5) as response:
        text = response.read().decode()
    return all(re.search(r'^' + name + r'\{', text, re.MULTILINE) for name in (
        'healthcheck_up', 'healthcheck_duration_seconds',
        'healthcheck_http_status_code', 'healthcheck_checks_total',
    ))


def grafana_ready():
    dashboard = get('http://127.0.0.1:3000/api/dashboards/uid/healthcheck-overview', True)
    datasource = get('http://127.0.0.1:3000/api/datasources/uid/prometheus/health', True)
    return len(dashboard['dashboard']['panels']) == 4 and datasource['status'] == 'OK'


def alerts_named(name, state=None):
    alerts = get('http://127.0.0.1:9090/api/v1/alerts')['data']['alerts']
    return [alert for alert in alerts
            if alert['labels'].get('alertname') == name
            and alert['labels'].get('job') == 'healthcheck'
            and (name != 'TargetDown' or alert['labels'].get('target') == 'demo-app')
            and (state is None or alert['state'] == state)]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('phase', choices=(
        'preflight', 'healthy', 'failure', 'recovery',
        'checker-failure', 'checker-recovery',
    ))
    parser.add_argument('--timeout', type=int, default=180)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error('--timeout deve ser maior que zero')

    if args.phase == 'preflight':
        for port in (3000, 8000, 8080, 9090):
            with socket.socket() as connection:
                connection.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                try:
                    connection.bind(('127.0.0.1', port))
                except OSError as exc:
                    raise SystemExit(f'Porta {port} indisponível: {exc}') from exc
        print('OK: as quatro portas estão livres', flush=True)
    elif args.phase == 'healthy':
        wait_for('quatro métricas expostas', metrics_ready, args.timeout)
        wait_for('scrape do checker UP', lambda: query('up{job="healthcheck"} == 1'), args.timeout)
        wait_for('demo-app disponível', lambda: query('healthcheck_up{target="demo-app"} == 1'), args.timeout)
        wait_for('disponibilidade com amostras suficientes', lambda: query(
            'sum by(target)(increase(healthcheck_checks_total[24h])) > 0'), args.timeout)
        wait_for('dashboard provisionado e datasource conectado', grafana_ready, args.timeout)
    elif args.phase == 'failure':
        wait_for('demo-app indisponível', lambda: query('healthcheck_up{target="demo-app"} == 0'), args.timeout)
        wait_for('TargetDown em firing', lambda: alerts_named('TargetDown', 'firing'), args.timeout)
    elif args.phase == 'recovery':
        wait_for('demo-app recuperado', lambda: query('healthcheck_up{target="demo-app"} == 1'), args.timeout)
        wait_for('TargetDown resolvido', lambda: not alerts_named('TargetDown'), args.timeout)
    elif args.phase == 'checker-failure':
        wait_for('scrape do checker falhando', lambda: query('up{job="healthcheck"} == 0'), args.timeout)
        wait_for('CheckerDown em firing', lambda: alerts_named('CheckerDown', 'firing'), args.timeout)
    else:
        wait_for('scrape do checker recuperado', lambda: query('up{job="healthcheck"} == 1'), args.timeout)
        wait_for('CheckerDown resolvido', lambda: not alerts_named('CheckerDown'), args.timeout)


if __name__ == '__main__':
    main()
