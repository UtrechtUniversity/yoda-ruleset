check {
        writeLine("serverLog", "[METADATA] Start updating published metadata.xml to JSON format and place into moai folder");

        iiGetPublicationConfig(*publicationConfig);

        iiCheckPublishedMetadataXmlForTransformationToJson("0", *batch, *pause, *delay);
}

input *batch="256", *pause="0.5", *delay="60"
output ruleExecOut

