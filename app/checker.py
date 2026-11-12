"""Checagens concorrentes, métricas e encerramento via SIGTERM/SIGINT."""
import argparse
import asyncio
import logging
import signal
import time

import httpx
from prometheus_client import Counter, Gauge, REGISTRY, start_http_server

from app.config import Target, load_config

LOG = logging.getLogger(__name__)


class Metrics:
    def __init__(self, targets, registry=REGISTRY):
        self.up = Gauge('healthcheck_up', 'Último resultado: sucesso=1, falha=0', ['target'], registry=registry)
        self.duration = Gauge('healthcheck_duration_seconds', 'Duração da última checagem em segundos', ['target'], registry=registry)
        self.status = Gauge('healthcheck_http_status_code', 'Último status HTTP, 0 sem resposta', ['target'], registry=registry)
        self.checks = Counter('healthcheck_checks_total', 'Total de checagens por resultado', ['target', 'result'], registry=registry)
        for target in targets:
            # Contadores começam em zero; gauges só existem após a primeira checagem.
            for result in ('success', 'failure'):
                self.checks.labels(target.name, result)


async def check_target(client: httpx.AsyncClient, target: Target, metrics: Metrics):
    started, status = time.perf_counter(), 0
    try:
        # Streaming evita baixar corpos grandes. Redirects são avaliados como recebidos.
        async with client.stream('GET', target.url, follow_redirects=False) as response:
            status = response.status_code
    except httpx.HTTPError as exc:
        LOG.warning('target=%s erro=%s', target.name, type(exc).__name__)
    duration = time.perf_counter() - started
    success = status == target.expected_status
    metrics.up.labels(target.name).set(int(success))
    metrics.duration.labels(target.name).set(duration)
    metrics.status.labels(target.name).set(status)
    metrics.checks.labels(target.name, 'success' if success else 'failure').inc()
    LOG.info('target=%s status=%d sucesso=%s duração=%.3fs', target.name, status, success, duration)


async def monitor(target, client, metrics, interval, timeout, stop):
    while not stop.is_set():
        started = time.perf_counter()
        try:
            # Limite total: inclui DNS, conexão e recebimento dos headers.
            await asyncio.wait_for(check_target(client, target, metrics), timeout=timeout)
        except TimeoutError:
            metrics.up.labels(target.name).set(0)
            metrics.duration.labels(target.name).set(time.perf_counter() - started)
            metrics.status.labels(target.name).set(0)
            metrics.checks.labels(target.name, 'failure').inc()
            LOG.warning('target=%s erro=total_timeout', target.name)
        delay = max(0, interval - (time.perf_counter() - started))
        try:
            await asyncio.wait_for(stop.wait(), timeout=delay)
        except TimeoutError:
            pass


async def run(config):
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)
    metrics = Metrics(config.targets)
    server, thread = start_http_server(8000)
    try:
        # Configuração explícita: não lê proxies nem certificados do ambiente.
        async with httpx.AsyncClient(timeout=config.timeout_seconds, trust_env=False) as client:
            tasks = [asyncio.create_task(monitor(t, client, metrics, config.interval_seconds,
                                                config.timeout_seconds, stop)) for t in config.targets]
            try:
                await asyncio.gather(*tasks)
            finally:
                for task in tasks:
                    task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
    finally:
        LOG.info('Encerrando servidor de métricas')
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def main():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config.yaml')
    args = parser.parse_args()
    try:
        config = load_config(args.config)
    except ValueError as exc:
        parser.error(str(exc))
    asyncio.run(run(config))


if __name__ == '__main__':
    main()
