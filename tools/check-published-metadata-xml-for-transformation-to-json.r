check {
        writeLine("serverLog", "[METADATA] Start updating published metadata.xml to JSON format and place into moai folder");

        iiGetPublicationConfig(*publicationConfig);

        *publicHost = *publicationConfig.publicHost;
        *yodaInstance = *publicationConfig.yodaInstance;
        *yodaPrefix = *publicationConfig.yodaPrefix;

        iiCheckPublishedMetadataXmlForTransformationToJson("0", *batch, *pause, *delay, *publicHost, *yodaInstance, *yodaPrefix);
}

input *batch="256", *pause="0.5", *delay="60"
output ruleExecOut

