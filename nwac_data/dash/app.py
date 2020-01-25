# -*- coding: utf-8 -*-
import asyncio
import datetime
import pathlib
from typing import List
from urllib.parse import parse_qsl, urlencode, urlparse

import attr
import dash
import dash_core_components as dcc
import dash_html_components as html
import structlog
from dash.dependencies import Input, Output
from toolz import first

from nwac_data.data import parse_site_data
from nwac_data.fetch import DataClient
from nwac_data.plot import plot_station_data

log = structlog.get_logger()


async def get_site_list():
    async with DataClient() as data_client:
        return list(sorted(await data_client.get_site_list()))


assets_folder = str(pathlib.Path(__file__).parent / "assets")

log.info("setup", assets_folder=assets_folder)

app = dash.Dash(
    __name__,
    meta_tags=[{"name": "viewport", "content": "width=device-width"}],
    assets_folder=assets_folder,
)

app.config.suppress_callback_exceptions = True
app.scripts.config.serve_locally = False

app.layout = html.Div(
    [dcc.Location(id="url", refresh=False), html.Div(id="page-layout")]
)


@attr.s(auto_attribs=True)
class PageState:
    sites: List[str]

    def encode(self):
        return urlencode(dict(sites=",".join(self.sites)))

    @classmethod
    def from_url(cls, url):

        parse_result = urlparse(url)
        params = dict(parse_qsl(parse_result.query))

        if "sites" in params:
            params["sites"] = params["sites"].split(",")
        else:
            params["sites"] = []

        return cls(sites=params["sites"])


def build_layout(state: PageState):
    site_list = asyncio.run(get_site_list())

    app_title = "NWAC Weather Data"
    controls = [
        html.Div(
            className="padding-top-bot",
            children=[
                html.H6("Station Site"),
                dcc.Dropdown(
                    id="sites",
                    options=[dict(label=s, value=s) for s in site_list],
                    value=state.sites if state.sites else first(site_list),
                    multi=True,
                ),
            ],
        )
    ]

    content = [
        html.Div(
            className="bg-white",
            children=[
                dcc.Loading(
                    id="loading-plot", children=dcc.Graph(id="plot"), type="default"
                )
            ],
        )
    ]

    return html.Div(
        children=[
            # Location
            dcc.Location(id="app-location", refresh=False),
            # Error Message
            html.Div(id="error-message"),
            # Top Banner
            html.Div(
                className="app-banner row",
                children=[
                    html.H2(className="h2-title", children=app_title),
                    html.H2(className="h2-title-mobile", children=app_title),
                ],
            ),
            # Body of the App
            html.Div(
                className="row app-body",
                children=[
                    # User Controls
                    html.Div(
                        className="four columns card",
                        children=[
                            html.Div(
                                className="bg-white user-control", children=controls
                            )
                        ],
                    ),
                    # Content
                    html.Div(className="eight columns card-left", children=content),
                    dcc.Store(id="error", storage_type="memory"),
                ],
            ),
        ]
    )


@app.callback(Output("page-layout", "children"), inputs=[Input("url", "href")])
def page_load(href):
    if not href:
        return []

    state = PageState.from_url(href)
    return build_layout(state)


# Callback to generate study data
@app.callback(Output("plot", "figure"), [Input("sites", "value")])
def update_plot(sites):
    log.info("update_plot", site=sites)

    async def get_site_data():
        async with DataClient() as client:
            return await client.get_site_data(sites, datetime.timedelta(days=5))

    station_data = asyncio.run(get_site_data())
    station_data = parse_site_data(station_data)

    return plot_station_data(station_data)


@app.callback(Output("url", "search"), [Input("sites", "value")])
def update_url(sites):
    log.info("update_location", sites=sites)
    return "?" + PageState(sites).encode()


server = app.server
