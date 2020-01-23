import datetime
import json
import re
from typing import Any, Dict, Optional, Set

import httpx
import structlog
from bs4 import BeautifulSoup

log = structlog.get_logger()


async def _get(url, client=None, **kwargs) -> httpx.Response:
    log.debug("_get", url=url, **kwargs)
    if client is None:
        async with httpx.AsyncClient() as client:
            return await client.get(url, **kwargs)
    else:
        return await client.get(url, **kwargs)


async def get_snodata_token(client: httpx.AsyncClient = None) -> str:

    resp = await _get("https://www.nwac.us/weatherdata/alpental/now", client=client)
    resp.raise_for_status()
    token, = re.search(r'const token = "(\w+)"', resp.text).groups()

    log.info("get_snodata_token", token=token)
    return token


async def get_snodata_stations(
    token: str, client: httpx.AsyncClient = None
) -> Dict[str, str]:
    url = (
        f"https://api.snowobs.com/v1/station/current"
        f"?token={token}&units=english&qc=true&source=nwac"
    )

    station_data = json.loads(_get(url, client=client).text)

    return {s["NAME"]: s["STID"] for s in station_data["station_current"]["STATION"]}


async def get_site_list(client: httpx.AsyncClient = None) -> Set[str]:

    resp = await _get("https://www.nwac.us/weatherdata/", client=client)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, features="html.parser")

    return {
        l.find("a", class_="station-link")
        .attrs["href"]
        .split("/")[2]: l.text.split("\n")[1]
        .strip()
        for l in soup.find_all("li", class_="station-title-cell")
    }


def _fmt_time(dt: Optional[datetime.datetime]) -> Optional[str]:
    if dt is not None:
        return dt.strftime("%Y%m%d%H%M")
    else:
        return None


async def get_site_data(
    site_id: str,
    start: datetime.datetime = None,
    end: datetime.datetime = None,
    client: httpx.AsyncClient = None,
) -> Any:
    log.info("get_site_data", site_id=site_id, start=start, end=end)
    resp = await _get(f"https://www.nwac.us/weatherdata/{site_id}/now", client=client)
    resp.raise_for_status()
    nowsoup = BeautifulSoup(resp.text, features="html.parser")

    script, = [s for s in nowsoup.find_all("script") if "new soGroupTable" in s.text]

    token, = re.search(r'const token = "(\w+)";', script.text).groups()
    table_config, = re.search(r"const table_config = (\[.*\]);", script.text).groups()
    station_ids = set(dict(json.loads(table_config)).keys())

    log.info("get_site_timeseries", token=token, station_ids=station_ids)
    params = dict()
    params["token"] = token
    params["stid"] = ",".join(station_ids)
    params["source"] = "nwac"
    if start:
        params["start"] = _fmt_time(start)
    if end:
        params["end"] = _fmt_time(end)

    resp = await _get(
        "https://api.snowobs.com/v1/station/timeseries?", params=params, client=client
    )

    log.info("get_site_timeseries complete", token=token, station_ids=station_ids)

    return json.loads(resp.text)
