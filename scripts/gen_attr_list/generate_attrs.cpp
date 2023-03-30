#include <iostream>
#include <saimetadata.h>
#include <algorithm>
#include <json.hpp>

constexpr const char *const undefined = "undefined";

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

    if (result == "bool" || result == "macsec_sci")
    {
        json["type"] = "bool";
    }
    else if (result == "macsec_ssci")
    {
        json["type"] = "sai_uint32_t";
    }
    else if (result == "chardata")
    {
        json["type"] = "char";
    }
    else if (result == "int32_list")
    {
        json["type"] = "sai_s32_list_t";
    }
    else if (result == "uint32_list")
    {
        json["type"] = "sai_u32_list_t";
    }
    else if (result == "int8_list")
    {
        json["type"] = "sai_s8_list_t";
    }
    else if (result == "uint8_list")
    {
        json["type"] = "sai_u8_list_t";
    }
    else if (result == "int16_list")
    {
        json["type"] = "sai_s16_list_t";
    }
    else if (result == "uint16_list")
    {
        json["type"] = "sai_u16_list_t";
    }
    else if (result == "int32_range")
    {
        json["type"] = "sai_s32_range_t";
    }
    else if (result == "uint32_range")
    {
        json["type"] = "sai_u32_range_t";
    }
    else if (result == undefined)
    {
        json["type"] = undefined;
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

    return json;
}

nlohmann::json attribute(const sai_object_type_info_t *obj_type_info)
{
    nlohmann::json obj_info;
    for (size_t index = 0; index < obj_type_info->attrmetadatalength; index++)
    {
        obj_info.push_back(nlohmann::json{
            { "name", obj_type_info->attrmetadata[index]->attridname },
            { "properties", attribute_properties(obj_type_info->attrmetadata[index]) } });
    }

    return obj_info;
}

nlohmann::json enums(const sai_object_type_info_t *obj_type_info)
{
    nlohmann::json j;
    auto pname = (*obj_type_info).enummetadata->valuesnames;
    auto pvalue = (*obj_type_info).enummetadata->values;
    while (*pname)
    {
        j[*pname] = *pvalue;
        pname++;
        pvalue++;
    }

    return j;
}

int main()
{
    nlohmann::json json;
    const sai_object_type_info_t *const *obj_type_info = sai_metadata_all_object_type_infos;
    std::string enum_list;
    while (*(++obj_type_info))
    {
        json.push_back(nlohmann::json{
            { "name", (*obj_type_info)->objecttypename },
            { "description", description((*obj_type_info)->objecttypename) },
            { "attributes", attribute(*obj_type_info) },
            { "enums", enums(*obj_type_info) } });
        enum_list.clear();
    }
    std::cout << json.dump() << std::endl;
    return 0;
}
