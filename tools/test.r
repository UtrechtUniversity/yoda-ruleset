check {
        writeLine("stdout","start");
        uuTest("0", *batch, *pause, *delay);
        writeLine("stdout","stop");
}

input *batch="256", *pause="0.5", *delay="60"
output ruleExecOut

