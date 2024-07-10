from models import SessionLocal, Category, Task, Question, Cluster, Response, Completion
from preprocessing import add_images_to_task
import json
from random import randint, choice
from scoring import get_quiz_result
from faker import Faker

session = SessionLocal()


task = Task(
    title='The Network State Survey',
    description='This is a test for the network state survey',
    network='mumbai',
    contract_address='0x5A05289A5Ffbfa6a45663D092A0fE7C1Bc0c5bc9'
)

session.add(task)

# Create categories without setting opposites yet
category_structured = Category(name='Structured', task_id=task.task_id)
category_creative = Category(name='Creative', task_id=task.task_id)
category_individualist = Category(name='Individualist', task_id=task.task_id)
category_collectivist = Category(name='Collectivist', task_id=task.task_id)

session.add(category_structured)
session.add(category_creative)
session.add(category_individualist)
session.add(category_collectivist)

session.commit()


# Now set them as opposites of each other
category_creative.opposite_category_id = category_structured.category_id
category_structured.opposite_category_id = category_creative.category_id
category_collectivist.opposite_category_id = category_individualist.category_id
category_individualist.opposite_category_id = category_collectivist.category_id

session.add(category_structured)
session.add(category_creative)
session.add(category_individualist)
session.add(category_collectivist)


session.commit()


quiz = json.load(open('./json/quiz.json', 'r'))


# questions = []
for i, q in enumerate(quiz):
    question = Question(
        task_id=task.task_id,
        sequence_num=i+1,
        text=q['question'],
        image_path=q['img'],
        image_ipfs_hash=q['ipfs'])
    if q['category'] == 'Creative-Collectivist':
        question.categories = [category_creative, category_collectivist]
    elif q['category'] == 'Creative-Individualist':
        question.categories = [category_creative, category_individualist]
    elif q['category'] == 'Structured-Individualist':
        question.categories = [category_structured, category_individualist]
    elif q['category'] == 'Structured-Collectivist':
        question.categories = [category_structured, category_collectivist]

    session.add(question)
    # questions.append(question)

clusters = [
    Cluster(task_id=task.task_id, name='Creative Collectivist', image_ipfs_hash='Qmbbhbbawqnn1ZN6fWkQRL26cCrJYypLZJPKrFBMmY4Hfa'),
    Cluster(task_id=task.task_id, name='Creative Individualist', image_ipfs_hash='QmS25zAxoiAjBxW8f3QW4etahfnx9QcNTxxxsF3HJnCXRB'),
    Cluster(task_id=task.task_id, name='Structured Collectivist', image_ipfs_hash='QmV5zju6bM98CyZwpVmvSdZwR7Kou1eAYkfAXyfnkYDceV'),
    Cluster(task_id=task.task_id, name='Structured Individualist', image_ipfs_hash='QmQ3LHSPDVm3TpM2BGX5p3bwinDG8hknaHurQDHT5awMNf')
]
session.add_all(clusters)

session.commit()

# add_images_to_task(task.task_id)

fake = Faker()

num_surveyors = 10
questions = session.query(Question).filter_by(task_id=task.task_id).all()
for i in range(0, num_surveyors):
    fid = randint(0, 10000)
    username = fake.user_name()
    responses = []
    for question in questions:
        value = choice([-2, -1, 1, 2])
        response = Response(
            question_id=question.question_id,
            task_id=task.task_id,
            user_fid=fid,
            username=username,
            value=value
        )
        responses.append(response)
        session.add(response)

    session.commit()
    responses = session.query(Response).filter_by(task_id=task.task_id, user_fid=fid)
    result = get_quiz_result(responses)

    cluster = session.query(Cluster).filter_by(task_id=task.task_id, name=result['name']).first()
    completion = Completion(task_id=task.task_id, user_fid=fid, cluster_id=cluster.cluster_id, token_id=0)
    session.add(completion)
    session.commit()

session.commit()

