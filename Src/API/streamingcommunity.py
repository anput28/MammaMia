import traceback

from bs4 import BeautifulSoup

from Src.Utilities import web
from Src.Utilities.convert import get_TMDb_id_from_IMDb_id
from Src.Utilities.info import get_info_tmdb, is_movie, get_info_imdb
import Src.Utilities.config as config
import json
import random
import re
from urllib.parse import urlparse, parse_qs
from fake_headers import Headers
from Src.Utilities.loadenv import load_env
import urllib.parse

env_vars = load_env()

SC_DOMAIN = config.SC_DOMAIN
Public_Instance = config.Public_Instance
Alternative_Link = env_vars.get('ALTERNATIVE_LINK')

headers = Headers()
request_manager = web.RequestManager(f'https://streamingcommunity.{SC_DOMAIN}')


async def get_version():
    try:
        api = f'https://streamingcommunity.{SC_DOMAIN}/richiedi-un-titolo'
        response = await request_manager.get(api, get_json=False)
        soup = BeautifulSoup(response, "lxml")

        version = json.loads(soup.find("div", {"id": "app"}).get("data-page"))['version']
        return version
    except Exception as e:
        print("Couldn't find the version", e)
        version = "65e52dcf34d64173542cd2dc6b8bb75b"
        return version


async def search(query, ismovie, client, SC_FAST_SEARCH, movie_id):
    response = await request_manager.get(query)
    print(response)

    for item in response['data']:
        tid = item['id']
        slug = item['slug']
        type = item['type']
        if type == "tv":
            type = 0
        elif type == "movie":
            type = 1
        if type == ismovie:
            if SC_FAST_SEARCH == "0":
                api = f'https://streamingcommunity.{SC_DOMAIN}/titles/{tid}-{slug}'
                response = await request_manager.get(api, get_json=False)
                soup = BeautifulSoup(response, "lxml")
                data = json.loads(soup.find("div", {"id": "app"}).get("data-page"))
                version = data['version']
                if "tt" in movie_id:
                    movie_id = str(await get_TMDb_id_from_IMDb_id(movie_id, client))
                tmdb_id = str(data['props']['title']['tmdb_id'])
                if tmdb_id == movie_id:
                    return tid, slug, version
            elif SC_FAST_SEARCH == "1":
                version = await get_version()
                return tid, slug, version
        else:
            print("Couldn't find anything")


async def get_film(tid, version):
    more_headers = {
        "x-inertia": "true",
        "x-inertia-version": version
    }

    api = f'https://streamingcommunity.{SC_DOMAIN}/iframe/{tid}'
    response = await request_manager.get(api, more_headers, get_json=False)

    iframe = BeautifulSoup(response, 'lxml')
    iframe = iframe.find('iframe').get("src")

    vixid = iframe.split("/embed/")[1].split("?")[0]

    response = await request_manager.get(iframe, more_headers, get_json=False)
    soup = BeautifulSoup(response, "lxml")
    script = soup.find("body").find("script").text
    token = re.search(r"'token':\s*'(\w+)'", script).group(1)
    expires = re.search(r"'expires':\s*'(\d+)'", script).group(1)
    quality = re.search(r'"quality":(\d+)', script).group(1)

    url = f'https://vixcloud.co/playlist/{vixid}.m3u8?token={token}&expires={expires}'

    parsed_url = urlparse(iframe)
    query_params = parse_qs(parsed_url.query)

    if 'canPlayFHD' in query_params:
        url += "&h=1"
    if 'b' in query_params:
        url += "&b=1"
    if quality == "1080":
        if "&h" in url:
            url = url
        elif "&b" in url and quality == "1080":
            url = url.replace("&b=1", "&h=1")
        elif quality == "1080" and "&b" and "&h" not in url:
            url = url + "&h=1"
    else:
        url = url + f"&token={token}"
    url720 = f'https://vixcloud.co/playlist/{vixid}.m3u8'
    return url, url720, quality


async def get_season_episode_id(tid, slug, season, episode, version):
    more_headers = {
        "x-inertia": "true",
        "x-inertia-version": version
    }

    api = f'https://streamingcommunity.{SC_DOMAIN}/titles/{tid}-{slug}/stagione-{season}'
    response = await request_manager.get(api, more_headers)
    json_response = response.get('props', {}).get('loadedSeason', {}).get('episodes', [])
    for dict_episode in json_response:
        if dict_episode['number'] == episode:
            return dict_episode['id']


async def get_episode_link(episode_id, tid, version):
    api = f"https://streamingcommunity.{SC_DOMAIN}/iframe/{tid}?episode_id={episode_id}&next_episode=1"
    response = await request_manager.get(api, get_json=False)

    soup = BeautifulSoup(response, "lxml")
    iframe = soup.find("iframe").get("src")
    vixid = iframe.split("/embed/")[1].split("?")[0]

    more_headers = {
        "x-inertia": "true",
        "x-inertia-version": version
    }

    response = await request_manager.get(iframe, more_headers, get_json=False)
    soup = BeautifulSoup(response, "lxml")
    script = soup.find("body").find("script").text
    token = re.search(r"'token':\s*'(\w+)'", script).group(1)
    expires = re.search(r"'expires':\s*'(\d+)'", script).group(1)
    quality = re.search(r'"quality":(\d+)', script).group(1)

    url = f'https://vixcloud.co/playlist/{vixid}.m3u8?token={token}&expires={expires}&referer=1'

    parsed_url = urlparse(iframe)
    query_params = parse_qs(parsed_url.query)
    if 'canPlayFHD' in query_params:
        url += "&h=1"
    if 'b' in query_params:
        url += "&b=1"
    if quality == "1080":
        if "&h" in url:
            url = url
        elif "&b" in url and quality == "1080":
            url = url.replace("&b=1", "&h=1")
        elif quality == "1080" and "&b" and "&h" not in url:
            url = url + "&h=1"
    else:
        url = url + f"&token={token}"
    url720 = f'https://vixcloud.co/playlist/{vixid}.m3u8'
    return url, url720, quality


async def streaming_community(imdb, client, SC_FAST_SEARCH):
    try:
        if Public_Instance == "1":
            weird_link = json.loads(Alternative_Link)
            link_post = random.choice(weird_link)
            response = await client.get(f"{link_post}fetch-data/{SC_FAST_SEARCH}/{SC_DOMAIN}/{imdb}")
            url_streaming_community = response.headers.get('x-url-streaming-community')
            url_720_streaming_community = response.headers.get('x-url-720-streaming-community')
            quality_sc = response.headers.get('x-quality-sc')
            print(quality_sc, url_streaming_community)
            return url_streaming_community, url_720_streaming_community, quality_sc
        general = is_movie(imdb)
        ismovie = general[0]
        imdb_id = general[1]

        show_name = None
        season = None
        episode = None
        tmdba = None

        if ismovie == 0:
            season = int(general[2])
            episode = int(general[3])
            if SC_FAST_SEARCH == "1":
                type = "StreamingCommunityFS"
                if "tt" in imdb:
                    show_name = await get_info_imdb(imdb_id, ismovie, type, client)
                else:
                    tmdba = imdb_id.replace("tmdb:", "")
                    show_name = get_info_tmdb(tmdba, ismovie, type)
            elif SC_FAST_SEARCH == "0":
                type = "StreamingCommunity"
                if "tt" in imdb:
                    tmdba = await get_TMDb_id_from_IMDb_id(imdb_id, client)
                else:
                    tmdba = imdb_id.replace("tmdb:", "")
                show_name, date = get_info_tmdb(tmdba, ismovie, type)
        else:
            if SC_FAST_SEARCH == "1":
                type = "StreamingCommunityFS"
                if "tt" in imdb:
                    show_name = await get_info_imdb(imdb_id, ismovie, type, client)
                else:
                    tmdba = imdb_id.replace("tmdb:", "")
                    show_name = get_info_tmdb(tmdba, ismovie, type)
            elif SC_FAST_SEARCH == "0":
                type = "StreamingCommunity"
                if "tt" in imdb:
                    show_name, date = await get_info_imdb(imdb_id, ismovie, type, client)
                else:
                    tmdba = imdb_id.replace("tmdb:", "")
                    show_name, date = get_info_tmdb(tmdba, ismovie, type)

        show_name = show_name.replace(" ", "+").replace("–", "+").replace("—", "+")
        show_name = urllib.parse.quote_plus(show_name)

        query = f'https://streamingcommunity.{SC_DOMAIN}/api/search?q={show_name}'
        tid, slug, version = await search(query, ismovie, client, SC_FAST_SEARCH, imdb_id)
        if ismovie == 1:
            url, url720, quality = await get_film(tid, version)
            print("MammaMia found results for StreamingCommunity")
            return url, url720, quality, slug
        if ismovie == 0:
            episode_id = await get_season_episode_id(tid, slug, season, episode, version)
            print(f"Episode id: {episode_id}")
            url, url720, quality = await get_episode_link(episode_id, tid, version)
            print("MammaMia found results for StreamingCommunity")
            return url, url720, quality, slug
    except Exception as e:
        print("MammaMia: StreamingCommunity failed", e, traceback.format_exc())
        return None, None, None, None
