# settings
import config

# various modules
import multiprocessing
import threading
from Queue import Queue
import time
import os
import signal
import db

# telepot's msg loop & Bot
from telepot.loop import MessageLoop
from telepot import Bot 
from handle_msg import handle_msg

# bot object
bot = Bot(config.token)
mgr = multiprocessing.Manager()
shared_dict = mgr.dict()

def thread(fork_process,thread_queue,shared_dict):
    thread = threading.currentThread()
    post = db.DB(config.username,config.password,config.dbname,config.host,config.port)
    post.connect()
    print 'fork process - %s, thread - %s' % (fork_process,thread.getName())
    while 1:
        msg = thread_queue.get()
        print 'received msg from fork_process - {}, thread - {}, msg - {}'.format(fork_process,thread.getName(),msg,post)
        handle_msg(msg,bot,shared_dict,post)
        #bot.sendMessage(data['from']['id'],data['text'])

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
    except KeyboardInterrupt, e:
        print os.getpid()
        os.kill(parent_process, signal.SIGKILL)

def handle(msg):
    fork_queue.put(msg)

fork_queue = multiprocessing.Queue()
parent_process = os.getpid()

for i in range(config.forks_qt):
    p = multiprocessing.Process(target=worker,args=(parent_process,fork_queue,shared_dict))
    p.daemon = True
    p.start()

MessageLoop(bot, handle).run_forever()
