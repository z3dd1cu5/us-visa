import os
import tornado.ioloop
import tornado.web
from datetime import datetime
from threading import Lock

lock = Lock()

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        global lock
        code = self.get_argument('code', '')
        email = self.get_argument('email', '')
        password = self.get_argument('pswd', '')
        lock.acquire()
        try:
            os.system('bash /home/zeddy/ais-ng/run.sh "%s" "%s" "%s" "/home/zeddy/ais-ng/session.txt"' % (code, email, password))
            page_text = open("/home/zeddy/ais-ng/session.txt.page", "r").read()
            if "Account Inactive" in page_text:
                self.write('{"code": 401, "error": "Account Banned"}')
            elif "Continue" in page_text:
                self.write(open("/home/zeddy/ais-ng/session.txt", "r").read())
            else:
                self.write('{"code": 402, "error": "AIS NG Failed"}')
        except Exception as e:
            print(e)
            self.write('{"code": 402, "error": "AIS NG Failed"}')
        os.system('rm "/home/zeddy/ais-ng/session.txt"')
        os.system('rm "/home/zeddy/ais-ng/session.txt.page"')
        lock.release()

        os.system('echo "[%s] %s %s %s" >> /home/zeddy/ais-ng/log.txt' % (datetime.now().strftime("%Y-%m-%d, %H:%M:%S"), code, email, password))

def make_app():
    return tornado.web.Application([
        (r"/ais-ng", MainHandler),
    ])

if __name__ == "__main__":
    app = make_app()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()
