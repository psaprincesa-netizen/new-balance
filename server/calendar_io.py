"""iCalendar exchange with bounded recurrence expansion and timezone conversion."""
from datetime import datetime, date, time, timedelta, timezone
from itertools import islice
from icalendar import Calendar, Event
from dateutil.rrule import rrulestr
from server.store import InvalidInput


def timestamp(value):
    if isinstance(value,datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value,date):
        return datetime.combine(value,time.min,tzinfo=timezone.utc)
    raise InvalidInput('Evento sem data de início válida.')


def import_calendar(data):
    try:
        calendar=Calendar.from_ical(data)
        events=[]
        for component in calendar.walk('VEVENT'):
            if component.get('RECURRENCE-ID') or component.get('RDATE'):
                raise InvalidInput('Exceções de recorrência e RDATE precisam ser convertidos em eventos individuais antes de importar.')
            start=timestamp(component.decoded('DTSTART'))
            end=timestamp(component.decoded('DTEND')) if component.get('DTEND') else start+component.decoded('DURATION',timedelta(hours=1))
            if end<=start:raise InvalidInput('Um evento tem duração inválida.')
            starts=[start]
            rule=component.get('RRULE')
            if rule:
                if not rule.get('COUNT') and not rule.get('UNTIL'):
                    raise InvalidInput('Recorrências precisam ter uma data final ou quantidade definida.')
                if rule.get('FREQ',[None])[0] not in ('DAILY','WEEKLY','MONTHLY','YEARLY'):
                    raise InvalidInput('Use recorrência diária, semanal, mensal ou anual.')
                starts=list(islice(rrulestr(rule.to_ical().decode(),dtstart=start),1001))
            excluded=set()
            entries=component.get('EXDATE',[])
            for entry in entries if isinstance(entries,list) else [entries]:
                excluded.update(timestamp(v.dt) for v in entry.dts)
            for occurrence in starts:
                if occurrence in excluded:continue
                events.append({'title':str(component.get('SUMMARY','Evento'))[:200],
                    'start':occurrence.astimezone(timezone.utc).isoformat(),
                    'end':(occurrence+(end-start)).astimezone(timezone.utc).isoformat(),
                    'location':str(component.get('LOCATION',''))[:500],
                    'description':str(component.get('DESCRIPTION',''))[:4000]})
                if len(events)>1000:raise InvalidInput('Limite de 1000 ocorrências por agenda.')
        if not events:raise InvalidInput('Nenhum evento foi encontrado no arquivo ICS.')
        return {'events':events}
    except InvalidInput:raise
    except Exception:raise InvalidInput('Arquivo ICS inválido. Confira as datas e recorrências.') from None


def export_calendar(item):
    calendar=Calendar();calendar.add('prodid','-//DRAP office//Agenda//PT-BR');calendar.add('version','2.0')
    for index,entry in enumerate(item['content']['events']):
        event=Event();event.add('uid',f"{item.get('id','calendar')}-{index}@drap-office")
        event.add('dtstamp',datetime.now(timezone.utc))
        event.add('summary',entry['title'])
        event.add('dtstart',timestamp(datetime.fromisoformat(entry['start'].replace('Z','+00:00'))))
        event.add('dtend',timestamp(datetime.fromisoformat(entry['end'].replace('Z','+00:00'))))
        event.add('location',entry.get('location',''));event.add('description',entry.get('description',''))
        calendar.add_component(event)
    return calendar.to_ical()
