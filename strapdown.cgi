#!/usr/bin/perl
#
# To make apache render files ending with .md with strapdown.js
# markdown renderer (http://strapdownjs.com/), add following lines
# to /etc/apache2/httpd.conf:
#
#    Action markdown /cgi-bin/strapdown.cgi
#    AddHandler markdown .md .mdh
#    DirectoryIndex index.html index.md index.mdh
#
# then enable mod_actions by running "a2enmod actions" and store
# this script to cgi-bin directory as file strapdown.cgi.  Finally
# restart apache.
#

use File::stat;
use Date::Format;
use Date::Parse qw(str2time);

open(DEBUGLOG, '>>', '/tmp/pDebug.log') || die;
say DEBUGLOG "Session start";
$fName=$ENV{'PATH_INFO'};
$lName=$ENV{'PATH_TRANSLATED'};

$mtime = stat($lName)->mtime;

$lmTime=time2str("Last-Modified: %a, %d %b %Y %H:%M:%S GMT", $mtime, "GMT");

#Short circuit if we have an IF_MODIFIED_SINCE
if ( $ENV{'HTTP_IF_MODIFIED_SINCE'} ) {
  $if_m = str2time( $ENV{'HTTP_IF_MODIFIED_SINCE'} );
  if ($mtime <= $if_m) {
    print "Status: 304 Not Modified
Last-modified: ${lmTime}

";
    exit(0);
  }
}


%vars=(
       'caching' => undef,
       'debug' => undef,
       'help' => undef,
       'preload' => undef,
       'raw' => undef,
       'scriptbase' => '//bits.efn.no',
       'theme' => undef,
       'title' => undef,
);
%helpstr=(
       'caching' => 'Caching enabled. Default __on__.',
       'debug' => 'Show a list of debug variables. Default __off__.',
       'help' => 'Show this help text. Default __off__.',
       'preload' => 'Uses static knowledge of `strapdown.js` to speed up page loading. Default __on__',
       'raw' => 'Display the raw *Markdown*. Default __off__.',
       'scriptbase' => 'Where all the scripts are located. Default `//bits.efn.no`. This will probably change in the future',
       'theme' => 'The CSS-styles to be appied to this document. Default __`noheader`__. Other examples are `amelia`,`bootstrap`,`bootstrap-responsive`,`cerulean`,`cyborg`,`journal`,`readable`,`simplex`,`slate`,`spacelab`,`spruce`,`superhero`,`united`',
       'title' => 'The HTML title of this document. Default __name of the file__',
);

($suffix)=$fName=~/\.([^.]+)$/;

open(CONTENT,"<$lName");
if ($suffix eq "mdh" )
{
  while (($line=<CONTENT>) && (($key,$value)=$line=~/([^:]+):(.*)/) ) {
    if (exists $vars{$key}) {
      $vars{$key}=$value;
    }
    else {
      error("# undefined key '$key' used");
    }
  }
  $body=$line;
}
local $/;
$body.=<CONTENT>;
close(CONTENT);

debug() if (str2bool($vars{'debug'}));
help() if (str2bool($vars{'help'}));
  
print createPage($body,\%vars);

sub createRaw {
  my $body=shift;
  my $vars=shift;

  say DEBUGLOG "Caching is defined as ".$vars->{'caching'};
  my $cache=(! defined($vars->{'caching'})) || str2bool($vars->{'caching'});
  say DEBUGLOG "Caching: ".$cache;
  $lmTime=undef if (! $cache);

  return "Content-type: text/plain
${lmTime}

${body}
";
}

sub createPage {
  my $body=shift;
  my $vars=shift;
  say DEBUGLOG "RAW:". $vars->{'raw'};
  if (str2bool($vars->{'raw'})) {
    return createRaw($body, $vars);
  }

  if (! $vars->{'title'}) {
    ($vars->{'title'})=$ENV{'PATH_INFO'}=~/([^\/]+)$/;
  }
  if (! $vars->{'theme'}) {
    ($vars->{'theme'})='efn';
  }

  say DEBUGLOG "Caching is defined as ".$vars->{'caching'};
  my $cache=(! defined($vars->{'caching'})) || str2bool($vars->{'caching'});
  say DEBUGLOG "Caching: ".$cache;
  $lmTime=undef if (! $cache);
  my $scriptbase=$vars->{'scriptbase'};
  my $theme=$vars->{'theme'};
  my $preload="";
  if ((! defined($vars->{'preload'})) || str2bool($vars->{'preload'})) {
    $preload="  <link rel=\"stylesheet\" href=\"${scriptbase}/v/0.2/strapdown.css\" as=\"style\">
  <link rel=\"stylesheet\" href=\"${scriptbase}/v/0.2/themes/bootstrap-responsive.min.css\" as=\"style\">
  <link rel=\"stylesheet\" href=\"${scriptbase}/v/0.2/themes/${theme}.min.css\" as=\"style\">
";
    #$preload.="<style>.navbar{display:none}</style>";

  }
  say DEBUGLOG $preload;
  say DEBUGLOG "hei";
  return "Content-type: text/html
${lmTime}

<!DOCTYPE html>
<html>
<head>
  <title>$vars->{'title'}</title>
${preload}
</head>
<xmp theme=\"${theme}\" style=\"display:none;\">
${body}
</xmp>
<script src=\"${scriptbase}/v/0.2/strapdown.js\"></script>
</html>
";
}

sub error {
  print "Status: 500 Internal server error\n";
  print createPage($_[0], {'scriptbase' => $vars{'scriptbase'}});
  exit(0);
}

sub dumpDict {
  my $dict=shift;

  $km=length("VARIABLE");
  $vm=length("VALUE");
  foreach (keys %{$dict}) {
    my $l=length($_);
    $km=$l if ($l>$km);
    $l=length($dict->{$_});
    $vm=$l if ($l>$vm);
  }
  my $text=sprintf("|%-${km}s|%-${vm}s|\n","VARIABLE", "VALUE");
  $text.="|";
  for ($i=0;$i<$km;$i++) {
    $text.="-";
  }
  $text.="|";
  for ($i=0;$i<$vm;$i++) {
    $text.="-";
  }
  $text.="|\n";
  foreach (sort keys %{$dict}) {
    $text.=sprintf("|%-${km}s|%-${vm}s|\n",$_, $dict->{$_});
  }

  return $text;
}

sub str2bool {
  my $value=shift;
  say DEBUGLOG "str2bool";
  say DEBUGLOG $value;
  return 0 if (!$value);
  $value=lc $value;
  return 0 if ($value eq "false");
  return 0 if ($value eq "off");
  return 0 if ($value eq "disabled");
  return 0 if ($value eq "unset");
  say DEBUGLOG "Returning true";
  return 1;
}

sub debug {
  my $text="#DEBUG\n\n";
  $text.="##Page variables\n\n";
  $text.=dumpDict(\%vars);
  $text.="\n";
  $text.="##Server variables\n\n";
  $text.=dumpDict(\%ENV);
  $text.="\n";
  $text.="##Other stuff\n\n";
  $whoami=`whoami`;
  chop($whoami);
  $text.=dumpDict(
		  {
		   'whoami' => $whoami,
		   'cwd' => `pwd`,
		  });
  
  print createPage($text, { 'title' => 'DEBUG', 'caching' => false, 'scriptbase' => $vars{'scriptbase'}});
  exit(0);
}

sub help {
  my $text="#HELP\n";
  $text.="##Page variables\n";
  $text.=dumpDict(\%helpstr);
  print createPage($text, { 'title' => 'HELP', 'caching' => false, 'scriptbase' => $vars{'scriptbase'} });
  exit(0);
}
