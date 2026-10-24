"""Public form responses are bounded and never disclose the response collection."""
import hashlib
import json
import math
import re
from datetime import date
from server.store import InvalidInput


def form_schema(content):
    fields=content.get('fields') or [{'type':'text','required':True,'options':[]} for _ in content['questions']]
    result={'questions':content['questions'],'fields':fields}
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
