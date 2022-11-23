import aiohttp
import asyncio
import sys
from datetime import datetime, date, timedelta

class Client:
    async def __aenter__(self):
        self._session = aiohttp.ClientSession(cookie_jar=self._cookie_jar)
        return self
    async def __aexit__(self, *err):
        await self._session.close()
    def __init__(self, username: str, password: str):
        self._username = username
        self._password = password
        self._cookie_jar = aiohttp.CookieJar()
    def load_cookies(self, file_path):
        self._cookie_jar.load(file_path)
    def save_cookies(self, file_path):
        self._cookie_jar.save(file_path)
    async def login(self):
        self._cookie_jar.clear()
        await self._session.post('https://app.hotschedules.com/hs/prelogin.hs', 
                                data={'username': self._username, 'password': self._password},
                                headers={'Content-Type': 'application/x-www-form-urlencoded'})
        if 'hs_user' not in self._session.cookie_jar.filter_cookies('https://app.hotschedules.com/hs/prelogin.hs'): # type: ignore
            raise Exception('Login failed')
    async def _authed_request(self, method, url, **kwargs):
        if self._cookie_jar.filter_cookies(url).get('hs_user') is None:
            await self.login()
        async with self._session.request(method, url, allow_redirects=False, **kwargs) as resp:
            if resp.status != 302:
                return await resp.json()
            await self.login()
            async with self._session.request(method, url, allow_redirects=False, **kwargs) as resp:
                if resp.status == 302:
                    raise Exception('request failed')
                return await resp.json()
    async def get_employees(self):
        employees = await self._authed_request('GET', 'https://app.hotschedules.com/hs/spring/client/employee/?active=true')
        return [Employee(employee) for employee in employees]
    async def get_shifts(self, start: date, end: date):
        shifts = await self._authed_request('GET', f"https://app.hotschedules.com/hs/spring/shifts/posted/?start={start.strftime('%Y-%m-%d')}&end={end.strftime('%Y-%m-%d')}")
        return [Shift(shift) for shift in shifts]

class Employee:
    __slots__ = [
        'id',
        'first_name',
        'full_name',
        'last_name',
        'nickname',
    ]
    def __init__(self, data):
        self.id = data['id']
        self.first_name = data['firstname']
        self.last_name = data['lastname']
        self.full_name = data['displayFullName']
        self.nickname = data['nickname']
        if self.nickname == 'null':
            self.nickname = None
    def __str__(self):
        if self.nickname:
            return f'{self.full_name} ({self.nickname})'
        return self.full_name

class Shift:
    __slots__ = [
        'owner_id',
        'start',
        'duration',
    ]
    def __init__(self, data):
        self.owner_id = data['ownerId']
        self.start = datetime.strptime(data['startDate'], '%Y-%m-%d')
        timestamp = datetime.strptime(data['startTime'], '%H:%M')
        self.start = self.start.replace(hour=timestamp.hour, minute=timestamp.minute)
        self.duration = timedelta(minutes=data['duration'])
    @property
    def end(self):
        return self.start + self.duration

