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

our $logLevel;

my @module = ("use File::stat;","use Date::Format","use Date::Parse qw(str2time)","use YAML::XS;", "use YAML::XS 'LoadFile';");
for (@module) {
  eval;
  if ($@) {
    $_=~/\w+\W(\S+)/;
    prefail("$1");
  }
}
;

use File::stat;

my $fName=$ENV{'PATH_INFO'};
my $lName=$ENV{'PATH_TRANSLATED'};

my $mtime = stat($lName)->mtime;

our $lmTime=time2str("Last-Modified: %a, %d %b %Y %H:%M:%S GMT", $mtime, "GMT");

#Short circuit if we have an IF_MODIFIED_SINCE
if ( $ENV{'HTTP_IF_MODIFIED_SINCE'} ) {
  my $if_m = str2time( $ENV{'HTTP_IF_MODIFIED_SINCE'} );
  if ($mtime <= $if_m) {
    print "Status: 304 Not Modified
Last-modified: ${lmTime}

";
    exit(0);
  }
}

#TODO: Add lang variable, perhaps some automation:
#http://search.cpan.org/~ambs/Lingua-Identify-0.56/lib/Lingua/Identify.pm

our %CanOverride;
our %PageVars=(
       'caching' => undef,
       'debug' => undef,
       'help' => undef,
       'logfile' => undef,
       'loglevel' => undef,
       'preload' => undef,
       'raw' => undef,
       'scriptbase' => '//bits.efn.no',
       'shortcuticon' => undef,
       'theme' => undef,
       'title' => undef,
      );

our %Helpstr=(
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

sub logg {
  if ($PageVars{'logfile'}) {
    if ($_[0]>=$logLevel) {
      say LOGFILE dbgLevel2String($_[0]).": ".$_[1];
    }
  }
}

my ($suffix)=$fName=~/\.([^.]+)$/;

our $hasSiteConf = 0;
if ( -f "strapdown.conf") {
  $hasSiteConf=1;
  my $settings = LoadFile("strapdown.conf");
  transferValidVars(\%PageVars, $settings->{'PageVars'});
  transferValidVars(\%CanOverride, $settings->{'CanOverride'}, \%PageVars);
}

open(CONTENT,"<$lName");
if ($suffix eq "mdh" ) {
  my $headers='';
  while (my $line=<CONTENT>) {
    $headers.=$line;
    last if ($line eq "...\n" );
  }
  my $settings = Load($headers);
  transferValidVars(\%PageVars, $settings);
}

my ($params, $canCache)=normalizeQuery($ENV{'QUERY_STRING'},\%CanOverride);

my $QSTRING=qstringFromParams($params);

if ($QSTRING ne $ENV{'QUERY_STRING'}) {
  #print "Status: 307 Temporary Redirect\n";
  print "Status: 308 Permanent Redirect\n";
  printf "Cache-Control: max-age=%d\n", ($canCache)?7*24*60*60:5;
  printf "Location: %s%s\n", $ENV{'REDIRECT_URL'}, ($QSTRING)?'?'.$QSTRING:'';
  print "Content-type: text/plain\n";
  print "\n";
  print "Normalizing URL\n";
  exit(0);
}
use constant {
	      DEBUG => 1,
	      INFO => 2,
	     };

if ($PageVars{'loglevel'}) {
  $logLevel=string2DbgLevel($PageVars{'loglevel'});
  if (!$logLevel) {
    error("# invalid value for 'loglevel':".$PageVars{'loglevel'});
  }
} else {
  $logLevel=INFO;
}

if ($PageVars{'logfile'}) {
  open(LOGFILE, '>>', $PageVars{'logfile'}) || die;
  logg INFO, "Start logging";
  logg INFO, "Loglevel is: ".dbgLevel2String($logLevel);
}

local $/;
my $body.=<CONTENT>;
close(CONTENT);

debug() if (str2bool($PageVars{'debug'}));
help() if (str2bool($PageVars{'help'}));

print createPage($body,\%PageVars);

sub createRaw {
  my $body=shift;
  my $vars=shift;

  logg DEBUG, "Caching is defined as ".$vars->{'caching'};
  my $cache=(! defined($vars->{'caching'})) || str2bool($vars->{'caching'});
  logg DEBUG, "Caching: ".$cache;
  $lmTime='' if (! $cache);

  return "Content-type: text/plain
${lmTime}

${body}
";
}

sub createPage {
  my $body=shift;
  my $vars=shift;
  logg DEBUG, "raw value is: '". setAndTrue($vars->{'raw'})."'";
  if (str2bool($vars->{'raw'})) {
    return createRaw($body, $vars);
  }

  if (! $vars->{'title'}) {
    ($vars->{'title'})=$ENV{'PATH_INFO'}=~/([^\/]+)$/;
  }
  if (! $vars->{'theme'}) {
    ($vars->{'theme'})='readable';
  }

  logg DEBUG, "Caching is defined as ".$vars->{'caching'};
  my $cache=(! defined($vars->{'caching'})) || str2bool($vars->{'caching'});
  logg DEBUG, "Caching: ".$cache;
  $lmTime='' if (! $cache);
  my $scriptbase=$vars->{'scriptbase'};
  my $theme=$vars->{'theme'};
  my $preload="";
  my $shortcuticon;
  my $shortcuticon_type;
  if (defined($vars->{'shortcuticon'})) {
    if ($vars->{'shortcuticon'}=~/\.(\w\w\w)$/) {
      if ($1 eq 'svg') {
	$shortcuticon_type="image/svg+xml";
      } elsif ($1 eq 'ico') {
	$shortcuticon_type="image/x-icon";
      } elsif ($1 eq 'gif') {
	$shortcuticon_type="image/gif";
      } elsif ($1 eq 'png') {
	$shortcuticon_type="image/png";
      }

      if ($shortcuticon_type) {
	$shortcuticon='<link rel="icon" type="'.$shortcuticon_type.'" href="'.$vars->{'shortcuticon'}.'">';
      }
    }
  }
  my @styles=(
	   "${scriptbase}/v/0.3/strapdown.css",
	   "${scriptbase}/v/0.3/themes/bootstrap-responsive.min.css",
	   "${scriptbase}/v/0.3/themes/${theme}.min.css"
	  );
  my $linklist;
  if ((! defined($vars->{'preload'})) || str2bool($vars->{'preload'})) {
    foreach (@styles) {
      $linklist.="\n" if ($linklist);
      $linklist.='  <link rel="stylesheet" href="'.$_.'" as="style">';
    }
    $preload.="${linklist}";
    #$preload.="<style>.navbar{display:none}</style>";
  }
  if ( $ENV{'H2_PUSH'}) {
    my @scripts=(
	      "${scriptbase}/v/0.3/strapdown.js"
	     );
    $linklist='';
    foreach (@styles) {
      $linklist.=', ' if ($linklist);
      $linklist.='<'.$_.'>;rel=preload;as=style;crossorigin';
    }
    foreach (@scripts) {
      $linklist.=', ' if ($linklist);
      $linklist.='<'.$_.'>;rel=preload;as=script;crossorigin';
    }
    print "link: ${linklist}\n";
  }
  $preload.="
  ${shortcuticon}
";
  logg INFO, "PRELOAD: ".$preload;

  my %redirTarget=(%$params);
  $redirTarget{'raw'}='1';
  my $redirectTarget='?'.qstringFromParams(\%redirTarget);

  my $metaredir='';
  if (setAndTrue($vars->{'raw'})) {
    $metaredir="<noscript>
  <meta http-equiv=\"refresh\" content=\"0; url=${redirectTarget}\">
</noscript>";
  }

  return "Content-type: text/html; charset=utf-8
${lmTime}

<!DOCTYPE html>
<html>
<head>
  <title>$vars->{'title'}</title>
${preload}
${metaredir}
</head>
<body>
<noscript>
<p>This site uses javascript to render properly. In case you don't have javascript. We tried to redirect you to the non-javascript version, but seem to have failed. Please refer to the same page with \"<a href=\"${redirectTarget}\">raw=1</a>\" appended</p>
</noscript>
<textarea data-theme=\"${theme}\" style=\"display:none;\">
${body}
</textarea>
<script src=\"${scriptbase}/v/0.3/strapdown.js\"></script>
</body>
</html>
";
}

sub error {
  print "Status: 500 Internal server error\n";
  print createPage($_[0], {'scriptbase' => $PageVars{'scriptbase'}});
  exit(0);
}

sub escape {
  return $_[0] if (!defined $_[0]);
  return $_[0]=~s/\*/\\\*/gr;
}

sub dumpDict {
  my $headers=shift;
  my $dict=shift;
  my $dict2=shift;

  my $km=length($headers->[0]);
  my $vm=length($headers->[1]);
  my $vm2=length($headers->[2]);
  foreach (keys %{$dict}) {
    my $l=length($_);
    $km=$l if ($l>$km);
    $l=(defined $dict->{$_})?length($dict->{$_}):0;
    $vm=$l if ($l>$vm);
  }
  if ($dict2) {
    foreach (keys %{$dict2}) {
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
  for (my $i=0;$i<$km;$i++) {
    $text.="-";
  }
  $text.="|";
  for (my $i=0;$i<$vm;$i++) {
    $text.="-";
  }
  if ($dict2) {
    $text.="|";
    for (my $i=0;$i<$vm2;$i++) {
      $text.="-";
    }
  }
  $text.="|\n";
  foreach (sort keys %{$dict}) {
    my $val1=escape($dict->{$_});
    $val1='' if (! defined $val1);
    $text.=sprintf("|%-${km}s|%-${vm}s",escape($_), $val1);
    if ($dict2) {
      my $val2=escape($dict2->{$_});
      $val2='' if (! defined $val2);
      $text.=sprintf("|%-${vm2}s", $val2);
    }
    $text.="|\n";
  }

  return $text;
}

sub str2bool {
  my $value=shift;
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
  $text.=dumpDict(['Variable', 'Value', 'Can override'],\%PageVars, \%CanOverride);
  $text.="\n";
  $text.="##Server variables\n\n";
  $text.=dumpDict(['Variable', 'Value'],\%ENV);
  $text.="\n";
  $text.="##Other stuff\n\n";
  my $whoami=`whoami`;
  chop($whoami);
  $text.=dumpDict(['Variable', 'Value'],
		  {
		   'whoami' => $whoami,
		   'cwd' => trim(`pwd`),
		   'hasSiteConf' => $hasSiteConf,
		  });

  my %pass=(%PageVars,( 'title' => 'DEBUG', 'caching' => 0, 'debug' => undef));
  print createPage($text, \%pass);
  exit(0);
}

sub help {
  my $text="#HELP\n";
  $text.="##Page variables\n";
  $text.=dumpDict(['Variable', 'Explanation'],\%Helpstr);
  my %pass=(%PageVars,( 'title' => 'HELP', 'caching' => 0));
  print createPage($text, \%pass);
  exit(0);
}

sub dbgLevel2String {
  if ($_[0] == DEBUG) {
    return "DEBUG";
  } elsif ($_[0] == INFO) {
    return "INFO";
  }
}

sub string2DbgLevel {
  my $str=uc $_[0];
  if ($str eq 'DEBUG') {
    return DEBUG;
  } elsif ($str eq 'INFO') {
    return INFO;
  }
  return undef;
}

sub transferValidVars {
  my ($dest, $source, $check) = @_;
  $check = $dest if (!$check);
  foreach my $key (keys %{$source}) {
    if (exists $check->{$key}) {
      $dest->{$key}=$source->{$key};
    } else {
      error("# undefined key '$key' used");
    }
  }
}

sub prefail {
  my $modfailure=$_[0];
  print "Status: 200 OK\n";
  print "Content-type: text/plain\n";
  print "\n";
  print "Module '${modfailure}' does not exist, please install it first!\n";

  exit(0);
}


sub trim {
  my $res=$_[0];
  $res=~s/^\s+|\s+$//g;
  return $res;
}

sub normalizeQuery {
  my $query=$_[0];
  my $can_override=$_[1];

  my $canCache=1;
  my %params;
  foreach (split('&', $query)) {
    (my $key, my $value)=split('=',$_);
    if ($can_override->{$key} eq 'b') {
      $params{$key}=($value)?"1":"0";
      $PageVars{$key}=$params{$key};
    } elsif ($can_override->{$key}) {
      $params{$key}=$value;
      $PageVars{$key}=$params{$key};
    } elsif (exists $PageVars{$key}) {
      $canCache=0;
    }
  }
  return (\%params, $canCache);
}

sub qstringFromParams {
  my $para=$_[0];
  my $nstring="";
  my $vars;
  foreach (sort keys %{$para}) {
    $nstring.="&" if ($nstring);
    $nstring.=sprintf("%s=%s",$_,$para->{$_});
  }
  return $nstring;
}

sub setAndTrue {
  my ($value) = @_;
  return (defined $value and $value);
}
