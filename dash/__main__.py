from nwac_data.dash.app import app

server = app.server

if __name__ == "__main__":
    app.run_server(debug=True)
