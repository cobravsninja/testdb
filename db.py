import psycopg2
from time import time

class DB:
    ## host, credentials, etc.
    __username=__password=__dbname=__host=__port   = None

    def __init__(self,username,password,dbname,host,port=5432,timeout=3600):
        self.__username     = username
        self.__password     = password
        self.__dbname       = dbname
        self.__host         = host
        self.__port         = port
        self.__timeout      = timeout
        self.__close        = True

    def connect(self):
        try:
            self.__connection = psycopg2.connect("dbname='%s' user='%s' password='%s' host='%s' port=%d" % (self.__dbname,
                    self.__username, self.__password, self.__host, self.__port))
            self.__connection.set_session(autocommit=True)
            self.__connect_time = time()
            self.__close = False
        except Exception as e:
            print self.__host
            raise Exception(e)

    def close(self):
        self.__close = True
        self.__connection.close()

    def fetch_data(self,sql,params=()):
        return self.execute(sql,params,False)

    def fetch_one(self,sql,params=()):
        return self.execute(sql,params,False,False,1)

    def execute_out(self,sql,params=()):
        return self.execute(sql,params,True,True)

    def execute(self,sql,params=(),execute=True,out=False,one=None):
        try:
            if self.__close is True:
                raise Exception("not connected")

            if time() - self.__connect_time >= self.__timeout:
                print 'reconnecting...'
                self.close()
                self.connect()
            cur = self.__connection.cursor()
            cur.execute(sql , params)

            if execute is True:
                if out is True:
                    return cur.fetchone()[0]
                return

            if one is not None:
                return cur.fetchone()
            else:
                return cur.fetchall()
        except Exception as e:
            raise Exception(e)
