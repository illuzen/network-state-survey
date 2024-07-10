from fastapi import APIRouter
from ape import accounts, project, networks
import logging
import os
from time import time
import pandas as pd
from api.models import SessionLocal, Task, Response, Question, Completion, Category, Cluster

db_session = SessionLocal()

# Configure the logging with time
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p')
logger = logging.getLogger(__name__)

stats_router = APIRouter(prefix='/stats')

infura_key = os.environ.get('INFURA_API_KEY')

network_provider = {
    'mumbai': 'https://polygon-mumbai.infura.io/v3/' + infura_key,
    'polygon': 'https://polygon-mainnet.infura.io/v3/' + infura_key
}

network = {
    'mumbai': networks.polygon.mumbai,
    'polygon': networks.polygon.mainnet
}

response_by_value = {
    -2: 'Strongly Disagree',
    -1: 'Disagree',
    1: 'Agree',
    2: 'Strongly Agree'
}

all_responses = {}


def collection_size(task: Task):
    with network[task.network].use_provider(network_provider[task.network]) as _:
        nft_contract = project.SBT.at(task.contract_address)
        return nft_contract.numIdentities(chain_id=network[task.network].chain_id)


@stats_router.get("/collection-size/{task_id}")
def get_collection_size(task_id: int):
    task = db_session.query(Task).filter_by(task_id=task_id).first()
    return collection_size(task)


@stats_router.get('/survey-stats/{task_id}')
def get_collection_stats(task_id: int):
    responses = get_all_responses(task_id)
    logger.info("responses: {}".format(responses))
    grouped = responses.groupby(['question', 'text']).size()
    d = {}
    for (question, answer), count in grouped.items():
        try:
            d[question][answer] = count
        except KeyError:
            d[question] = { answer: count }
    logger.info('survey-stats returning {}'.format(d))
    return d


@stats_router.get('/individual-responses/{task_id}/{username}')
def get_individual_responses(task_id: int, username: str):
    responses = get_all_responses(task_id)
    return responses[responses['username'] == username].to_dict('records')

# @stats_router.get('/user/{username}')
# def get_user(username: str):
#     responses = get_all_responses(task_id)
#     user_data = responses[['username', 'token_id', 'user_fid', 'cluster']].drop_duplicates(subset='username')
#     return user_data.to_dict('records')


@stats_router.get('/all-users/{task_id}')
def get_all_usernames(task_id: int):
    responses = get_all_responses(task_id)
    user_data = responses[['username', 'token_id', 'user_fid', 'cluster']].drop_duplicates(subset='username')
    user_data.fillna(0, inplace=True)
    logger.info('usernames: {}'.format(user_data))
    return user_data.to_dict('records')


@stats_router.get('/all-tasks')
def get_all_tasks():
    stmt = db_session.query(Task).statement
    df = pd.read_sql(stmt, db_session.bind)
    return df.to_dict('records')


@stats_router.get('/task/{task_id}')
def get_task(task_id: int):
    stmt = db_session.query(Task).filter_by(task_id=task_id).statement
    df = pd.read_sql(stmt, db_session.bind)
    return df.to_dict('records')


@stats_router.get('/all-clusters/{task_id}')
def get_all_clusters(task_id: int):
    stmt = db_session.query(Cluster).filter_by(task_id=task_id).statement
    df = pd.read_sql(stmt, db_session.bind)
    return df.to_dict('records')


def nested_dict_from_groupby(grouped):
    result_dict = {}
    for keys, value in grouped.items():
        current_level = result_dict
        # Iterate over the keys (except for the last one) to create the nested structure
        for key in keys[:-1]:
            if key not in current_level:
                current_level[key] = {}
            current_level = current_level[key]
        # Use the last key for the actual group data (you might want to customize this part)
        current_level[keys[-1]] = value
    return result_dict


@stats_router.get('/responses-by-cluster/{task_id}')
def get_responses_by_cluster(task_id: int):
    responses = get_all_responses(task_id)
    grouped = responses.groupby(['cluster', 'question', 'text']).size()
    reply = nested_dict_from_groupby(grouped)

    return reply


last_load_time = time()


def get_all_responses(task_id: int):
    global last_load_time
    if task_id not in all_responses or time() - last_load_time > 60:
        t0 = time()
        logger.info('Cache miss for responses for task {}'.format(task_id))
        stmt = db_session.query(Response).filter_by(task_id=task_id).statement
        df = pd.read_sql(stmt, db_session.bind)

        questions_by_id = {
            question.question_id: question.text
            for question in db_session.query(Question).filter_by(task_id=task_id).all()
        }
        df['question'] = df['question_id'].apply(lambda x: questions_by_id[x])

        cluster_by_user_fid = {
            completion.user_fid: {
                'cluster': completion.cluster.name,
                'token_id': completion.token_id
            }
            for completion in db_session.query(Completion).filter_by(task_id=task_id).all()
        }
        df['cluster'] = df['user_fid'].apply(lambda x: cluster_by_user_fid[x]['cluster'])
        df['token_id'] = df['user_fid'].apply(lambda x: cluster_by_user_fid[x]['token_id'])

        df['text'] = df['value'].apply(lambda x: response_by_value[x])

        all_responses[task_id] = df
        last_load_time = time()
        logger.info(f'Gathering responses for task_id {task_id} took {time() - t0:.2f} seconds')
    return all_responses[task_id]
