from fastapi import Request, APIRouter
from pydantic import BaseModel
from fastapi.templating import Jinja2Templates
from api.external.hub_api import validate_message
from api.external.minter import health_check, mint_to
from api.routes.stats import collection_size
from api.models import SessionLocal, Question, Response, Completion, Cluster, Task
from typing import Optional
from api.scoring import get_quiz_result
import json
import logging

# Configure the logging with time
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p')

# Create a logger object
logger = logging.getLogger(__name__)

db_session = SessionLocal()

frames_router = APIRouter()

templates = Jinja2Templates(directory="api/routes/templates")


class TrustedData(BaseModel):
    messageBytes: str


class FrameSignature(BaseModel):
    trustedData: TrustedData


url_stem = 'https://earthnetcdn.com'

nft_url = {
    'mumbai': 'https://testnets.opensea.io/assets/mumbai/0x5A05289A5Ffbfa6a45663D092A0fE7C1Bc0c5bc9',
    'polygon': 'https://opensea.io/collection/the-network-state-survey'
}

button_scores = [2, 1, -1, -2]
button_titles = json.load(open('./json/button_titles.json', 'r'))

no_duplicates = json.load(open('./json/no_duplicates.json', 'r'))
no_such_survey = json.load(open('./json/no_such_survey.json', 'r'))
start_image = json.load(open('./json/start.json', 'r'))
final_image = json.load(open('./json/final.json', 'r'))
start_url = 'https://gateway.pinata.cloud/ipfs/{}'.format(start_image['ipfs'])
final_url = 'https://gateway.pinata.cloud/ipfs/{}'.format(final_image['ipfs'])

result_images = {
    'success': 'https://i.imgur.com/DqqXVAI.png',
    'no_address': 'https://i.imgur.com/RLQPXFb.png',
    'already_completed': 'https://gateway.pinata.cloud/ipfs/{}'.format(no_duplicates['ipfs']),
    'no_such_survey': 'https://gateway.pinata.cloud/ipfs/{}'.format(no_such_survey['ipfs'])
    # 'invalid_text_input': 'https://i.imgur.com/NxUVXI6.png',
    # 'invalid_message': 'https://i.imgur.com/1m7xHMM.png',
    # 'mint_failed': 'https://i.imgur.com/XASsSBv.png',
    # 'unknown_error': 'https://i.imgur.com/8Q3KAxj.png'
}


@frames_router.get("/")
async def read_item(request: Request):
    health_check.delay()

    return templates.TemplateResponse("result.html", {'request': request, 'result_image': result_images['success']})


@frames_router.get("/already-completed")
async def already_completed(request: Request):
    return templates.TemplateResponse("result.html",
                                      {'request': request, 'result_image': result_images['already_completed']})


@frames_router.get("/task/{task_id}")
def get_task(request: Request, task_id: int):
    return show_task(request, task_id, 0)


@frames_router.post("/task/{task_id}/{page_num}")
def show_task(request: Request, task_id: int, page_num: int, frame_signature: Optional[FrameSignature] = None):
    task = db_session.query(Task).filter_by(task_id=task_id).first()

    if task is None:
        return templates.TemplateResponse("result.html",
                                          {'request': request, 'result_image': result_images['no_such_survey']})

    if page_num == 0:
        response = {
            'request': request,
            'task_id': task_id,
            'image_tags': get_image_tags(start_url)
        }
        return templates.TemplateResponse("start.html", response)

    question = get_question(task_id, page_num)

    if frame_signature is not None:
        message = validate_message(frame_signature.trustedData.messageBytes)
        username = message['action']['interactor']['username']
        button_index = message['action']['tapped_button']['index']
        user_fid = message['action']['interactor']['fid']

        already_completed = db_session.query(Completion).filter_by(user_fid=user_fid, task_id=task_id).first()
        if already_completed is not None and user_fid != 336572:
            logger.warning('User {} already completed task {}'.format(username, task_id))
            return templates.TemplateResponse("result.html",
                                              {'request': request, 'result_image': result_images['already_completed']})

        if page_num < len(questions.get(task_id, [])):
            existing = db_session.query(Response).filter_by(user_fid=user_fid, question_id=question.question_id).first()
            if existing and user_fid != 336572:
                existing.value = button_scores[button_index - 1]
                logger.info('Replacing response for user {} = {}'.format(username, existing))
            else:
                response = Response(
                    question_id=question.question_id,
                    task_id=task_id,
                    user_fid=user_fid,
                    username=username,
                    value=button_scores[button_index - 1])
                db_session.add(response)
                logger.info('Adding response for user {} = {}'.format(username, response))

            db_session.commit()
        else:
            # final stage: mint
            # recipients = message['action']['interactor']['verifications']
            recipients = message['action']['interactor']['verified_addresses']['eth_addresses']
            if len(recipients) == 0:
                logger.error('No address to mint to. Aborting')
                return templates.TemplateResponse("result.html",
                                                  {'request': request, 'result_image': result_images['no_address']})

            recipient = recipients[0]
            all_answers = db_session.query(Response).filter_by(task_id=task_id, username=username)

            result = get_quiz_result(all_answers)

            cluster = db_session.query(Cluster).filter_by(task_id=task_id, name=result['name']).first()

            token_id = collection_size(task) + 1

            completion = Completion(task_id=task_id, user_fid=user_fid, cluster_id=cluster.cluster_id)
            db_session.add(completion)
            db_session.commit()

            metadata = ipfs_metadata(all_answers, cluster, token_id)

            mint_to.delay(completion.completion_id, metadata, recipient, token_id)

            return templates.TemplateResponse("end.html",
                                              {'request': request, 'result_image': final_url, 'nft_url': '{}/{}'.format(nft_url[task.network], token_id)})
    response = {
        'request': request,
        'meta_tags': '{}{}'.format(get_image_tags('https://gateway.pinata.cloud/ipfs/{}'.format(question.image_ipfs_hash)),
                                   get_button_tags(task_id, page_num + 1))
    }

    # logger.info(response)
    return templates.TemplateResponse('task_page.html', response)


def get_image_tags(url):
    return '''
        <meta property="og:title" content="The Network State Survey"/>
        <meta property="og:image" content="{}">
        <meta property="fc:frame" content="vNext"/>
        <meta property="fc:frame:image" content="{}">
        <meta property="fc:frame:image:aspect_ratio" content="1.91:1"/>
    '''.format(url, url)


def get_button_tags(task_id: int, page_num: int):
    tags = [
        '''
            <meta property="fc:frame:button:{}" content="{}">
            <meta property="fc:frame:button:{}:action" content="post">
        '''.format(index + 1, title, index + 1)
        for index, title in enumerate(button_titles)
    ]

    return ''.join(tags) + '<meta property="fc:frame:post_url" content="{}/task/{}/{}">'.format(url_stem, task_id,
                                                                                                page_num)

questions = {} # { task_id: [questions] }


def get(lst, index, default=None):
    return lst[index] if 0 <= index < len(lst) else default


def get_question(task_id: int, page_num: int):
    if task_id not in questions:
        questions[task_id] = db_session.query(Question).filter_by(task_id=task_id).all()
        logger.info('Cache miss for question {} from task {}, received from db {}'.format(page_num, task_id, questions[task_id]))
    else:
        logger.info('Cache hit for question {} from task {}: {}'.format(page_num, task_id, questions[task_id]))
    return get(questions[task_id], page_num, None)


def ipfs_metadata(answers, cluster, token_id):
    username = answers[0].username

    metadata = {
        'name': cluster.name,
        'image': 'ipfs://{}'.format(cluster.image_ipfs_hash),
        'token_id': token_id,
        'username': username,
        'survey': answers[0].task.title,
        'attributes': [
            map_step_to_attribute(answer)
            for answer in answers
        ],
        # 'external_uri': ''
    }

    logger.info('Constructed metadata: {}'.format(metadata))
    return metadata


agreement = {
    -2: 'Strongly Disagree',
    -1: 'Disagree',
    1: 'Agree',
    2: 'Strongly Agree'
}

def map_step_to_attribute(response):
    return {
        'trait_type': response.question.text,
        'value': agreement[response.value]
    }

