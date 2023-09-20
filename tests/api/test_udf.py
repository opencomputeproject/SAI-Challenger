from pprint import pprint
import pytest


@pytest.fixture(scope='module', autouse=True)
def skip_all(testbed_instance):
    testbed = testbed_instance
    if testbed is not None and len(testbed.npu) != 1:
        pytest.skip('invalid for {} testbed'.format(testbed.name))

@pytest.mark.npu
class TestSaiUdf:
    # object with parent SAI_OBJECT_TYPE_UDF_MATCH SAI_OBJECT_TYPE_UDF_GROUP

    def test_udf_create(self, npu):
        commands = [
            {
                'name': 'udf_match_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_UDF_MATCH',
                'attributes': [],
            },
            {
                'name': 'udf_group_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_UDF_GROUP',
                'attributes': ['SAI_UDF_GROUP_ATTR_LENGTH', '10'],
            },
            {
                'name': 'udf_1',
                'op': 'create',
                'type': 'SAI_OBJECT_TYPE_UDF',
                'attributes': [
                    'SAI_UDF_ATTR_MATCH_ID',
                    '$udf_match_1',
                    'SAI_UDF_ATTR_GROUP_ID',
                    '$udf_group_1',
                    'SAI_UDF_ATTR_OFFSET',
                    '10',
                ],
            },
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values create =======')
        pprint(results)

    @pytest.mark.dependency(name="test_sai_udf_attr_base_set")
    def test_sai_udf_attr_base_set(self, npu):

        commands = [
            {
                "name": "udf_1",
                "op": "set",
                "attributes": ["SAI_UDF_ATTR_BASE", 'SAI_UDF_BASE_L2']
            }
        ]
        results = [*npu.process_commands(commands)]
        print("======= SAI commands RETURN values set =======")
        pprint(results)



    @pytest.mark.dependency(depends=["test_sai_udf_attr_base_set"])
    def test_sai_udf_attr_base_get(self, npu):

        commands = [
            {
                "name": "udf_1",
                "op": "get",
                "attributes": ["SAI_UDF_ATTR_BASE"]
            }
        ]
        results = [*npu.process_commands(commands)]
        print("======= SAI commands RETURN values get =======")
        for command in results:
            for attribute in command:
                pprint(attribute.raw())
        r_value = results[0][0].value()
        print(r_value)
        assert r_value == 'SAI_UDF_BASE_L2', 'Get error, expected SAI_UDF_BASE_L2 but got %s' %  r_value


    def test_udf_remove(self, npu):
        commands = [
            {'name': 'udf_1', 'op': 'remove'},
            {'name': 'udf_group_1', 'op': 'remove'},
            {'name': 'udf_match_1', 'op': 'remove'},
        ]

        results = [*npu.process_commands(commands)]
        print('======= SAI commands RETURN values remove =======')
        pprint(results)
