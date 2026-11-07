"""Conditions refer only to earlier single-choice questions, preventing cycles."""
def valid_conditions(fields):
    for i,field in enumerate(fields):
        condition=field.get('showWhen')
        if condition is None:continue
        if not isinstance(condition,dict) or set(condition)!={'question','value'}:return False
        parent=condition.get('question');value=condition.get('value')
        if type(parent) is not int or not 0<=parent<i:return False
        if fields[parent].get('type')!='choice' or not isinstance(value,str) or value=='' or not isinstance(fields[parent].get('options',[]),list) or value not in fields[parent].get('options',[]):return False
    return True


def visible_questions(fields,answers):
    visible=[]
    for field in fields:
        condition=field.get('showWhen')
        visible.append(not condition or (visible[condition['question']] and condition['question']<len(answers) and answers[condition['question']]==condition['value']))
    return visible


def canonical_answers(fields,answers):
    return [answer if visible else '' for answer,visible in zip(answers,visible_questions(fields,answers))]
