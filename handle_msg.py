# -*- coding: utf-8 -*-
import time
import re
from config import allowed_users, master_users, chat_groups
from bs4 import BeautifulSoup
import requests
import urllib.request, urllib.error, urllib.parse
import http.cookiejar
import json
import os
import sys
#from random import randint, choice
from random import uniform, choice
from string import ascii_letters
from image import check_image_request, insert_images, insert_image_request
from telepot.exception import TelegramError
import json

def _convert_to_idn(url):
    """Convert a URL to IDN notation"""
    # this function should only be called with a unicode string
    # strategy: if the host cannot be encoded in ascii, then
    # it'll be necessary to encode it in idn form
    parts = list(urllib.parse.urlsplit(url))
    try:
        parts[1].encode('ascii')
    except UnicodeEncodeError:
        # the url needs to be converted to idn notation
        host = parts[1].rsplit(':', 1)
        newhost = []
        port = ''
        if len(host) == 2:
            port = host.pop()
        for h in host[0].split('.'):
            newhost.append(h.encode('idna').decode('utf-8'))
        parts[1] = '.'.join(newhost)
        if port:
            parts[1] += ':' + port
        return urllib.parse.urlunsplit(parts)
    else:
        return url 

def fetch_images_from_db(chat_id,keyword_id,keyword_n,db,shared_dict):
    search = False
    if str(chat_id) + str(keyword_id) +'db' in shared_dict:
        print("%s for group %s already in progress, sleeping for a while" % (keyword_id,chat_id))
        time.sleep(uniform(1,5))
    else:
        shared_dict[str(chat_id) + str(keyword_id) + 'db'] = 1
        search = True

    query = "SELECT id,url,type FROM images WHERE chat_id = %s AND keyword_id = %s AND keyword_n = %s AND requested = FALSE LIMIT 10"
    #print 'chat_id - {}, keyword_id - {}, keyword_n - {}'.format(chat_id,keyword_id,keyword_n)
    data = db.fetch_data(query,(chat_id,keyword_id,keyword_n,))
    if data is not None:
        if len(data) < 3:
            query = "DELETE FROM images WHERE chat_id = %s AND keyword_id = %s AND keyword_n = %s"
            db.execute(query,(chat_id,keyword_id,keyword_n,))
            return None
        for i in data:
            query = "UPDATE images SET requested = TRUE WHERE chat_id = %s AND keyword_n = %s AND id = %s"
            db.execute(query,(chat_id,keyword_n,i[0]))
        if search is True:
            del shared_dict[str(chat_id) + str(keyword_id) + 'db']
        return data
    return data

def fetch_images_from_google(chat_id,keyword,keyword_id,keyword_n,header,db,shared_dict,bot):
    if str(chat_id) + keyword in shared_dict:
        bot.sendMessage(chat_id,'po etomu slovu poka idet poisk - ' + keyword)
        return 1

    shared_dict[str(chat_id) + keyword] = 1
    query = keyword.split()
    #query = str('+'.join(query).encode('utf-8'))
    query = '+'.join(query)
    print('query - ' + query)

    url="https://www.google.co.in/search?q="+urllib.parse.quote(query)+"&source=lnms&tbm=isch"
    soup = BeautifulSoup(urllib.request.urlopen(urllib.request.Request(url,headers=header)),'html.parser')

    ActualImages=[]
    for a in soup.find_all("div",{"class":"rg_meta"}):
        link , Type =json.loads(a.text)["ou"]  ,json.loads(a.text)["ity"]
        ActualImages.append((link,Type))

    total_images = len(ActualImages)
    if total_images == 0:
        del shared_dict[str(chat_id) + keyword]
        return None

    print("there are total" , total_images,"images")
    nuran = {}
    i = 0

    for a, (img , Type) in enumerate( ActualImages):
        if Type == 'png' or Type == 'jpg':
            nuran[i] = {}
            nuran[i]['url'] = img
            nuran[i]['type'] = Type
            i += 1

    if len(nuran) < 3:
        del shared_dict[str(chat_id) + keyword]
        return None

    del shared_dict[str(chat_id) + keyword]
    #print shared_dict

    insert_images(chat_id,keyword_id,keyword_n,nuran,db)
    return fetch_images_from_db(chat_id,keyword_id,keyword_n,db,shared_dict)

def fetch_images(chat_id,keyword,keyword_n,header,db,shared_dict,bot):
    keyword_id = check_image_request(chat_id,keyword,db)
    if keyword_id is not None:
        images = fetch_images_from_db(chat_id,keyword_id[0],keyword_n,db,shared_dict)
        return images if images is not None else fetch_images_from_google(chat_id,keyword,keyword_id,keyword_n,header,db,shared_dict,bot)

    keyword_id = insert_image_request(chat_id,keyword,db)
    return fetch_images_from_google(chat_id,keyword,keyword_id,keyword_n,header,db,shared_dict,bot)

def get_image(chat_id,keyword,shared_dict,db,bot,msg=True):
    print('keyword - ' + keyword)

    header={'User-Agent':"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.134 Safari/537.36"}
    shared_dict[str(chat_id) + 'n'] += 1

    keyword_n = len(keyword) % 10
    nuran = fetch_images(chat_id,keyword,keyword_n,header,db,shared_dict,bot)
    if nuran == 1:
        shared_dict[str(chat_id) + 'n'] -= 1
        return
    if nuran is None and msg is True:
        shared_dict[str(chat_id) + 'n'] -= 1
        bot.sendMessage(chat_id,'ni4ego ne naydeno(')
        return

    DIR = '/tmp'
    index = 0
    num = 0

    if msg is True:
        bot.sendMessage(chat_id,'lovi fotki')
    while 1:
        try:
            print('trying to open %s' % nuran[index][1])
            url = _convert_to_idn(urllib.parse.unquote(nuran[index][1]))
            print('unquotted url %s' % url)
            url = urllib.parse.quote(url,safe=':/')
            req = urllib.request.Request(url, headers=header)
            raw_img = urllib.request.urlopen(req,timeout=5).read()
            type = 'jpg' if nuran[index][2] == True else 'png'
            image_name =  "".join(choice(ascii_letters) for i in range(20))
            f = open(os.path.join(DIR , image_name + "."+type), 'wb')
            f.write(raw_img)
            f.close()
            print('sending %s' % os.path.join(DIR , image_name + "."+type))
            bot.sendPhoto(chat_id,open(os.path.join(DIR , image_name + "."+type), 'rb'))
            os.unlink(os.path.join(DIR , image_name + "."+type))
        except TelegramError as e:
            print("Telegram error - {}".format(e))
            index += 1
            #if e[0] == 'Bad Request: PHOTO_INVALID_DIMENSIONS':
            #    print('invalid image')
            continue
        except IndexError:
            print("index out of range, breaking")
            break
        except Exception as e:
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print("error - {}".format(e))
            print(exc_type, fname, exc_tb.tb_lineno)
            index += 1
            continue
        num += 1
        index += 1
        if num >= 3:
            break

    shared_dict[str(chat_id) + 'n'] -= 1
    print('chat id count for %s - %s' % (chat_id,shared_dict[str(chat_id) + 'n']))

def generate_bot_array(lst):
    keyboard_lst = []
    tmp_lst = []
    i = 0
    for val in lst:
        i += 1
        tmp_lst.append(val)
        if i % 3 == 0:
            keyboard_lst.append(tmp_lst)
            tmp_lst = []

    keyboard_lst.append(tmp_lst)
    return keyboard_lst

def handle_msg(msg,bot,shared_dict,db):
    chat_id = str(msg['chat']['id'])
    if msg['chat']['id'] in master_users and chat_id + 'chat' in shared_dict:
        if msg['text'].upper() == 'STOP':
            bot.sendMessage(chat_id,'Chat has been ended',reply_markup={'hide_keyboard': True})
            del shared_dict[chat_id + 'chat']
            return

        if shared_dict[chat_id + 'chat'] == 0:
            if msg['text'] not in chat_groups:
                bot.sendMessage(chat_id,'Incorrect group',reply_markup={'hide_keyboard': True})
                del shared_dict[chat_id + 'chat']
                return

            shared_dict[chat_id + 'chat'] = chat_groups[msg['text']]
            bot.sendMessage(chat_id,"You're talking with group %s" % msg['text'],reply_markup={'hide_keyboard': True})
        else:
            bot.sendMessage(shared_dict[chat_id + 'chat'],msg['text'])
    elif msg['chat']['id'] in master_users and 'forward' in shared_dict and msg['text'].upper() == 'STOP FORWARD':
        bot.sendMessage(chat_id,"OK, forwarding has been disabled, bye")
        del shared_dict['forward']
    elif msg['chat']['id'] in master_users and msg['text'].upper() == 'CHAT':
        bot.sendMessage(chat_id,'Which one?',reply_markup={'keyboard': generate_bot_array(chat_groups.keys())})
        shared_dict[chat_id + 'chat'] = 0
    elif msg['chat']['id'] in master_users and msg['text'].upper() == 'FORWARD':
        bot.sendMessage(chat_id,"OK, I'll forward all msgs to you")
        shared_dict['forward'] = msg['chat']['id']
    elif ((msg['chat']['type'] == 'private' and msg['chat']['id'] in allowed_users) or
        (msg['chat']['type'] == 'supergroup' or msg['chat']['type'] == 'group') and msg['chat']['id'] in allowed_users):

        if chat_id + 'n' not in shared_dict:
            shared_dict[chat_id + 'n'] = 0

        # check shared dict
        if shared_dict[chat_id + 'n'] >= allowed_users[msg['chat']['id']]:
            bot.sendMessage(msg['chat']['id'],'ya poka zanat')
            return

        # check msgs
        if 'text' in msg and re.match(r'(FOTKI|ФОТКИ) .+',msg['text'].upper(),re.IGNORECASE):
            bot.sendMessage(chat_id,'pristupayu k poisku fotok')
            get_image(chat_id,re.match(r'^[^\s]+ (.+)$',msg['text'],re.IGNORECASE).group(1),shared_dict,db,bot)
    elif msg['chat']['type'] == 'private':
        bot.sendMessage(msg['from']['id'],'idi na huy, ya teba ne znayu')
    else:
        pass
