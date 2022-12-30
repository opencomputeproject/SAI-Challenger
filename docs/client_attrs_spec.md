# Attributes values format

Every client might have its specific attribute values representation. For example Redis representation of the `objlist` is a string like `"2:oid:0x1001,oid:0x1002"`. While Thrift represents `objlist` as `sai_thrift_object_list_t(count=2, idlist=[0x1001, 0x1002])`.

SaiClient must have some standart representation and all the implementations must convert all output attributes to this standard representation. Also they should expect all the input attributes in the same format.

In order to achieve a maximum level of abstraction currently a string format was used for SaiClient. Current implementation looks mostly like Redis format but not exactly. For example we are not using `oid:` prefix for OIDs.

An example of both kinds of convertions could be found in: `ThriftConverter.convert_attributes_to_thrift` and `ThriftConverter.convert_attributes_from_thrift`.

#### SAI types  with examples

There are some examples of how it is done in the current implementation:

##### Boolean:

`booldata` => "true", "false"

##### Strings:

`chardata` => "value"

##### Integers:
`s8`, `u8`, `s16`, `u16`, `s32`, `u32`, `s64`, `u64`, `ptr` => "1000"

##### OID:
`oid` => "0x10001"

##### IP:
`ipaddr` => "192.168.0.1", "2001::1"
`ip4` => "192.168.0.1"
`ip6` => "2001::1"
`ipaddrlist` => "2:192.168.0.1,192.168.0.2"
`ipprefix` => "192.168.0.0/24", "2001::/64"

##### MAC:

`mac` => "00:CC:CC:CC:CC:00"

#### Lists:

Lists format: "size:comma_separated_values":

##### Integer lists:

`s8list`, `u8list`, `s16list`, `u16list`, `s32list`, `u32list` => "2:10,20"

##### Object lists:

`objlist`, => "3:0x1001,0x1002,0x1003"

#### Other types:

**TODO**: Specification for other types should be added when we are ready to test them. I suggest looking at Redis format to cover these.

_aclaction, aclcapability, aclfield, aclresource, authkey, encrypt_key, latchstatus, macsecauthkey, macsecsak, macsecsalt, maplist, porterror, porteyevalues, portlanelatchstatuslist, qosmap, reachability, segmentlist, sysportconfig, sysportconfiglist, tlvlist, s32range, u32range, u16rangelist, rx_status, vlanlist_

