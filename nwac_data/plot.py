from typing import Iterable

import colorlover
import pandas
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .data import StationData

_strftime_isoformat = "%Y-%m-%dT%H:%M:%S%z"


def _local_time(s: pandas.Series):
    return pandas.to_datetime(s).tz_convert("US/Pacific").strftime(_strftime_isoformat)


colorscale = colorlover.scales["9"]["qual"]["Set1"]


def _alpha(color, a):
    c, = colorlover.to_numeric([color])
    c = tuple(c)[:3] + (a,)
    return f"rgba({','.join(map(str, c))})"


def add_temp_trace(stations: Iterable[StationData], f: go.Figure, **f_kwargs):
    obs = None

    for i, s in enumerate(stations):
        color = colorscale[i]
        obs = s.obs

        if "air_temp" not in obs.columns:
            continue
        f.add_trace(
            go.Scatter(
                x=_local_time(obs.index),
                y=obs["air_temp"],
                name=f"{s.name} - {s.elevation}",
                mode="lines",
                line_color=color,
            ),
            **f_kwargs,
        )

    if obs is not None:
        f.add_shape(
            go.layout.Shape(
                type="line",
                x0=_local_time(obs.index).values[0],
                x1=_local_time(obs.index).values[-1],
                y0=32,
                y1=32,
                line=dict(dash="dot", width=1),
            ),
            **f_kwargs,
        )

    f.update_yaxes(
        patch=go.layout.YAxis(title="Temperature").to_plotly_json(), **f_kwargs
    )

    return f


def degree_to_dir(d):
    dirs = [
        "N",
        "NNE",
        "NE",
        "ENE",
        "E",
        "ESE",
        "SE",
        "SSE",
        "S",
        "SSW",
        "SW",
        "WSW",
        "W",
        "WNW",
        "NW",
        "NNW",
    ]
    ix = int(round(d / (360.0 / len(dirs))))
    return dirs[ix % len(dirs)]


def add_wind_trace(stations: StationData, f: go.Figure, **f_kwargs):
    for i, s in enumerate(stations):
        color = colorscale[i]
        obs = s.obs

        if "wind_speed" not in obs.columns:
            continue

        f.add_trace(
            go.Scatter(
                x=_local_time(obs.index),
                y=obs["wind_speed"],
                name=f"{s.name} - {s.elevation}",
                mode="lines",
                line_color=color,
            ),
            **f_kwargs,
        )

        if "wind_speed_min" in obs.columns and "wind_gust" in obs.columns:
            # Draw the gust and min traces without lines/legends, fill between
            f.add_trace(
                go.Scatter(
                    x=_local_time(obs.index),
                    y=obs["wind_gust"],
                    name=f"{s.name} - {s.elevation}",
                    mode="lines",
                    #        fill='tonexty',
                    showlegend=False,
                    line_color=_alpha(color, 0),
                    #        fillcolor=_alpha(color,.2)
                ),
                **f_kwargs,
            )

            f.add_trace(
                go.Scatter(
                    x=_local_time(obs.index),
                    y=obs["wind_speed_min"],
                    name=f"{s.name} - {s.elevation}",
                    mode="lines",
                    fill="tonexty",
                    showlegend=False,
                    line_color=_alpha(color, 0),
                    fillcolor=_alpha(color, 0.2),
                ),
                **f_kwargs,
            )

        if "wind_direction" in obs.columns:
            f.add_trace(
                go.Scatter(
                    x=_local_time(obs.index),
                    y=obs["wind_direction"],
                    text=list(map(degree_to_dir, obs["wind_direction"].values)),
                    name=f"{s.name} - {s.elevation}",
                    mode="markers",
                    showlegend=False,
                    fillcolor=_alpha(color, 0.5),
                    line_color=_alpha(color, 0.8),
                ),
                secondary_y=True,
                **f_kwargs,
            )

    f.update_yaxes(
        patch=go.layout.YAxis(title="Wind Speed"), secondary_y=False, **f_kwargs
    )

    f.update_yaxes(
        patch=go.layout.YAxis(
            title="Wind Direction",
            fixedrange=True,
            range=(0, 360),
            showgrid=False,
            tickmode="array",
            tickvals=list(range(0, 360 + 1, 45)),
            ticktext=list(map(degree_to_dir, range(0, 360 + 1, 45))),
        ),
        secondary_y=True,
        **f_kwargs,
    )

    return f


def add_precip_trace(stations: StationData, f: go.Figure, **f_kwargs):
    for i, s in enumerate(stations):
        color = colorscale[i]
        obs = s.obs

        if "precip_accum_one_hour" in obs.columns:
            f.add_trace(
                go.Bar(
                    x=_local_time(obs.index),
                    y=obs["precip_accum_one_hour"],
                    name=f"{s.name} - {s.elevation}",
                    marker_color=_alpha(color, 0.5),
                ),
                secondary_y=True,
                **f_kwargs,
            )

        if "snow_depth_24h" in obs.columns:
            f.add_trace(
                go.Scatter(
                    x=_local_time(obs.index),
                    y=obs["snow_depth_24h"],
                    name=f"{s.name} - {s.elevation}",
                    mode="lines",
                    line_color=color,
                ),
                secondary_y=False,
                **f_kwargs,
            )

    f.update_xaxes(patch=go.layout.XAxis(showgrid=True), **f_kwargs)

    f.update_yaxes(
        patch=go.layout.YAxis(
            title="Precip (inch/hr)", showgrid=False, range=(0, 0.25)
        ),
        secondary_y=True,
        **f_kwargs,
    )

    f.update_yaxes(
        patch=go.layout.YAxis(title="Snow Depth (24h)", range=(0, None)),
        secondary_y=False,
        **f_kwargs,
    )

    return f


def add_snow_trace(stations: StationData, f: go.Figure, **f_kwargs):
    for i, s in enumerate(stations):
        color = colorscale[i]
        obs = s.obs

        if "snow_depth" in obs.columns:
            f.add_trace(
                go.Scatter(
                    x=_local_time(obs.index),
                    y=obs["snow_depth"],
                    name=f"{s.name} - {s.elevation}",
                    mode="lines",
                    line_color=color,
                ),
                secondary_y=False,
                **f_kwargs,
            )

    f.update_yaxes(
        patch=go.layout.YAxis(title="Snow Depth", range=(0, None)),
        secondary_y=False,
        **f_kwargs,
    )

    return f


def plot_station_data(stations):
    fig = make_subplots(
        shared_xaxes=True,
        rows=4,
        cols=1,
        vertical_spacing=0.05,
        specs=[[{"secondary_y": True}]] * 4,
    )

    add_temp_trace(stations, fig, row=1, col=1)
    add_precip_trace(stations, fig, row=2, col=1)
    add_wind_trace(stations, fig, row=3, col=1)
    add_snow_trace(stations, fig, row=4, col=1)

    has_legend = set()

    for t in fig.select_traces():
        if t.showlegend is not False:
            if t.name in has_legend:
                t.showlegend = False
            else:
                t.showlegend = True
                has_legend.add(t.name)

    fig.update_layout(hovermode="x")
    fig.update_layout(showlegend=True, legend_orientation="h", legend_y=-0.15)
    fig.update_xaxes(patch=go.layout.XAxis(tickformat="%H:%M %a %b %d").to_plotly_json())

    fig.update_layout(
        height=700,
        autosize=True,
        margin=go.layout.Margin(l=12, r=12, b=12, t=12, pad=4),
    )
    return fig
