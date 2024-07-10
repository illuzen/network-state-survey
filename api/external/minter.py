from celery import Celery
from ape import accounts, project, networks
from celery.signals import worker_init
import logging
import os
import pwd
import json
from .ipfs import pin_text
from api.models import SessionLocal, Completion

db_session = SessionLocal()

# Get the current process's user ID
uid = os.getuid()

infura_key = os.environ.get('INFURA_API_KEY')

# Get the user name from the user ID
user_name = pwd.getpwuid(uid).pw_name

# Configure the logging with time
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p')
logger = logging.getLogger(__name__)

logger.info(f"The process is running as: {user_name}")

app = Celery('minter', broker='pyamqp://guest@localhost//')

account = None

network_provider = {
    'mumbai': 'https://polygon-mumbai.infura.io/v3/' + infura_key,
    'polygon': 'https://polygon-mainnet.infura.io/v3/' + infura_key
}


@worker_init.connect
def on_worker_init(**kwargs):
    global account
    account = accounts.load('dev')
    account.set_autosign(True)


@app.task
def health_check():
    logger.info('health_check ok')
    return 'ok'


@app.task
def mint_to(completion_id, metadata, recipient_address, token_id):
    network = {
        'mumbai': networks.polygon.mumbai,
        'polygon': networks.polygon.mainnet
    }

    completion = db_session.query(Completion).filter_by(completion_id=completion_id).first()
    logger.info('Minting {} nft to {}, minter: {}'.format(completion.cluster.name, recipient_address, account))

    with network[completion.task.network].use_provider(network_provider[completion.task.network]) as _:
        tries = 0
        success = False
        while tries < 3:
            try:
                filename = '{}-{}.json'.format(recipient_address, completion.cluster.name)
                hash = pin_text(filename, json.dumps(metadata))

                nft_contract = project.SBT.at(completion.task.contract_address)
                receipt = nft_contract.mint(recipient_address, 'ipfs://{}'.format(hash), sender=account)
                if not receipt.failed:
                    success = True
                    completion.token_id = token_id
                    db_session.commit()
                    break
            except Exception as e:
                logger.error('Transaction failed: {}'.format(e))

            tries += 1

    if not success:
        logger.error('Transaction failed too many times. Not retrying')

    with open('./results.tsv', 'a') as f:
        result = '{}\t{}\t{}\t{}\t{}\n'.format(hash, recipient_address, completion.token_id, completion.user_fid, success)
        logger.info('Writing to results: {}'.format(result))
        f.write(result)

