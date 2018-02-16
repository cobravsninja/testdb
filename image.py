import time
import calendar

def check_table(table_name,db):
    return db.fetch_one('SELECT 1 FROM information_schema.tables WHERE table_name= %s',(table_name,))

# image_requests date partition
def create_image_request_date(image_requests_part,db):
    last_day = calendar.monthrange(int(time.strftime('%Y')),int(time.strftime('%m')))[1]
    query = "CREATE TABLE {} PARTITION OF image_requests FOR VALUES FROM ('{}') TO ('{}') PARTITION BY LIST(chat_id)".format(
            image_requests_part,
            time.strftime('%Y-%m-01'),
            time.strftime('%Y-%m-') + str(last_day))
    db.execute(query)

# image_requests date/group partition
def create_image_request_group(image_requests_part,image_requests_part_group,chat_id,db):
    query = "CREATE TABLE {} PARTITION OF {} FOR VALUES IN ('{}')".format(
            image_requests_part_group,image_requests_part,chat_id)
    db.execute(query)
    query = "CREATE INDEX ON %s (keyword)" % image_requests_part_group
    db.execute(query)
    query = "CREATE INDEX ON %s (chat_id)" % image_requests_part_group
    db.execute(query)

# images group part
def create_images_part(images_part,chat_id,db):
    print('ya tut - ' + images_part)
    query = "CREATE TABLE {} PARTITION OF images FOR VALUES IN (%s) PARTITION BY LIST(keyword_n)".format(images_part)
    db.execute(query,(chat_id,))

# images group subpart
def create_images_sub_part(images_part,images_part_subpart,keyword_n,db):
    query = "CREATE TABLE {} PARTITION OF {} FOR VALUES IN ('{}')".format(
            images_part_subpart,images_part,keyword_n)
    db.execute(query)
    query = "CREATE INDEX ON %s (chat_id)" % images_part_subpart
    db.execute(query)
    query = "CREATE INDEX ON %s (keyword_id)" % images_part_subpart
    db.execute(query)
    query = "CREATE INDEX ON %s (id)" % images_part_subpart
    db.execute(query)

def insert_image_request(chat_id,keyword,db):
    image_requests_part = 'image_requests' + time.strftime('%Y%m')
    if check_table(image_requests_part,db) is None:
        create_image_request_date(image_requests_part,db)

    image_requests_part_group = image_requests_part + str(abs(int(chat_id)))
    if check_table(image_requests_part_group,db) is None:
        create_image_request_group(image_requests_part,image_requests_part_group,chat_id,db)

    query = 'INSERT INTO image_requests (keyword,logdate,chat_id) VALUES (%s,now(),%s) RETURNING id'
    return db.execute_out(query,(keyword,chat_id))

def check_image_request(chat_id,keyword,db):

    # check keyword existence
    query = """SELECT id FROM image_requests WHERE keyword = %s AND chat_id = %s
        AND logdate >= DATE_TRUNC('month',NOW())
        AND logdate < NOW() + INTERVAL '1 month -1 day'"""

    return db.fetch_one(query,(keyword,chat_id,))

def insert_images(chat_id,keyword_id,keyword_n,nuran,db):
    images_part = 'images%s' % abs(int(chat_id))

    if check_table(images_part,db) is None:
        create_images_part(images_part,chat_id,db)

    images_sub_part = images_part + str(keyword_n)
    if check_table(images_sub_part,db) is None:
        create_images_sub_part(images_part,images_sub_part,keyword_n,db)

    for i in nuran:
        query = "INSERT INTO images (keyword_id,url,type,chat_id,keyword_n) VALUES (%s,%s,%s,%s,%s)"
        image_type = 'TRUE' if nuran[i]['type'] == 'jpg' else 'FALSE'
        db.execute(query,(keyword_id,nuran[i]['url'],image_type,chat_id,keyword_n,))
