# -*- coding: utf-8 -*-
import re
from config import allowed_users
from bs4 import BeautifulSoup
import requests
import urllib2
import cookielib
import json
import os
from random import randint, choice
from string import ascii_letters
from image import check_image_request, insert_images, insert_image_request
from telepot.exception import TelegramError
import json

def fetch_images_from_db(chat_id,keyword_id,keyword_n,db):
    query = "SELECT id,url,type FROM images WHERE chat_id = %s AND keyword_id = %s AND keyword_n = %s AND requested = FALSE LIMIT 3"
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
        return data
    return data

def fetch_images_from_google(chat_id,keyword,keyword_id,keyword_n,header,db,shared_dict,bot):
    if str(chat_id) + keyword in shared_dict:
        bot.sendMessage(chat_id,'po etomu slovu poka idet poisk - ' + keyword)
        return 1

    shared_dict[str(chat_id) + keyword] = 1
    query = keyword.split()
    query = u'+'.join(query).encode('utf-8')
    print 'query - ' + query

    url="https://www.google.co.in/search?q="+query+"&source=lnms&tbm=isch"
    soup = BeautifulSoup(urllib2.urlopen(urllib2.Request(url,headers=header)),'html.parser')

    ActualImages=[]
    for a in soup.find_all("div",{"class":"rg_meta"}):
        link , Type =json.loads(a.text)["ou"]  ,json.loads(a.text)["ity"]
        ActualImages.append((link,Type))

    total_images = len(ActualImages)
    if total_images == 0:
        del shared_dict[str(chat_id) + keyword]
        return None

    print  "there are total" , total_images,"images"
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
    return fetch_images_from_db(chat_id,keyword_id,keyword_n,db)

def fetch_images(chat_id,keyword,keyword_n,header,db,shared_dict,bot):
    keyword_id = check_image_request(chat_id,keyword,db)
    if keyword_id is not None:
        images = fetch_images_from_db(chat_id,keyword_id[0],keyword_n,db)
        #print images
        return images if images is not None else fetch_images_from_google(chat_id,keyword,keyword_id,keyword_n,header,db,shared_dict,bot)

    keyword_id = insert_image_request(chat_id,keyword,db)
    return fetch_images_from_google(chat_id,keyword,keyword_id,keyword_n,header,db,shared_dict,bot)

def get_image(chat_id,keyword,shared_dict,db,bot):
    print 'keyword - ' + keyword

    header={'User-Agent':"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.134 Safari/537.36"}
    shared_dict[str(chat_id) + 'n'] += 1

    keyword_n = len(keyword) % 10
    nuran = fetch_images(chat_id,keyword,keyword_n,header,db,shared_dict,bot)
    if nuran == 1:
        shared_dict[str(chat_id) + 'n'] -= 1
        return
    if nuran is None:
        shared_dict[str(chat_id) + 'n'] -= 1
        bot.sendMessage(chat_id,'ni4ego ne naydeno(')
        return

    DIR = '/tmp'
    num = 0

    bot.sendMessage(chat_id,'lovi fotki')
    while 1:
        try:
            print 'trying to open %s' % nuran[num][1]
            req = urllib2.Request(nuran[num][1], headers={'User-Agent' : header})
            raw_img = urllib2.urlopen(req,timeout=5).read()
            type = 'jpg' if nuran[num][2] == True else 'png'
            image_name =  "".join(choice(ascii_letters) for i in range(20))
            f = open(os.path.join(DIR , image_name + "."+type), 'wb')
            f.write(raw_img)
            f.close()
            print 'sending %s' % os.path.join(DIR , image_name + "."+type)
            bot.sendPhoto(chat_id,open(os.path.join(DIR , image_name + "."+type), 'rb'))
            os.unlink(os.path.join(DIR , image_name + "."+type))
        except TelegramError as e:
            print "Telegram error - {}".format(e)
            if e[0] == 'Bad Request: PHOTO_INVALID_DIMENSIONS':
                print 'invalid image'
            num += 1
        except Exception as e:
            print "error - {}".format(e)
            num += 1
        num += 1
        if num >= 3:
            break

    shared_dict[str(chat_id) + 'n'] -= 1

def handle_msg(msg,bot,shared_dict,db):
    if ((msg['chat']['type'] == 'private' and msg['chat']['id'] in allowed_users) or
        (msg['chat']['type'] == 'supergroup' or msg['chat']['type'] == 'group') and msg['chat']['id'] in allowed_users):

        if str(msg['chat']['id']) + 'n' not in shared_dict:
            shared_dict[str(msg['chat']['id']) + 'n'] = 0

        # check shared dict
        if shared_dict[str(msg['chat']['id']) + 'n'] >= allowed_users[msg['chat']['id']]:
            bot.sendMessage(msg['chat']['id'],'ya poka zanat')
            return

        # check msgs
        if 'text' in msg and re.match(ur'(FOTKI|ФОТКИ) .+',msg['text'].upper(),re.IGNORECASE):
            bot.sendMessage(msg['chat']['id'],'pristupayu k poisku fotok')
            get_image(msg['chat']['id'],re.match(ur'^[^\s]+ (.+)$',msg['text'],re.IGNORECASE).group(1),shared_dict,db,bot)
    elif msg['chat']['type'] == 'private':
        bot.sendMessage(msg['from']['id'],'idi na huy, ya teba ne znayu')
    else:
        pass
