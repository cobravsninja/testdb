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

def fetch_images_from_db(chat_id,keyword_id,keyword_n,db):
    query = "SELECT id,url,type FROM images WHERE chat_id = %s AND keyword_id = %s AND keyword_n = %s AND requested = b'0' LIMIT 10"
    print 'chat_id - {}, keyword_id - {}, keyword_n - {}'.format(chat_id,keyword_id,keyword_n)
    data = db.fetch_data(query,(chat_id,keyword_id,keyword_n,))
    if data is not None:
        if len(data) < 3:
            query = "DELETE FROM images WHERE chat_id = %s AND keyword_id = %s AND keyword_n = %s"
            db.execute(query,(chat_id,keyword_id,keyword_n,))
            return None
        return data
    return data

def fetch_images_from_google(chat_id,keyword,keyword_id,keyword_n,header,db):
    query = keyword.split()
    query = '+'.join(query)

    url="https://www.google.co.in/search?q="+query+"&source=lnms&tbm=isch"
    soup = BeautifulSoup(urllib2.urlopen(urllib2.Request(url,headers=header)),'html.parser')

    ActualImages=[]
    for a in soup.find_all("div",{"class":"rg_meta"}):
        link , Type =json.loads(a.text)["ou"]  ,json.loads(a.text)["ity"]
        ActualImages.append((link,Type))

    total_images = len(ActualImages)
    if total_images == 0:
        #shared_dict[chat_id] -= 1
        #bot.sendMessage(chat_id,'ni4ego ne naydeno(')
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
        return None

    # populate db
    insert_images(chat_id,keyword_id,keyword_n,nuran,db)
    return fetch_images_from_db(chat_id,keyword_id,keyword_n,db)

def fetch_images(chat_id,keyword,keyword_n,header,db):
    keyword_id = check_image_request(chat_id,keyword,db)
    if keyword_id is not None:
        images = fetch_images_from_db(chat_id,keyword_id[0],keyword_n,db)
        print images
        return images if images is not None else fetch_images_from_google(chat_id,keyword,keyword_id,keyword_n,header,db)

    keyword_id = insert_image_request(chat_id,keyword,db)
    return fetch_images_from_google(chat_id,keyword,keyword_id,keyword_n,header,db)

def get_image(chat_id,keyword,shared_dict,db,bot):
    header={'User-Agent':"Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/43.0.2357.134 Safari/537.36"}
    shared_dict[chat_id] += 1

    keyword_n = len(keyword) % 10
    nuran = fetch_images(chat_id,keyword,keyword_n,header,db)
    if nuran is None:
        shared_dict[chat_id] -= 1
        bot.sendMessage(chat_id,'ni4ego ne naydeno(')
        return

    DIR = '/tmp'
    num = 0

    bot.sendMessage(chat_id,'lovi fotki')
    while 1:
        query = "UPDATE images SET requested = b'1' WHERE chat_id = %s AND keyword_n = %s AND id = %s"
        try:
            print "url - {}".format(nuran[num][1])
            req = urllib2.Request(nuran[num][1], headers={'User-Agent' : header})
            raw_img = urllib2.urlopen(req,timeout=10).read()
            type = 'jpg' if nuran[num][2] == 0 else 'png'
            image_name =  "".join(choice(ascii_letters) for i in range(20))
            print 'image_name ' + image_name
            f = open(os.path.join(DIR , image_name + "."+type), 'wb')
            f.write(raw_img)
            f.close()
            bot.sendPhoto(chat_id,open(os.path.join(DIR , image_name + "."+type), 'rb'))
            os.unlink(os.path.join(DIR , image_name + "."+type))
            db.execute(query,(chat_id,keyword_n,nuran[num][0]))
        except TelegramError as e:
            print "Telegram error - {}".format(e)
            if e[0] == 'Bad Request: PHOTO_INVALID_DIMENSIONS':
                print 'invalid image'
                db.execute(query,(chat_id,keyword_n,nuran[num][0]))
            num += 1
        except Exception as e:
            print "error - {}".format(e)
            num += 1
        num += 1
        if num >= 3:
            break

    shared_dict[chat_id] -= 1

def handle_msg(msg,bot,shared_dict,db):
    if ((msg['chat']['type'] == 'private' and msg['chat']['id'] in allowed_users) or
        (msg['chat']['type'] == 'supergroup' or msg['chat']['type'] == 'group') and msg['chat']['id'] in allowed_users):

        # check shared dict
        if msg['chat']['id'] not in shared_dict:
            shared_dict[msg['chat']['id']] = 0
        if shared_dict[msg['chat']['id']] >= allowed_users[msg['chat']['id']]:
            bot.sendMessage(msg['chat']['id'],'ya poka zanat')
            return

        # check msgs
        if 'text' in msg and re.match(ur'fotki .+',msg['text'],re.IGNORECASE):
            get_image(msg['chat']['id'],re.match(ur'^fotki (.+)$',msg['text'],re.IGNORECASE).group(1),shared_dict,db,bot)
    elif msg['chat']['type'] == 'private':
        bot.sendMessage(msg['from']['id'],'idi na huy, ya teba ne znayu')
    else:
        pass
