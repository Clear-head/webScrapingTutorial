import redis
import pickle

HOST = "192.168.40.131"
PORT = 6379

def connect_redis():
    try:
        print(redis.__version__)
        r = redis.Redis(host=HOST, port=PORT)

        if r.ping():
            print()
            print("Redis Connected!")
            return r.get
        else:
            raise redis.ConnectionError("Fail to Ping")
    except redis.ConnectionError as e:
        print(e)
        print(f"Redis connect failed, Connection Error")
        return False
    
    except Exception as e:
        print(f"Redis connect failed, error code : {e}")
        return False
    

def insert_contents(driver, items):
    for item in items:
        ogj = pickle.dumps(items)

        
    pass


def get_contents():
    pass