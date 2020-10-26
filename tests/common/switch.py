import redis
import time

class Sai:

    attempts = 40

    def __init__(self):
        self.r = redis.Redis(db=1)


    def alloc_vid(self):
        pass

    def operate(self, obj, attrs, op):
        self.r.delete("GETRESPONSE_KEY_VALUE_OP_QUEUE")

        status1 = []
        attempt = 0
        while len(self.r.lrange("GETRESPONSE_KEY_VALUE_OP_QUEUE", 0, -1)) > 0 and attempt < self.attempts:
            time.sleep(0.05)
            attempt += 1

        if attempt == self.attempts:
            return []

        self.r.lpush("ASIC_STATE_KEY_VALUE_OP_QUEUE", obj, attrs, op)
        self.r.publish("ASIC_STATE_CHANNEL", "G")

        status = []
        attempt = 0
        while len(status) < 3 and attempt < self.attempts:
            time.sleep(0.05)
            attempt += 1
            status = self.r.lrange("GETRESPONSE_KEY_VALUE_OP_QUEUE", 0, -1)

        self.r.delete("GETRESPONSE_KEY_VALUE_OP_QUEUE")

        return status

    def create(self, obj, attrs):
        return self.operate(obj, attrs, "Screate")

    def remove(self, obj):
        return self.operate(obj, "{}", "Dremove")

    def set(self, obj, attr):
        return self.operate(obj, attr, "Sset")

    def get(self, obj, attrs):
        return self.operate(obj, attrs, "Sget")


