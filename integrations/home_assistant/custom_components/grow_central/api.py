"""Local authenticated API client. TLS verification stays enabled."""
from urllib.parse import quote, urlparse
import asyncio
import math

PREFIX = '/api/v1/home-assistant'


def validate_url(value):
    parsed = urlparse(value)
    if (parsed.scheme not in {'http', 'https'} or not parsed.hostname or
            parsed.username or parsed.password or parsed.path not in {'', '/'} or
            parsed.query or parsed.fragment):
        raise ValueError('Expected a plain HTTP(S) origin')
    return value.rstrip('/')


class GrowCentralAPI:
    def __init__(self, session, url, token):
        self.session = session
        self.url = validate_url(url)
        self.headers = {'Authorization': f'Bearer {token}'}

    async def request(self, path, payload=None):
        async with asyncio.timeout(15):
            async with self.session.request('GET' if payload is None else 'POST',
                self.url + PREFIX + path, headers=self.headers, json=payload,
                allow_redirects=False) as response:
                if response.status in {401, 403}:
                    raise PermissionError('Bridge authentication or permission denied')
                if response.status != 200:
                    raise ConnectionError(f'Grow Central HTTP {response.status}')
                return await response.json()

    async def snapshot(self):
        result = await self.request('/snapshot')
        if not isinstance(result, dict) or result.get('schema') != 1 or not isinstance(result.get('devices'), list):
            raise ValueError('Unsupported Grow Central response')
        devices = {}
        for row in result['devices']:
            if (not isinstance(row, dict) or not isinstance(row.get('id'), str) or
                not isinstance(row.get('name'), str) or not isinstance(row.get('online'), bool) or
                not isinstance(row.get('writable'), bool) or
                (row.get('on') is not None and not isinstance(row['on'], bool)) or
                not isinstance(row.get('measurements'), dict) or row['id'] in devices):
                raise ValueError('Malformed Grow Central device')
            for metric in row['measurements'].values():
                if (not isinstance(metric, dict) or not isinstance(metric.get('unit'), str) or
                    not isinstance(metric.get('device_class'), str) or
                    not isinstance(metric.get('value'), (float, int)) or
                    isinstance(metric['value'], bool) or not math.isfinite(metric['value'])):
                    raise ValueError('Malformed Grow Central measurement')
            devices[row['id']] = row
        return devices

    async def switch(self, identifier, on):
        return await self.request('/devices/' + quote(identifier, safe='') + '/switch', {'on': on})
