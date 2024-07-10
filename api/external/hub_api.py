import requests
import logging
import os
from time import time

# Configure the logging with time
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p')

# Create a logger object
logger = logging.getLogger(__name__)

tasks = {}
secret_key = 'done!'
api_key = os.environ.get('NEYNAR_API_KEY')

def get_headers():
    return {
        "accept": "application/json",
        "api_key": api_key,
        "content-type": "application/json"
    }


def validate_message(messageBytes):
    url = "https://api.neynar.com/v2/farcaster/frame/validate"
    payload = {
        "cast_reaction_context": False,
        "follow_context": True,
        'message_bytes_in_hex': messageBytes
    }
    t0 = time()
    response = requests.post(url, json=payload, headers=get_headers())
    logger.info(f'Request to farcaster hub took {time() - t0:.2f} seconds')
    if response.ok:
        j = response.json()
        if j['valid']:
            logger.info('Decoded message: {}'.format(j))
            return j
    else:
        logger.error('message not ok {}'.format(response))
    return None


def get_user(addr):
    addr = addr.lower()
    url = 'https://api.neynar.com/v2/farcaster/user/bulk-by-address?addresses={}'.format(addr)
    response = requests.get(url, headers=get_headers())
    if response.ok:
        logger.info('ok')
        users = response.json()[addr]
        if len(users) > 1:
            logger.warning('multiple users for address {}'.format(addr))
        elif len(users) == 0:
            logger.error('no users found') # should not happen, should get bad response instead
        else:
            # 1 user exactly
            user = users[0]
            return user
    else:
        logger.error('not ok')
    return None


def get_recent_casts(fid):
    url = 'https://api.neynar.com/v1/farcaster/casts?fid=3&viewerFid={}&limit=25'.format(fid)
    response = requests.get(url, headers=get_headers())
    if response.ok:
        logger.info('ok')
        casts = response.json()['result']['casts']
        return casts
    else:
        logger.error('not ok')
    return None


def find_earn(casts):
    earns = [
        cast
        for cast in casts
        if secret_key in cast['text']
    ]
    if len(earns) == 0:
        logger.error('no earns found')
    elif len(earns) > 1:
        logger.error('multiple earns found')
    else:
        logger.info('earn found!')
        earn = earns[0]
        logger.info(earn)
        return earn


def get_replies(cast_hash, thread_hash, fid):
    url = 'https://api.neynar.com/v1/farcaster/all-casts-in-thread?threadHash={}&viewerFid={}'.format(thread_hash, fid)
    response = requests.get(url, headers=get_headers())
    if response.ok:
        logger.info('ok')
        replies = [
            cast
            for cast in response.json()['result']['casts']
            if cast['parentHash'] == cast_hash
        ]
        return replies
    else:
        logger.error('not ok')
    return None

# user_addr = '0x0916C04994849c676ab2667Ce5bbDF7CcC94310a'

# user = get_user(user_addr)
# casts = get_recent_casts(user['fid'])
# earn = find_earn(casts)
# replies = get_replies(cast_hash=earn['hash'], thread_hash=earn['threadHash'], fid=user['fid'])
# logger.info('Recieved {} replies to earn cast'.format(len(replies)))

