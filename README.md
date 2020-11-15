# sai-challenger
SAI testing infrastructure that is based on SONiC sairedis project

```sh
git clone https://github.com/andriy-kokhan/sai-challenger.git
cd sai-challenger/
git submodule update --init --recursive
```

## To build sai-challenger
```sh
docker build -f Dockerfile.sai -t sai-challenger .
docker build -f Dockerfile.saivs -t saivs-challenger .
```

## To run sai-challenger
```sh
docker run --name sai-challenger-run \
	-v $(pwd):/sai-challenger \
	--cap-add=NET_ADMIN \
	--device /dev/net/tun:/dev/net/tun \
	-d sai-challenger

docker exec -ti sai-challenger-run bash
```

## SAI operation
When Orchagent creates new SAI object, it actually performs two operations on Redis DB:
1. Enqueue SAI object create operation through LPUSH (in fact, Redis linked list object
   is used as an queue to pass SAI object data between Orchagent and Syncd);
2. Inform Syncd about new data in the linked list through PUBLISH operation;

```sh
    /*
     * KEYS[1] : tableName + "_KEY_VALUE_OP_QUEUE
     * ARGV[1] : key
     * ARGV[2] : value
     * ARGV[3] : op
     * KEYS[2] : tableName + "_CHANNEL"
     * ARGV[4] : "G"
     */
    string luaEnque =
        "redis.call('LPUSH', KEYS[1], ARGV[1], ARGV[2], ARGV[3]);"
        "redis.call('PUBLISH', KEYS[2], ARGV[4]);";
```

Where 'op' string consists of two parts: DB operation ("S" - set, "D" - delete) and
SAI operation ("create", "notify", "set", etc);

Both orchagent and syncd use VIDCOUNTER to generate new VID values.

```sh
/*
 * Current VID format:
 *
 * bits 63..56 - switch index
 * bits 55..48 - SAI object type
 * bits 47..40 - global context
 * bits 40..0  - object index
 */
```
For more information, please refer to VirtualObjectIdManager::allocateNewObjectId() located in:
sonic-sairedis/lib/src/VirtualObjectIdManager.cpp


### Example:

#### Create SAI object request
```sh
LPUSH ASIC_STATE_KEY_VALUE_OP_QUEUE "SAI_OBJECT_TYPE_SWITCH:oid:0x21000000000000" '["SAI_SWITCH_ATTR_INIT_SWITCH","true","SAI_SWITCH_ATTR_SRC_MAC_ADDRESS","52:54:00:EE:BB:70"]' Screate
PUBLISH  ASIC_STATE_CHANNEL  G
```

#### Retrieve SAI object create responce
```sh
redis-cli -n 1 LRANGE GETRESPONSE_KEY_VALUE_OP_QUEUE 0 -1
redis-cli -n 1 DEL GETRESPONSE_KEY_VALUE_OP_QUEUE
```

##### Expected output of previous command
```sh
1) "Sgetresponse"
2) "[]"
3) "SAI_STATUS_SUCCESS"
```

#### Get SAI object's attribute request
```sh
LPUSH ASIC_STATE_KEY_VALUE_OP_QUEUE "SAI_OBJECT_TYPE_SWITCH:oid:0x21000000000000" '["SAI_SWITCH_ATTR_DEFAULT_VIRTUAL_ROUTER_ID","oid:0x0"]' Sget
PUBLISH  ASIC_STATE_CHANNEL  G
```

#### Retrieve SAI object's attribute get responce
```sh
redis-cli -n 1 LRANGE GETRESPONSE_KEY_VALUE_OP_QUEUE 0 -1
redis-cli -n 1 DEL GETRESPONSE_KEY_VALUE_OP_QUEUE
```

##### Expected output of previous command
```sh
1) "Sgetresponse"
2) "[\"SAI_SWITCH_ATTR_DEFAULT_VIRTUAL_ROUTER_ID\",\"oid:0x3000000000022\"]"
3) "SAI_STATUS_SUCCESS"
```

