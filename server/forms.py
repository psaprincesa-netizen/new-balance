"""Public form responses are bounded and never disclose the response collection."""
import hashlib
import json
import math
import re
import unicodedata
from datetime import date
from server.store import InvalidInput
from server.form_conditions import valid_conditions,visible_questions,canonical_answers


MULTI_SEPARATOR='; '
PRIVATE_FIELD_KEYS=('correct','correctAnswer','points')


def full_fields(content):
    return content.get('fields') or [{'type':'text','required':True,'options':[]} for _ in content['questions']]


def form_schema(content):
    # Correct answers and points stay private: respondents only see the questions.
    fields=[{k:v for k,v in f.items() if k not in PRIVATE_FIELD_KEYS} for f in full_fields(content)]
    if not valid_conditions(fields):raise InvalidInput('O proprietário deve revisar as condições de exibição deste formulário.')
    result={'questions':content['questions'],'fields':fields,'quiz':bool(content.get('quiz'))}
    result['schema_id']=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()
    return result


def validate_answers(content, answers, schema_id):
    schema=form_schema(content)
    if schema_id != schema['schema_id']:
        raise InvalidInput('As perguntas mudaram. Reabra o formulário antes de responder.')
    if not isinstance(answers,list) or len(answers)!=len(schema['questions']):
        raise InvalidInput('Responda às perguntas do formulário.')
    if any(not isinstance(a,str) or len(a)>4000 for a in answers):raise InvalidInput('Use respostas textuais com até 4000 caracteres.')
    answers=canonical_answers(schema['fields'],answers)
    visible=visible_questions(schema['fields'],answers)
    for index,(answer,field) in enumerate(zip(answers,schema['fields'])):
        if not visible[index]:continue
        if not isinstance(answer,str) or len(answer)>4000 or (field['required'] and not answer.strip()):
            raise InvalidInput('Preencha os campos obrigatórios com até 4000 caracteres.')
        if not answer:
            continue
        kind=field['type']
        if kind=='rating' and answer not in ('1','2','3','4','5'):raise InvalidInput('Escolha uma avaliação de 1 a 5.')
        if kind=='choice' and answer not in field.get('options',[]):
            raise InvalidInput('Selecione uma opção válida.')
        if kind=='multiple':
            picked=answer.split(MULTI_SEPARATOR)
            if len(set(picked))!=len(picked) or any(p not in field.get('options',[]) for p in picked):
                raise InvalidInput('Selecione opções válidas.')
        if kind=='scale' and answer not in [str(n) for n in range(1,field.get('max',5)+1)]:
            raise InvalidInput('Escolha um valor da escala.')
        if kind=='email' and not re.fullmatch(r'[^\s@]+@[^\s@]+\.[^\s@]+',answer):
            raise InvalidInput('Informe um e-mail válido.')
        if kind=='number':
            try:
                if not math.isfinite(float(answer)):raise ValueError()
            except ValueError:raise InvalidInput('Informe um número válido.') from None
        if kind=='date':
            try:date.fromisoformat(answer)
            except ValueError:raise InvalidInput('Informe uma data válida.') from None
    return answers


def _normalize(value):
    text=unicodedata.normalize('NFKD',str(value))
    return ' '.join(''.join(ch for ch in text if not unicodedata.combining(ch)).casefold().split())


def is_graded(field):
    correct=field.get('correct',field.get('correctAnswer'))
    return bool(correct) if isinstance(correct,list) else isinstance(correct,str) and correct!=''


def answer_is_correct(answer,field):
    kind=field.get('type')
    if kind=='multiple':
        return set(answer.split(MULTI_SEPARATOR) if answer else [])==set(field.get('correct') or [])
    if kind=='number':
        try:
            return answer!='' and float(answer)==float(field['correct'])
        except ValueError:
            return False
    if kind in ('choice','scale'):
        return answer==field['correct']
    return answer!='' and _normalize(answer)==_normalize(field['correct'])


def score_response(content,answers):
    """Quiz score computed on the server, so public respondents never see the key."""
    score=total=0
    fields=full_fields(content);visible=visible_questions(fields,answers)
    for index,(answer,field) in enumerate(zip(answers,fields)):
        if not visible[index]:continue
        field={**field,'correct':field.get('correct',field.get('correctAnswer'))}
        if not is_graded(field):
            continue
        points=field.get('points',1)
        total+=points
        if answer_is_correct(answer,field):
            score+=points
    return {'score':score,'total':total}
def quiz_score(content,answers):
    if not content.get('quiz'):return {}
    earned=maximum=0
    for answer,field in zip(answers,content.get('fields',[])):
        if 'correctAnswer' not in field:continue
        points=field.get('points',1);maximum+=points
        if answer.strip().casefold()==field['correctAnswer'].strip().casefold():earned+=points
    return {'score':earned,'maxScore':maximum}

def valid_quiz(content):
    if type(content.get('quiz',False)) is not bool:return False
    if not isinstance(content.get('fields',[]),list) or not isinstance(content.get('responses',[]),list):return False
    if any(not isinstance(f,dict) for f in content.get('fields',[])):return False
    if not valid_conditions(content.get('fields',[])):return False
    for field in content.get('fields',[]):
        if not isinstance(field,dict):return False
        if 'points' in field and (type(field['points']) is not int or not 0<=field['points']<=100):return False
        if 'correctAnswer' in field:
            answer=field['correctAnswer']
            if not isinstance(answer,str) or not 1<=len(answer)<=4000:return False
            if field.get('type')=='choice' and answer not in field.get('options',[]):return False
            if field.get('type')=='rating' and answer not in ('1','2','3','4','5'):return False
    for response in content.get('responses',[]):
        if not isinstance(response,dict):return False
        if 'maxScore' in response:
            if type(response.get('score')) is not int or type(response.get('maxScore')) is not int or not 0<=response['score']<=response['maxScore']<=10000:return False
    return True
