#!/usr/bin/python3
import tornado.ioloop
import asyncio

# Import frontend and backend files
from Web.BackEnd import BackEnd
from Web.FrontEnd import FrontEnd

def create_app():
    return tornado.web.Application([
        (r"/labs/",FrontEnd),
        (r"/backend/",BackEnd)])


if __name__ == '__main__':
    app = create_app()
    app.listen(8888)
    try:
        tornado.ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        tornado.ioloop.IOLoop.instance().stop()