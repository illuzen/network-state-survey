import requests
import logging
import os

pinata_api_key = os.environ.get('PINATA_API_KEY')
pinata_api_secret = os.environ.get('PINATA_API_SECRET')
pinata_jwt = os.environ.get('PINATA_JWT')

# Configure the logging with time
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p')
logger = logging.getLogger(__name__)


def get_headers():
    return {
        'Authorization': 'Bearer {}'.format(pinata_jwt)
        # "Content-Type": "multipart/form-data"
    }


def pin_img(path):
    image = open(path, 'rb')
    filename = path.split('/')[-1]
    files = {
        'file': (filename, image)
    }
    response = requests.post('https://api.pinata.cloud/pinning/pinFileToIPFS', files=files, headers=get_headers())
    j = response.json()
    if response.ok:
        logger.info('Successfully pinned: {}'.format(j))
    else:
        logger.error('Could not pin {}: {}'.format(filename, j))
    return j['IpfsHash']


def pin_text(filename, text):
    logger.info('Pinning {}:{} to ipfs'.format(filename, text))
    files = {
        'file': (filename, text, 'text/plain')
    }
    response = requests.post('https://api.pinata.cloud/pinning/pinFileToIPFS', files=files, headers=get_headers())
    j = response.json()
    if response.ok:
        logger.info('Successfully pinned: {}'.format(j))
    else:
        logger.error('Could not pin {}: {}'.format(filename, j))
    return j['IpfsHash']

# pin_img('img/questions/0.png')
