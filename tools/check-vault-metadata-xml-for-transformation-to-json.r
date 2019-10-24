check {
        writeLine("serverLog", "[METADATA] Start updating vault metadata.xml to JSON format");
        iiCheckVaultMetadataXmlForTransformationToJson("0", *batch, *pause, *delay);
}

input *batch="256", *pause="0.5", *delay="60"
output ruleExecOut

