#!/usr/bin/env perl

use 5.12.0;

# "API shell"
# easy wrapper for irule/uu api calling convention calls.
# with fancy output formatting if jq is installed.
#
# api> api_uu_ping {"foo": 42}

sub run {
    @_ or die "usage: $0 <api_name> [args_json={}]\n";
    my $api  = shift;
    my $json = @_ && length $_[0] ? join(' ', @_) : '{}';
    $json =~ s/%/%%/g;

    my $wri = sub { print @_ };

    my $jq; open $jq, '|-', 'jq .' and $wri = sub { print $jq @_ };

    open my $irule, '-|', "irule", "$api(*a)", "*a=$json", "ruleExecOut";
    $wri->($_) while (defined ($_ = <$irule>));
    close $irule;
    close $jq;
}

if (@ARGV) {
    run @ARGV;
    exit;
} else {
    use Term::ReadLine;

    my $term = new Term::ReadLine $0;
    while (defined ($_ = $term->readline('api> '))) {
        s/^\s*//; s/\s*$//;
        next unless length;
        run(/^(\S+)(?:\s*(.*))$/)
    }
}
