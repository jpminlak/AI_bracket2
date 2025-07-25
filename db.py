import pymysql
from pymysql import Error
class Database:
    def __init__(self):
        self.connection=None
        try:
            self.connection = pymysql.connect(
                host='svc.sel5.cloudtype.app',
                port=30522,
                database='test',
                user='root',
                password='1234',
                charset='utf8mb4',
                cursorclass=pymysql.cursors.DictCursor
            )
        except Error as e:
            print(f"DB 연결 실패: {e}")
            
    def save_weather_record(self,weather,temperature,clothes,region):
        try:
            with self.connection.cursor() as cursor:
                query="""
                INSERT INTO weather_record(weather,temperature,clothes,region) 
                VALUES(%s,%s,%s,%s)
                """
                cursor.execute(query,(weather,temperature,clothes,region))
                print("저장 성공")
        except Error as e:
            print(e)
    
    def get_weather_record(self):
        try:
            with self.connection.cursor() as cursor:
                query="""
                SELECT * FROM weather_record
                ORDER BY created_at DESC
                """
                cursor.execute(query)
                records=cursor.fetchall()
            return records
        except  Error as e:
            print(e)
            return []
    
    def get_region(self,city):
        try:
            with self.connection.cursor() as cursor:
                query="""
                SELECT * FROM region WHERE name = %s
                """
                cursor.execute(query,(city))
                records=cursor.fetchone()
            return records
        except  Error as e:
            print(e)
            return []
   
    def clothes(self,tem):
        try:
            with self.connection.cursor() as cursor:
                query="""
                SELECT clothes FROM temclo WHERE min_temp <= %s AND max_temp >= %s
                """
                cursor.execute(query,(tem,tem))
                records=cursor.fetchone()
                c=str(records['clothes'])
            return c
        except  Error as e:
            print(e)
            return []
    
    def close(self):
        if self.connection:
            self.connection.close()
            print("DB 연결종료")
    