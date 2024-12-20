import json

with open('config.json') as f:
    config = json.load(f)

SITE = config["Siti"]
FT_DOMAIN = SITE["Filmpertutti"]['domain']
SC_DOMAIN = SITE["StreamingCommunity"]['domain']
TF_DOMAIN = SITE["Tantifilm"]['domain']
LC_DOMAIN = SITE["LordChannel"]['domain']
SW_DOMAIN = SITE["StreamingWatch"]['domain']
AW_DOMAIN = SITE['AnimeWorld']['domain']
SKY_DOMAIN = SITE['SkyStreaming']['domain']
MYSTERIUS = SITE['Mysterius']['enabled']
DLHD = SITE['DaddyLiveHD']['enabled']

GENERAL = config['General']
dotenv = GENERAL["load_env"]
HOST = GENERAL["HOST"]
PORT = GENERAL["PORT"]
Public_Instance = GENERAL["Public_Instance"]
MediaProxy = GENERAL["MediaProxy"]
ForwardProxy = GENERAL["ForwardProxy"]
version = GENERAL["version"]
