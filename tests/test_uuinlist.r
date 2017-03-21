test {
	writeLine("stdout", uuinlist(*str, STRLIST));
	writeLine("stdout", uuinlist(*num, NUMLIST));
}

STRLIST = list("This", "is", "a", "test");
NUMLIST = list(1, 2, 3, 4);

input *str="test", *num=3
output ruleExecOut
