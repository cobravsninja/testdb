# settings
import config

# various modules
import sys
import time
import multiprocessing
import threading
from queue import Queue
import time
import os
import signal
import db
import time
from random import randint

# telepot's msg loop & Bot
from telepot.loop import MessageLoop
from telepot import Bot 
import asyncio
from handle_msg import handle_msg, get_image

# bot object
bot = Bot(config.token)
mgr = multiprocessing.Manager()
shared_dict = mgr.dict()

def thread(fork_process,thread_queue,shared_dict):
    thread = threading.currentThread()
    post = db.DB(config.username,config.password,config.dbname,config.host,config.port)
    post.connect()
    print('fork process - %s, thread - %s' % (fork_process,thread.getName()))
    while 1:
        msg = thread_queue.get()
        print('received msg from fork_process - {}, thread - {}, msg - {}'.format(fork_process,thread.getName(),msg,post))
        if 'forward' in shared_dict:
            if shared_dict['forward'] != msg['chat']['id']:
                bot.sendMessage(shared_dict['forward'],'{}'.format(msg))
        if 'scheduler' not in msg:
            handle_msg(msg,bot,shared_dict,post)
        else:
            if str(msg['chat_id']) + 'n' not in shared_dict:
                shared_dict[str(msg['chat_id']) + 'n'] = 0
            get_image(msg['chat_id'],msg['keyword'],shared_dict,post,bot,False)

def worker(parent_process,fork_queue,shared_dict):
    fork_process = multiprocessing.current_process()
    thread_queue = Queue()
    for i in range(config.threads_qt):
        t = threading.Thread(target=thread,args=(fork_process.name,thread_queue,shared_dict))
        t.setDaemon(True)
        t.start()
    try:
        #print 'Starting:',fork_process.name,fork_process.pid
        while 1:
            data = fork_queue.get()
            thread_queue.put(data)
    except KeyboardInterrupt as e:
        pass

def handle(msg):
    fork_queue.put(msg)

fork_queue = multiprocessing.Queue()
parent_process = os.getpid()

for i in range(config.forks_qt):
    p = multiprocessing.Process(target=worker,args=(parent_process,fork_queue,shared_dict))
    p.daemon = True
    p.start()

@asyncio.coroutine
def scheduler():
    while True:
        yield None
        for i in config.pida_groups:
            time.sleep(int(str(3) + str(randint(100,999))))
            bot.sendMessage(i,'kuku pidarugi')
            fork_queue.put({'scheduler':1,'chat_id':i,'keyword':'victoria secret'})

@asyncio.coroutine
def telepuzik():
    MessageLoop(bot,handle).run_as_thread()
    yield None

if __name__ == "__main__":
    try:
        tasks = asyncio.gather(asyncio.async(telepuzik()),asyncio.async(scheduler()))
        loop = asyncio.get_event_loop()
        loop.run_forever()
    except KeyboardInterrupt as e:
        print("keyboard interrupted")
