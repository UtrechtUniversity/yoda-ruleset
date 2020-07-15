check {
        writeLine("serverLog", "[METADATA] Start updating published metadata.xml to JSON format and place into moai folder");

        iiGetPublicationConfig(*publicationConfig);

        *publicHost = *publicationConfig.publicHost;
        *yodaInstance = *publicationConfig.yodaInstance;
        *yodaPrefix = *publicationConfig.yodaPrefix;

        rule_published_xml_to_json_check_published_metadata_xml_for_transformation_to_json("0", *batch, *pause, *delay, *publicHost, *yodaInstance, *yodaPrefix);
}

input *batch="256", *pause="0.5", *delay="60"
output ruleExecOut

