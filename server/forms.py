"""Public form responses are bounded and never disclose the response collection."""
import hashlib
import json
import math
import re
from datetime import date
from server.store import InvalidInput


def form_schema(content):
    fields=content.get('fields') or [{'type':'text','required':True,'options':[]} for _ in content['questions']]
    public_fields=[{k:v for k,v in field.items() if k in ('type','required','options')} for field in fields]
    result={'questions':content['questions'],'fields':public_fields}
    result['schema_id']=hashlib.sha256(json.dumps(result,sort_keys=True).encode()).hexdigest()
    return result


def validate_answers(content, answers, schema_id):
    schema=form_schema(content)
    if schema_id != schema['schema_id']:
        raise InvalidInput('As perguntas mudaram. Reabra o formulário antes de responder.')
    if not isinstance(answers,list) or len(answers)!=len(schema['questions']):
        raise InvalidInput('Responda às perguntas do formulário.')
    for answer,field in zip(answers,schema['fields']):
        if not isinstance(answer,str) or len(answer)>4000 or (field['required'] and not answer.strip()):
            raise InvalidInput('Preencha os campos obrigatórios com até 4000 caracteres.')
        if not answer:
            continue
        kind=field['type']
        if kind=='rating' and answer not in ('1','2','3','4','5'):raise InvalidInput('Escolha uma avaliação de 1 a 5.')
        if kind=='choice' and answer not in field.get('options',[]):
            raise InvalidInput('Selecione uma opção válida.')
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
        if 'score' in response or 'maxScore' in response:
            if type(response.get('score')) is not int or type(response.get('maxScore')) is not int or not 0<=response['score']<=response['maxScore']<=10000:return False
    return True
