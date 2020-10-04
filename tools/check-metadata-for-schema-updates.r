check {
        writeLine("serverLog", "[METADATA] Start updating metadata.");
        rule_batch_transform_vault_metadata("0", *batch, *pause, *delay);
}

input *batch="256", *pause="0.5", *delay="60"
output ruleExecOut
