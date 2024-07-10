import logging

# Configure the logging with time
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    datefmt='%m/%d/%Y %I:%M:%S %p')

# Create a logger object
logger = logging.getLogger(__name__)


def get_quiz_result(all_answers):
    scores = {}

    for answer in all_answers:
        for category in answer.question.categories:
            try:
                scores[category] += answer.value
            except KeyError:
                scores[category] = answer.value

    already_seen = set()
    names = []
    for category in scores:
        if category.name in already_seen:
            continue
        if scores.get(category, 0) > scores.get(category.opposite, 0):
            names.append(category.name)
        else:
            names.append(category.opposite.name)
        already_seen.add(category.name)
        already_seen.add(category.opposite.name)

    result = {
        'name': ' '.join(names),
        'scores': scores
    }
    logger.info('Computed result of quiz: {}'.format(result))

    return result
