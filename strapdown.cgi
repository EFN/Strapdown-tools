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

sub trim {
  my $res=$_[0];
  $res=~s/^\s+|\s+$//g;
  return $res;
}

sub logg {
  if ($vars{'logfile'}) {
    if ($_[0]>=$logLevel) {
      say LOG dbgLevel2String($_[0]).": ".$_[1];
    }
  }
}

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

#TODO: Add lang variable, perhaps some automation:
#http://search.cpan.org/~ambs/Lingua-Identify-0.56/lib/Lingua/Identify.pm

%vars=(
       'caching' => undef,
       'debug' => undef,
       'help' => undef,
       'logfile' => undef,
       'loglevel' => undef,
       'preload' => undef,
       'raw' => undef,
       'scriptbase' => '//bits.efn.no',
       'theme' => undef,
       'title' => undef,
      );

%can_override=(
       'debug' => 'b',
       'help' => 'b',
       'preload' => 'b',
       'raw' => 'b',
       'theme' => 's',
       'title' => 's',
	      );

%helpstr=(
       'caching' => 'Caching enabled. Default __on__.',
       'debug' => 'Show a list of debug variables. Default __off__.',
       'help' => 'Show this help text. Default __off__.',
       'logfile' => 'Log destination file. Default *None*.',
       'logfile' => 'Log level. Available values are `DEBUG` and `INFO`. Default `INFO`.',
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

%params;
foreach (split('&', $ENV{'QUERY_STRING'})) {
  (my $key, my $value)=split('=',$_);
  if ($can_override{$key} eq 'b') {
    $params{$key}=($value)?"1":"0";
  }
  else {
    $params{$key}=$value;
  }
}

$QSTRING="";
foreach (sort keys %params) {
  if ($can_override{$_}) {
    $vars{$_}=$params{$_};
    $QSTRING.="&" if ($QSTRING);
    $QSTRING.=sprintf("%s=%s",$_,$params{$_});
  }
}

if ($QSTRING ne $ENV{'QUERY_STRING'}) {
  #print "Status: 307 Temporary Redirect\n";
  print "Status: 308 Permanent Redirect\n";
  printf "Cache-Control: max-age=%d\n", 7*24*60*60;
  printf "Location: %s?%s\n", $ENV{'REDIRECT_URL'}, $QSTRING;
  print "Content-type: text/plain\n";
  print "\n";
  print "Normalizing URL\n";
  exit(0);
}

use constant {
 DEBUG => 1,
 INFO => 2,
};

if ($vars{'loglevel'}) {
  $logLevel=string2DbgLevel($vars{'loglevel'});
  if (!$logLevel) {
    error("# invalid value for 'loglevel':".$vars{'loglevel'});
  }
}
else {
  $logLevel=INFO;
}

if ($vars{'logfile'}) {
  open(LOG, '>>', $vars{'logfile'}) || die;
  logg INFO, "Start logging";
  logg INFO, "Loglevel is: ".dbgLevel2String($logLevel);
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

  log DEBUG, "Caching is defined as ".$vars->{'caching'};
  my $cache=(! defined($vars->{'caching'})) || str2bool($vars->{'caching'});
  logg DEBUG, "Caching: ".$cache;
  $lmTime=undef if (! $cache);

  return "Content-type: text/plain
${lmTime}

${body}
";
}

sub createPage {
  my $body=shift;
  my $vars=shift;
  logg DEBUG, "raw value is: '". $vars->{'raw'}."'";
  if (str2bool($vars->{'raw'})) {
    return createRaw($body, $vars);
  }

  if (! $vars->{'title'}) {
    ($vars->{'title'})=$ENV{'PATH_INFO'}=~/([^\/]+)$/;
  }
  if (! $vars->{'theme'}) {
    ($vars->{'theme'})='efn';
  }

  logg DEBUG, "Caching is defined as ".$vars->{'caching'};
  my $cache=(! defined($vars->{'caching'})) || str2bool($vars->{'caching'});
  logg DEBUG, "Caching: ".$cache;
  $lmTime=undef if (! $cache);
  my $scriptbase=$vars->{'scriptbase'};
  my $theme=$vars->{'theme'};
  my $preload="";
  if ((! defined($vars->{'preload'})) || str2bool($vars->{'preload'})) {
    $preload="  <link rel=\"stylesheet\" href=\"${scriptbase}/v/0.3/strapdown.css\" as=\"style\">
  <link rel=\"stylesheet\" href=\"${scriptbase}/v/0.3/themes/bootstrap-responsive.min.css\" as=\"style\">
  <link rel=\"stylesheet\" href=\"${scriptbase}/v/0.3/themes/${theme}.min.css\" as=\"style\">
";
    #$preload.="<style>.navbar{display:none}</style>";

  }
  logg INFO, "PRELOAD: ".$preload;

  return "Content-type: text/html; charset=utf-8
${lmTime}

<!DOCTYPE html>
<html>
<head>
  <title>$vars->{'title'}</title>
${preload}
</head>
<textarea data-theme=\"${theme}\" style=\"display:none;\">
${body}
</textarea>
<script src=\"${scriptbase}/v/0.3/strapdown.js\"></script>
</html>
";
}

sub error {
  print "Status: 500 Internal server error\n";
  print createPage($_[0], {'scriptbase' => $vars{'scriptbase'}});
  exit(0);
}

sub dumpDict {
  my $headers=shift;
  my $dict=shift;
  my $dict2=shift;

  $km=length($headers->[0]);
  $vm=length($headers->[1]);
  $vm2=length($headers->[2]);
  foreach (keys %{$dict}) {
    my $l=length($_);
    $km=$l if ($l>$km);
    $l=length($dict->{$_});
    $vm=$l if ($l>$vm);
  }
  if ($dict2) {
    foreach (keys %{$dict}) {
      my $l=length($_);
      $l=length($dict2->{$_});
      $vm2=$l if ($l>$vm);
    }
  }
  my $text=sprintf("|%-${km}s|%-${vm}s",$headers->[0],$headers->[1]);
  if ($dict2) {
    $text.=sprintf("|%-${vm2}s",$headers->[2]);
  }
  $text.=sprintf("|\n");
  $text.="|";
  for ($i=0;$i<$km;$i++) {
    $text.="-";
  }
  $text.="|";
  for ($i=0;$i<$vm;$i++) {
    $text.="-";
  }
  if ($dict2) {
    $text.="|";
    for ($i=0;$i<$vm2;$i++) {
      $text.="-";
    }
  }
  $text.="|\n";
  foreach (sort keys %{$dict}) {
    $text.=sprintf("|%-${km}s|%-${vm}s",$_, $dict->{$_});
    if ($dict2) {
      $text.=sprintf("|%-${vm2}s",$dict2->{$_});
    }
    $text.="|\n";
  }

  return $text;
}

sub str2bool {
  my $value=shift;
  logg DEBUG, "str2bool: '${value}'";
  return 0 if (!$value);
  $value=lc $value;
  return 0 if ($value eq "false");
  return 0 if ($value eq "off");
  return 0 if ($value eq "disabled");
  return 0 if ($value eq "unset");
  logg DEBUG, "Returning true";
  return 1;
}

sub debug {
  my $text="#DEBUG\n\n";
  $text.="##Page variables\n\n";
  $text.=dumpDict(['Variable', 'Value', 'Can override'],\%vars, \%can_override);
  $text.="\n";
  $text.="##Server variables\n\n";
  $text.=dumpDict(['Variable', 'Value'],\%ENV);
  $text.="\n";
  $text.="##Other stuff\n\n";
  $whoami=`whoami`;
  chop($whoami);
  $text.=dumpDict(['Variable', 'Value'],
		  {
		   'whoami' => $whoami,
		   'cwd' => trim(`pwd`),
		  });

  my %pass=(%vars,( 'title' => 'DEBUG', 'caching' => false, 'debug' => undef));
  print createPage($text, \%pass);
  exit(0);
}

sub help {
  my $text="#HELP\n";
  $text.="##Page variables\n";
  $text.=dumpDict(['Variable', 'Explanation'],\%helpstr);
  my %pass=(%vars,( 'title' => 'HELP', 'caching' => false));
  print createPage($text, \%pass);
  exit(0);
}

sub dbgLevel2String {
 if ($_[0] == DEBUG) {
   return "DEBUG";
 }
 elsif ($_[0] == INFO) {
   return "INFO";
 }
}

sub string2DbgLevel {
 my $str=uc $_[0];
 if ($str eq 'DEBUG') {
   return DEBUG;
 }
 elsif ($str eq 'INFO') {
   return INFO;
 }
 return undef;
}
