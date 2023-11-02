import json
import os


class SaiAttrsJsonLogger:

    used_attrs_json = dict()

    @classmethod
    def dump(cls, log_path=None) -> None:
        log_file_path = log_path or os.path.join(os.path.dirname(os.path.realpath(__file__)), 'tests', 'sai_attrs.json')
        with open(log_file_path, '+w') as log_fp:
            json.dump(cls.used_attrs_json, log_fp, indent=4)
    
    @classmethod
    def insert_attr_use(cls, obj_type, attr_name, oper):
        test_name = os.environ.get('PYTEST_CURRENT_TEST').split(':')[-1].split(' ')[0]
        cls.used_attrs_json[obj_type] = cls.used_attrs_json.get(obj_type, None) or dict()
        cls.used_attrs_json[obj_type][oper] = cls.used_attrs_json[obj_type].get(oper, None) or dict()
        cls.used_attrs_json[obj_type][oper][attr_name] = cls.used_attrs_json[obj_type][oper].get(attr_name, None) or dict()
        cls.used_attrs_json[obj_type][oper][attr_name][test_name] = "passed"
    
    @classmethod
    def update_test_result(cls, cur_test_name, result):
        for obj_type in cls.used_attrs_json:
            for oper in cls.used_attrs_json[obj_type]:
                for attr_name in cls.used_attrs_json[obj_type][oper]:
                    for test_name in cls.used_attrs_json[obj_type][oper][attr_name]:
                        if test_name == cur_test_name:
                            cls.used_attrs_json[obj_type][oper][attr_name][test_name] = result

