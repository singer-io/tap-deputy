from datetime import timedelta
import json
from singer import metrics, get_logger
from singer.utils import strptime_to_utc, now, strftime
from requests.exceptions import ConnectionError
import backoff
import requests


LOGGER = get_logger()


class Server5xxError(Exception):
    pass


class DeputyClient():
    def __init__(self, config, config_path, dev_mode):
        self.__config_path = config_path
        self.__config = config
        self.__user_agent = config.get('user_agent')
        self.__domain = config.get('domain')
        self.__client_id = config.get('client_id')
        self.__client_secret = config.get('client_secret')
        self.__redirect_uri = config.get('redirect_uri')
        self.__refresh_token = config.get('refresh_token')
        self.__access_token = config.get('access_token')
        self.__session = requests.Session()
        self.__dev_mode = dev_mode
        self.__expires_at = strptime_to_utc(config.get('expires_at')) \
            if config.get("expires_at") else None

    @property
    def config(self):
        return self.__config

    @property
    def refresh_token(self):
        return self.__refresh_token

    @property
    def access_token(self):
        return self.__access_token

    @property
    def expires_at(self):
        return self.__expires_at

    def __enter__(self):
        return self

    def __exit__(self, _type, value, traceback):
        self.__session.close()

    def refresh(self):
        """
        Checks token expiry and refresh token when it is expired and dev mode is not enabled
        """
        if self.__dev_mode:
            if not self.__access_token:
                raise Exception("Access token config property is missing")

            if not self.__expires_at:
                raise Exception(
                    "Expiry of access token config property is missing")

            if self.__expires_at < now():
                raise Exception(
                    "Access Token in config is expired, unable to authenticate in dev mode")

            return

        if self.__access_token and self.__expires_at > now():
            return

        data = self.post(
            '/oauth/access_token',
            auth_call=True,
            data={
                'client_id': self.__client_id,
                'client_secret': self.__client_secret,
                'redirect_uri': self.__redirect_uri,
                'refresh_token': self.__refresh_token,
                'grant_type': 'refresh_token',
                'scope': 'longlife_refresh_token'
            })

        self.__refresh_token = data['refresh_token']
        self.__access_token = data['access_token']
        # pad by 10 seconds for clock drift
        self.__expires_at = now() + timedelta(seconds=data['expires_in'] - 10)

        if not self.__dev_mode:
            self.__config['refresh_token'] = self.__refresh_token
            self.__config['access_token'] = self.__access_token
            self.__config['expires_at'] = strftime(self.__expires_at)

            with open(self.__config_path, 'w') as tap_config:
                json.dump(self.__config, tap_config, indent=2)

    @backoff.on_exception(backoff.expo,
                          (Server5xxError, ConnectionError),
                          max_tries=5,
                          factor=2)
    def request(self, method, path=None, url=None, auth_call=False, **kwargs):
        if auth_call is False and \
            (self.__access_token is None or
             self.__expires_at <= now()):
            self.refresh()

        if url is None and path:
            url = 'https://{}{}'.format(self.__domain, path)

        if 'endpoint' in kwargs:
            endpoint = kwargs['endpoint']
            del kwargs['endpoint']
        else:
            endpoint = None

        if 'headers' not in kwargs:
            kwargs['headers'] = {}

        kwargs['headers']['Authorization'] = 'OAuth {}'.format(
            self.__access_token)

        if self.__user_agent:
            kwargs['headers']['User-Agent'] = self.__user_agent

        with metrics.http_request_timer(endpoint) as timer:
            response = self.__session.request(method, url, **kwargs)
            timer.tags[metrics.Tag.http_status_code] = response.status_code

        if response.status_code >= 500:
            raise Server5xxError()

        response.raise_for_status()

        return response.json()

    def get(self, path, **kwargs):
        return self.request('GET', path=path, **kwargs)

    def post(self, path, **kwargs):
        return self.request('POST', path=path, **kwargs)
