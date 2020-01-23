import asyncio
import datetime
import json
import re
from typing import Any, Dict, Iterable, Optional, Set, Union

import attr
import httpx
import structlog
from aiocache import cached
from bs4 import BeautifulSoup
from toolz import first, identity

log = structlog.get_logger()


@attr.s
class DataClient:
    client: httpx.AsyncClient = attr.ib()

    @client.default
    def _default_client(self):
        return httpx.AsyncClient()

    async def _get(self, url: str, **kwargs) -> httpx.Response:
        log.debug("_get", url=url, **kwargs)
        return await self.client.get(url, **kwargs)

    async def get_snodata_token(self, client: httpx.AsyncClient = None) -> str:

        resp = await self._get("https://www.nwac.us/weatherdata/alpental/now")
        resp.raise_for_status()
        token, = re.search(r'const token = "(\w+)"', resp.text).groups()

        log.info("get_snodata_token", token=token)
        return token

    async def get_snodata_stations(self,) -> Dict[str, str]:
        token = await self.get_snodata_token()
        url = (
            f"https://api.snowobs.com/v1/station/current"
            f"?token={token}&units=english&qc=true&source=nwac"
        )

        station_data = json.loads((await self._get(url)).text)

        return {
            s["NAME"]: s["STID"] for s in station_data["station_current"]["STATION"]
        }

    async def get_site_list(self) -> Set[str]:

        resp = await self._get("https://www.nwac.us/weatherdata/")
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, features="html.parser")

        return {
            l.find("a", class_="station-link")
            .attrs["href"]
            .split("/")[2]: l.text.split("\n")[1]
            .strip()
            for l in soup.find_all("li", class_="station-title-cell")
        }

    @staticmethod
    def _fmt_time(dt: Optional[datetime.datetime]) -> Optional[str]:
        if dt is not None:
            return dt.strftime("%Y%m%d%H%M")
        else:
            return None

    @cached()
    async def _get_site_data(
        self,
        site_id: str,
        start: datetime.datetime = None,
        end: datetime.datetime = None,
    ) -> Any:
        log.info("get_site_data", site_id=site_id, start=start, end=end)
        resp = await self._get(f"https://www.nwac.us/weatherdata/{site_id}/now")
        resp.raise_for_status()
        nowsoup = BeautifulSoup(resp.text, features="html.parser")

        script, = [
            s for s in nowsoup.find_all("script") if "new soGroupTable" in s.text
        ]

        token, = re.search(r'const token = "(\w+)";', script.text).groups()
        table_config, = re.search(
            r"const table_config = (\[.*\]);", script.text
        ).groups()
        station_ids = set(dict(json.loads(table_config)).keys())

        log.info("get_site_timeseries", token=token, station_ids=station_ids)
        params = dict()
        params["token"] = token
        params["stid"] = ",".join(station_ids)
        params["source"] = "nwac"
        if start:
            params["start"] = self._fmt_time(start)
        if end:
            params["end"] = self._fmt_time(end)

        resp = await self._get(
            "https://api.snowobs.com/v1/station/timeseries?", params=params
        )

        log.info("get_site_timeseries complete", token=token, station_ids=station_ids)

        return json.loads(resp.text)

    @staticmethod
    def _floor_time(tm: datetime.datetime) -> datetime.datetime:
        return tm - datetime.timedelta(
            minutes=tm.minute, seconds=tm.second, microseconds=tm.microsecond
        )

    async def get_site_data(
        self,
        site_ids: Union[str, Iterable[str]],
        span: datetime.timedelta,
        time: datetime.datetime = None,
    ):
        if isinstance(site_ids, str):
            site_ids = [site_ids]
            _return = first
        else:
            _return = identity

        if time is None:
            time = datetime.datetime.utcnow()

        end = self._floor_time(time)
        start = self._floor_time(time) - span

        return _return(
            await asyncio.gather(
                *(self._get_site_data(s, start=start, end=end) for s in site_ids)
            )
        )
