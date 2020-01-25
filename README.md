# NWAC Data Dashboard

NWAC data dashboards, an experiment in dash-on-lambda.

Deployed at
[https://nwac-data.dev.asford.info](https://nwac-data.dev.asford.info).

## Setup

See [`asford/zappa-mvp`](https://github.com/asford/zappa-mvp) for deets.

1. `conda env create -p ./.conda` the host env.
2. `direnv allow` auto-activation of the host environment.
3. `pipenv install` the deployment env.
4. `pipenv run zappa deploy` to lambda.

## Lessons and Notes

Dash-on-Zappa is best with a [custom domain](https://romandc.com/zappa-django-guide/walk_domain/),
as Dash requires a [known pathname prefix](https://dash.plot.ly/integrating-dash).
Zappa's API gateway URLs include the stage name as a pathname prefix, but custom domain URLs do not.
With a custom domain the dash app will be properly configured out-of-the-box.
Without a custom domain, you must set the dash pathname prefix via the Zappa-provided
[STAGE env var](https://github.com/Miserlou/Zappa#setting-environment-variables).

Dash-on-Zappa is best with [CDN-hosted](https://dash.plot.ly/external-resources) dash components,
so that static files aren't served via concurrent lambda requests.
Serving static files from lambda may require concurrent lambda executions,
dramatically increasing cold-start time for infrequently accessed sites.
Set `app.scripts.config.serve_locally = False` so that component dependencies are served via CDN.
