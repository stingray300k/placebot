import sys
from enum import Enum
import time
import json

import requests
from bs4 import BeautifulSoup

SET_PIXEL_QUERY = \
    """mutation setPixel($input: ActInput!) {
      act(input: $input) {
        data {
          ... on BasicMessage {
            id
            data {
              ... on GetUserCooldownResponseMessageData {
                nextAvailablePixelTimestamp
                __typename
              }
              ... on SetPixelResponseMessageData {
                timestamp
                __typename
              }
              __typename
            }
            __typename
          }
          __typename
        }
        __typename
      }
    }
    """


class Color(Enum):
    BLACK = 27
    WHITE = 31


class Placer:
    REDDIT_URL = "https://www.reddit.com"
    LOGIN_URL = REDDIT_URL + "/login"
    INITIAL_HEADERS = {
        "accept": "*/*",
        "accept-encoding": "gzip, deflate, br",
        "accept-language": "en-US,en;q=0.9",
        "content-type": "application/x-www-form-urlencoded",
        "origin": REDDIT_URL,
        "sec-ch-ua": '" Not A;Brand";v="99", "Chromium";v="100", "Google Chrome";v="100"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "sec-fetch-dest": "empty",
        "sec-fetch-mode": "cors",
        "sec-fetch-site": "same-origin",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/100.0.4896.60 Safari/537.36"
    }

    def __init__(self):
        self.client = requests.session()
        self.client.headers.update(self.INITIAL_HEADERS)

        self.token = None
        self.logged_in = False

    def login(self, username: str, password: str):
        # get the csrf token
        print("Obtaining CSRF token...")
        r = self.client.get(self.LOGIN_URL)
        time.sleep(1)

        login_get_soup = BeautifulSoup(r.content, "html.parser")
        csrf_token = login_get_soup.find("input", {"name": "csrf_token"})["value"]

        # authenticate
        print("Logging in...")
        r = self.client.post(
            self.LOGIN_URL,
            data={
                "username": username,
                "password": password,
                "dest": self.REDDIT_URL,
                "csrf_token": csrf_token
            }
        )
        time.sleep(1)

        if r.status_code != 200:
            print("Login failed!")
            return
        else:
            print("Login successful!")

        # get the new access token
        print("Obtaining access token...")
        r = self.client.get(self.REDDIT_URL)
        data_str = BeautifulSoup(r.content, features="html.parser").find("script", {"id": "data"}).contents[0][len("window.__r = "):-1]
        data = json.loads(data_str)
        self.token = data["user"]["session"]["accessToken"]

        print("Logged in as " + username)
        self.logged_in = True

    def place_tile(self, x: int, y: int, color: Color):
        headers = self.INITIAL_HEADERS.copy()
        headers.update({
            "apollographql-client-name": "mona-lisa",
            "apollographql-client-version": "0.0.1",
            "content-type": "application/json",
            "origin": "https://hot-potato.reddit.com",
            "referer": "https://hot-potato.reddit.com/",
            "sec-fetch-site": "same-site",
            "authorization": "Bearer " + self.token
        })

        print("Placing tile at " + str(x) + ", " + str(y) + " with color " + str(color))
        r = requests.post(
            "https://gql-realtime-2.reddit.com/query",
            json={
                "operationName": "setPixel",
                "query": SET_PIXEL_QUERY,
                "variables": {
                    "input": {
                        "PixelMessageData": {
                            "canvasIndex": 0,
                            "colorIndex": color.value,
                            "coordinate": {
                                "x": x,
                                "y": y
                            }
                        },
                        "actionName": "r/replace:set_pixel"
                    }
                }
            },
            headers=headers
        )

        if r.status_code != 200:
            print("Error placing tile")
            print(r.content)
        else:
            print("Placed tile")