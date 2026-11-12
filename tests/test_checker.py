import asyncio
import logging

import httpx
import pytest
from prometheus_client import CollectorRegistry

from app.checker import Metrics, check_target, monitor
from app.config import Target


@pytest.mark.parametrize('response_status, expected, up', [(200, 200, 1), (503, 200, 0), (204, 204, 1), (302, 200, 0)])
def test_http_response(response_status, expected, up):
    registry = CollectorRegistry()
    target = Target('demo', 'http://demo-app:8080', expected)
    metrics = Metrics([target], registry)

    async def scenario():
        transport = httpx.MockTransport(lambda request: httpx.Response(response_status))
        async with httpx.AsyncClient(transport=transport, trust_env=False) as client:
            await check_target(client, target, metrics)

    asyncio.run(scenario())
    assert registry.get_sample_value('healthcheck_up', {'target': 'demo'}) == up
    assert registry.get_sample_value('healthcheck_http_status_code', {'target': 'demo'}) == response_status
    assert registry.get_sample_value('healthcheck_duration_seconds', {'target': 'demo'}) >= 0
    assert registry.get_sample_value('healthcheck_checks_total', {'target': 'demo', 'result': 'success' if up else 'failure'}) == 1


@pytest.mark.parametrize('error', [httpx.ConnectError, httpx.ReadTimeout])
def test_transport_failure_then_recovery(error, caplog):
    registry = CollectorRegistry()
    target = Target('demo', 'http://demo-app:8080', 200)
    metrics = Metrics([target], registry)
    calls = 0

    def handler(request):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise error('simulated', request=request)
        return httpx.Response(200)

    async def scenario():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler), trust_env=False) as client:
            await check_target(client, target, metrics)
            assert registry.get_sample_value('healthcheck_up', {'target': 'demo'}) == 0
            assert registry.get_sample_value('healthcheck_http_status_code', {'target': 'demo'}) == 0
            await check_target(client, target, metrics)

    with caplog.at_level(logging.WARNING):
        asyncio.run(scenario())
    assert error.__name__ in caplog.text
    assert registry.get_sample_value('healthcheck_up', {'target': 'demo'}) == 1
    for result in ('success', 'failure'):
        assert registry.get_sample_value('healthcheck_checks_total', {'target': 'demo', 'result': result}) == 1


def test_total_timeout_and_stop():
    registry = CollectorRegistry()
    target = Target('demo', 'http://demo-app:8080', 200)
    metrics = Metrics([target], registry)

    async def handler(request):
        await asyncio.Event().wait()

    async def scenario():
        stop = asyncio.Event()
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler), trust_env=False) as client:
            task = asyncio.create_task(monitor(target, client, metrics, 10, 0.01, stop))
            for _ in range(100):
                if registry.get_sample_value('healthcheck_up', {'target': 'demo'}) == 0:
                    break
                await asyncio.sleep(0.01)
            stop.set()
            await asyncio.wait_for(task, 0.5)
    asyncio.run(scenario())
    assert registry.get_sample_value('healthcheck_up', {'target': 'demo'}) == 0
    assert registry.get_sample_value('healthcheck_checks_total', {'target': 'demo', 'result': 'failure'}) == 1
