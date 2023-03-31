#include <iostream>
#include <saimetadata.h>
#include <algorithm>
#include <json.hpp>
#include <map>

constexpr const char *const undefined = "undefined";

std::map<std::string,std::string> sai_types_map = {
   {"bool",         "bool"},
   {"macsec_sci",   "bool"},
   {"macsec_ssci",  "sai_uint32_t"},
   {"chardata",     "char"},
   {"int32_list",   "sai_s32_list_t"},
   {"uint32_list",  "sai_u32_list_t"},
   {"int16_list",   "sai_s16_list_t"},
   {"uint16_list",  "sai_u16_list_t"},
   {"int8_list",    "sai_s8_list_t"},
   {"uint8_list",   "sai_u8_list_t"},
   {"int32_range",  "sai_s32_range_t"},
   {"uint32_range", "sai_u32_range_t"},
   {undefined,      undefined}
};

void type_name(nlohmann::json &json, const char *const name);

const char *const short_type_name(size_t index)
{
    if (index >= 0 && index < sai_metadata_enum_sai_attr_value_type_t.valuescount)
    {
        return sai_metadata_enum_sai_attr_value_type_t.valuesshortnames[index];
    }
    return undefined;
}

void acl_type_name(nlohmann::json &json, const std::string &name, const std::string &pattern)
{
    std::string subtype = name.substr(
        pattern.length() + 1);
    type_name(json, subtype.c_str());
    json["genericType"] = json["type"];
    json["type"] = "sai_" + pattern + "_t";
}

void type_name(nlohmann::json &json, const char *const name)
{
    std::string result;
    std::for_each(name, std::next(name, strlen(name)), [&result](const char ch) {
        result += std::tolower(ch);
    });

    auto it = sai_types_map.find(result);
    if (it != sai_types_map.end())
    {
        json["type"] = it->second;
    }
    else if (result.find("acl_field_data") != std::string::npos)
    {
        acl_type_name(json, result, "acl_field_data");
    }
    else if (result.find("acl_action_data") != std::string::npos)
    {
        acl_type_name(json, result, "acl_action_data");
    }
    else
    {
        json["type"] = "sai_" + result + "_t";
    }
}

std::string description(const std::string &name)
{
    std::string result;
    std::for_each(name.begin(), name.end(), [&result](const char &ch) {
        result += (ch == '_') ? ' ' :
                                std::tolower(ch);
    });
    result += '.';
    return result;
}

nlohmann::json attribute_properties_flags(const sai_attr_metadata_t *meta)
{
    nlohmann::json flags;
    if (meta->ismandatoryoncreate)
        flags.push_back("MANDATORY_ON_CREATE");
    if (meta->iscreateonly)
        flags.push_back("CREATE_ONLY");
    if (meta->iscreateandset)
        flags.push_back("CREATE_AND_SET");
    if (meta->isreadonly)
        flags.push_back("READ_ONLY");
    if (meta->iskey)
        flags.push_back("KEY");
    return flags;
}

nlohmann::json enums(const sai_enum_metadata_t *meta)
{
    nlohmann::json j;
    for (size_t index = 0; index < meta->valuescount; index++)
    {
        auto name = meta->valuesnames[index];
        auto value = meta->values[index];
        j[name] = value;
    }

    return j;
}

nlohmann::json attribute_properties(const sai_attr_metadata_t *meta)
{
    nlohmann::json json{
        { "description", meta->brief },
        { "flags", attribute_properties_flags(meta) }
    };
    type_name(json, short_type_name(meta->attrvaluetype));
    std::string name = json["type"];
    if (!strcmp(name.c_str(), "sai_object_id_t") ||
        !strcmp(name.c_str(), "sai_object_list_t"))
    {
        const sai_object_type_t *const obj_list = meta->allowedobjecttypes;
        nlohmann::json j;
        for (size_t i = 0; i < meta->allowedobjecttypeslength; i++)
        {
            j.push_back(sai_metadata_all_object_type_infos[obj_list[i]]->objecttypename);
        }
        json["objects"] = j;
    }
    if (meta->isenum || meta->isenumlist)
    {
        json["values"] = enums(meta->enummetadata);
    }

    return json;
}

nlohmann::json attribute(const sai_object_type_info_t *obj_type_info)
{
    nlohmann::json obj_info;
    for (size_t index = 0; index < obj_type_info->attrmetadatalength; index++)
    {
        auto attr = obj_type_info->attrmetadata[index];
        obj_info.push_back(nlohmann::json{
            { "name", attr->attridname },
            { "properties", attribute_properties(attr) } });
    }

    return obj_info;
}

int main()
{
    nlohmann::json json;
    const sai_object_type_info_t *const *obj_type_info = sai_metadata_all_object_type_infos;
    while (*(++obj_type_info))
    {
        json.push_back(nlohmann::json{
            { "name", (*obj_type_info)->objecttypename },
            { "description", description((*obj_type_info)->objecttypename) },
            { "attributes", attribute(*obj_type_info) } });
    }
    std::cout << json.dump() << std::endl;
    return 0;
}
