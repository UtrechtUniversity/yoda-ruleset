check {
        writeLine("serverLog", "[METADATA] Start updating vault metadata.xml to JSON format");
        rule_vault_xml_to_json_check_vault_metadata_xml_for_transformation_to_json("0", *batch, *pause, *delay);
}

input *batch="256", *pause="0.5", *delay="60"
output ruleExecOut

