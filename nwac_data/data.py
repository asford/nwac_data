from typing import Any, Tuple, Union, Dict, Iterable

import attr
import pandas


@attr.s(auto_attribs=True)
class StationData:
    name: str
    elevation: int
    obs: pandas.DataFrame


def parse_station_data(station_data: Any) -> StationData:
    elevation = int(station_data["ELEVATION"])
    name = station_data["NAME"]
    obs = pandas.DataFrame(station_data["OBSERVATIONS"])
    if len(obs):
        obs = obs.set_index("date_time")
    return StationData(elevation=elevation, name=name, obs=obs)


def parse_site_data(site_data: Union[Dict, Iterable[Dict]]) -> Tuple[StationData]:
    if isinstance(site_data, dict):
        site_data = [site_data]

    return tuple(
        parse_station_data(s)
        for site in site_data
        for s in site["station_timeseries"].get("STATION", [])
    )
