import json
from sai import Sai


class SaiPhy(Sai):

    def __init__(self, exec_params):
        super().__init__(exec_params)
        # TODO:
