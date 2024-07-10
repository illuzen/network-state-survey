from PIL import Image, ImageDraw, ImageFont
import json
import textwrap
from external.ipfs import pin_img
from external.hub_api import logger
import random
from models import SessionLocal, Question
import os

session = SessionLocal()

def text_to_png(text, filename):
    # Create an image with white background
    height = 400
    # width = int(height * 1.19)
    width = height
    font_size = 40
    color = (0, 0, 0)
    image = Image.open('./img/frame3.png')
    # image = Image.new('RGB', (width, height), color='white')
    draw = ImageDraw.Draw(image)

    # Load the specified font
    font = ImageFont.truetype("./font/Cinzel-Regular.ttf", font_size)

    # Calculate text size and position
    # text_width, text_height = draw.text(text, font=font)
    # x = (width - text_width) / 2
    # y = (height - text_height) / 2

    lines = textwrap.wrap(text, width=24)
    for i, line in enumerate(lines):
        # Draw the text on the image
        x = 4.5 * width / 10
        y = (i + 1) * (height / 12) + (height * 0.8)
        draw.text((x, y), line, fill=color, font=font, align='center')

    # Save the image
    image.save(filename)


def add_images_to_quiz():
    with open('./json/quiz.json', 'r') as f:
        j = json.load(f)
        for i, obj in enumerate(j):
            filename = './img/questions/{}.png'.format(i)
            text_to_png(obj['question'], filename)
            obj['img'] = filename

    with open('./json/quiz.json', 'w') as f:
        json.dump(fp=f, obj=j, indent=4)


def add_images_to_task(task_id):
    questions = session.query(Question).filter_by(task_id=task_id).all()
    dir = './img/questions/task_{}'.format(task_id)

    if not os.path.exists(dir):
        logger.info('Creating directory: {}'.format(dir))
        os.makedirs(dir, exist_ok=True)

    for i, question in enumerate(questions):
        filename = '{}/{}.png'.format(dir, question.question_id)
        text_to_png(question.text, filename)
        question.image_path = filename
        ipfs_hash = pin_img(filename)
        question.image_ipfs_hash = ipfs_hash
        session.add(question)
        logger.info('Created image for question {}: {} - {}'.format(question.question_id, question.text, question.image_ipfs_hash))


    session.commit()


def add_images_to_ipfs():
    with open('./json/quiz.json', 'r') as f:
        j = json.load(f)
        for i, obj in enumerate(j):
            hash = pin_img(obj['img'])
            obj['ipfs'] = hash

    with open('./json/quiz.json', 'w') as f:
        json.dump(fp=f, obj=j, indent=4)


def shuffle_questions():
    with open('./json/quiz.json', 'r') as f:
        j = json.load(f)
        random.shuffle(j)

    with open('./json/quiz.json', 'w') as f:
        json.dump(fp=f, obj=j, indent=4)


def make_start_img():
    make_img('Welcome to the Network State Survey! Please fill out to get your NFT', 'start.json')

def make_final_img():
    make_img('Your NFT is on its way! Please check the link below after 10 seconds', 'final.json')


def make_img(text, dest):
    if '/' in dest:
        logger.error('Bad destination')
        return
    filename = './img/questions/success.png'
    text_to_png(text, filename)
    hash = pin_img(filename)
    j = {
        'img': filename,
        'ipfs': hash
    }
    json.dump(fp=open('./json/{}'.format(dest), 'w'), obj=j, indent=4)

# make_start_img()
# make_final_img()
# add_images_to_quiz()
# add_images_to_ipfs()
make_img('No such survey', 'no_such_survey.json')



# shuffle_questions()