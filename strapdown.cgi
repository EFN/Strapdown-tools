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

$fName=$ENV{'PATH_INFO'};
$lName=$ENV{'PATH_TRANSLATED'};

%vars=(
  'title' => undef,
  'theme' => undef
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

createPage($body,%vars);

sub createPage {
  my $body=$_[0];
  if (! $vars{'title'}) {
    ($vars{'title'})=$ENV{'PATH_INFO'}=~/([^\/]+)$/;
  }
  if (! $vars{'theme'}) {
    ($vars{'theme'})='noheader';
  }

  print "Content-type: text/html

<!DOCTYPE html>
<html>
<title>$vars{'title'}</title>
<xmp theme=\"$vars{'theme'}\" style=\"display:none;\">
${body}
</xmp>
<script src=\"//bits.efn.no/v/0.2/strapdown.js\"></script>
</html>
";
}

sub error {
  print "Status: 500 Internal server error\n";
  createPage($_[0]);
  exit(0);
}
