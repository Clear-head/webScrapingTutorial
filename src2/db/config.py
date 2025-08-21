import json
import os



class DbConfig:
    def __init__(self):
        self.BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.PATH = os.path.join(self.BASE_DIR, 'resource', 'db_config.json')
        self.host, self.port = self.read_config()

    def read_config(self):
        json_path = self.PATH

        with open(json_path) as f:
            config = json.load(f)
            self.host = str(config["redis"]["host"])
            self.port = int(config["redis"]["port"])
        return self.host, self.port

    def get_config(self):
        return self.host, self.port