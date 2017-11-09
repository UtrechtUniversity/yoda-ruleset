testRule {

iiDatamanagerGroupFromVaultGroup(*vaultGroup, *datamanagerGroup);
writeLine("stdout", *datamanagerGroup);
}
input *vaultGroup=""
output ruleExecOut
