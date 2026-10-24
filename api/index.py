"""Vercel Python Function entrypoint; business logic lives in server/."""
from server.app import handler_for
from server.database import LazyStore

BaseHandler = handler_for(LazyStore())


class handler(BaseHandler):
    """Named top-level class recognized by Vercel's Python entrypoint analysis."""
