#!/usr/bin/env perl

use 5.12.0;
use warnings;

# Generates Python pep rule prototypes based on TAB-separated peps.sh output

sub snake {
    # camelCase -> snake_case
    shift =~ s/(?<=[a-z])([A-Z]+)/"_".lc $1/erg
}

while (<>) {
    chomp;
    my ($name, @argspec) = /(?|(^\S+)|\t([^\t]+))/g;
    unshift @argspec, "instance_name";
    @argspec = (@argspec[0,1], "out", @argspec[2..$#argspec])
        unless $name =~ /^api_/; # "out" injected only for non-api PEPs
    my $pargs = join ", ", "ctx", map {snake($argspec[$_]=~s/\s*:.*//r)||"_$_";} 0..$#argspec;

    print <<EOF;
\@policy.make_pep()
def pep_${name}_pre($pargs): return policy.succeed()
EOF
}
