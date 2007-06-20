#!/usr/local/bin/perl
# domain_form.cgi
# Display a form for setting up a new virtual domain

require './virtual-server-lib.pl';
&ReadParse();

if ($in{'import'}) {
	# Redirect to the import form
	&redirect("import_form.cgi");
	return;
	}
elsif ($in{'migrate'}) {
	# Redirect to the migration form
	&redirect("migrate_form.cgi");
	return;
	}
elsif ($in{'batch'}) {
	# Redirect to the batch creation
	&redirect("mass_create_form.cgi");
	return;
	}
elsif ($in{'delete'}) {
	# Redirect to the mass server deletion form
	@d = split(/\0/, $in{'d'});
	&redirect("mass_delete_domains.cgi?".join("&", map { "d=$_" } @d));
	return;
	}
elsif ($in{'mass'}) {
	# Redirect to the mass server update form
	@d = split(/\0/, $in{'d'});
	&redirect("mass_domains_form.cgi?".join("&", map { "d=$_" } @d));
	return;
	}

# Can this user even create servers?
&can_create_master_servers() || &can_create_sub_servers() ||
	&error($text{'form_ecannot'});

# If we are in generic mode, work out all possible modes for the current user
if ($in{'generic'}) {
	$gparent = &get_domain($in{'gparent'}) if ($in{'gparent'});
	if (&can_create_master_servers()) {
		# Top-level server
		push(@generics, [ $text{'form_generic_master'}, '' ]);
		}
	if (&can_create_sub_servers() && $gparent) {
		# Sub-server under parent's user
		push(@generics, [ $text{'form_generic_subserver'},
				  'add1=1&parentuser1='.$gparent->{'user'} ]);
		if (!$gparent->{'alias'}) {
			# Alias domain
			push(@generics, [ &text('form_generic_alias',
						$gparent->{'dom'}),
					  'to='.$gparent->{'id'} ]);
			}
		if (!$gparent->{'alias'} && !$gparent->{'subdom'} &&
		    &can_create_sub_domains()) {
			# Sub-domain
			push(@generics, [ &text('form_generic_subdom',
						$gparent->{'dom'}),
					  'add1=1&parentuser1='.
					  $gparent->{'user'}.'&subdom='.
					  $gparent->{'id'} ]);
			}
		}
	if (!defined($in{'genericmode'})) {
		$in{'genericmode'} = 0;
		}

	# Force inputs to match selected generic type 
	$generic = $generics[$in{'genericmode'}];
	%in = ( %in, map { split(/=/, $_, 2) } split(/\&/, $generic->[1]) );
	}

# Get parent settings
if ($in{'to'}) {
	# Creating an alias domain
	$aliasdom = &get_domain($in{'to'});
	$parentdom = $aliasdom->{'parent'} ?
		&get_domain($aliasdom->{'parent'}) : $aliasdom;
	$parentuser = $parentdom->{'user'};
	}
elsif (!&can_create_master_servers()) {
	# This user can only create a sub-server
	if ($access{'admin'}) {
		$parentdom = &get_domain($access{'admin'});
		$parentuser = $parentdom->{'user'};
		}
	else {
		$parentuser = $remote_user;
		}
	}
elsif ($in{'parentuser1'} || $in{'parentuser2'}) {
	# Creating sub-server explicitly
	$parentuser = $in{'add1'} ? $in{'parentuser1'} : $in{'parentuser2'};
	}
if ($parentuser && !$parentdom) {
	$parentdom = &get_domain_by("user", $parentuser, "parent", "");
	$parentdom || &error(&text('form_eparent', $parentuser));
	}
if ($in{'subdom'}) {
	# Creating a sub-domain
	$subdom = &get_domain($in{'subdom'});
	$subdom || &error(&text('form_esubdom', $in{'subdom'}));
	}

&ui_print_header(undef, $aliasdom ? $text{'form_title3'} :
			$subdom ? $text{'form_title4'} :
			$parentdom ? $text{'form_title2'} :
				     $text{'form_title'}, "",
			$aliasdom ? "create_alias" :
			$parentdom ? "create_subserver" :
			$subdom ? "create_subdom" :
				  "create_form");

# Show generic mode selector
if ($in{'generic'} && @generics > 1) {
	print "<b>$text{'form_genericmode'}</b>\n";
	@links = ( );
	for($i=0; $i<@generics; $i++) {
		$g = $generics[$i];
		if ($i == $in{'genericmode'}) {
			push(@links, $g->[0]);
			}
		else {
			push(@links, "<a href='domain_form.cgi?generic=1&".
				     "genericmode=$i&gparent=$in{'gparent'}&".
				     "$g->[1]'>$g->[0]</a>");
			}
		}
	print &ui_links_row(\@links),"<p>\n";
	}

# Form header
@tds = ( "width=30%" );
print &ui_form_start("domain_setup.cgi", "post");
print &ui_hidden("parentuser", $parentuser),"\n";
print &ui_hidden("to", $in{'to'}),"\n";
print &ui_hidden("subdom", $in{'subdom'}),"\n";
print &ui_hidden_table_start($text{'form_header'}, "width=100%", 2,
			     "basic", 1);

# Domain name
if ($subdom) {
	print &ui_table_row(&hlink($text{'form_domain'}, "domainname"),
		&ui_textbox("dom", undef, 20).".$subdom->{'dom'}",
		undef, \@tds);
	}
else {
	local $force = $access{'forceunder'} && $parentdom ?
			".$parentdom->{'dom'}" :
		       $access{'subdom'} ? ".$access{'subdom'}" : undef;
	print &ui_table_row(&hlink($text{'form_domain'}, "domainname"),
	      &ui_textbox("dom", $force, 50),
	      undef, \@tds);
	}

# Description / owner
print &ui_table_row(&hlink($text{'form_owner'}, "ownersname"),
		    &ui_textbox("owner", undef, 50),
		    undef, \@tds);

if (!$parentuser) {
	# Password
	print &ui_table_row(&hlink($text{'form_pass'}, "password"),
		&new_password_input("vpass"),
		undef, \@tds);
	}

# Generate Javascript for template change
print "<script>\n";
print "function select_template(num)\n";
print "{\n";
@availtmpls = &list_available_templates($parentdom, $aliasdom);
$deftmpl = $availtmpls[0];
foreach $t (@availtmpls) {
	local $tmpl = &get_template($t->{'id'});
	print "if (num == $tmpl->{'id'}) {\n";
	if (!$parentdom) {
		# Set group for unix user
		if (&can_choose_ugroup()) {
			$num = $tmpl->{'ugroup'} eq "none" ? 0 : 1;
			$val = $tmpl->{'ugroup'} eq "none" ? "" : $tmpl->{'ugroup'};
			print "    document.forms[0].group_def[$num].checked = true;\n";
			print "    document.forms[0].group.value = \"$val\";\n";
			}

		# Set quotas
		print &quota_javascript("quota", $tmpl->{'quota'}, "home", 0);
		print &quota_javascript("uquota", $tmpl->{'uquota'}, "home", 0);

		# Set limits
		print &quota_javascript("mailboxlimit", $tmpl->{'mailboxlimit'},
					"none", 1);
		print &quota_javascript("aliaslimit", $tmpl->{'aliaslimit'},
					"none", 1);
		print &quota_javascript("dbslimit", $tmpl->{'dbslimit'},
					"none", 1);
		if ($config{'bw_active'}) {
			print &quota_javascript("bwlimit", $tmpl->{'bwlimit'},
						"bw", 1);
			}
		$num = $tmpl->{'domslimit'} eq "none" ? 1 :
		       $tmpl->{'domslimit'} eq "0" ? 0 : 2;
		$val = $num == 2 ? $tmpl->{'domslimit'} : "";
		print "    document.forms[0].domslimit_def[$num].checked = true;\n";
		print "    document.forms[0].domslimit.value = \"$val\";\n";

		# Set no database name
		print "    document.forms[0].nodbname[$tmpl->{'nodbname'}].checked = true;\n";
		}
	print "    }\n";
	}
print "}\n";
print "</script>\n";

# Show template selection field
foreach $t (&list_available_templates($parentdom, $aliasdom)) {
	$firsttemplate ||= $t;
	push(@opts, [ $t->{'id'}, $t->{'name'} ]);
	push(@cantmpls, $t);
	}
print "</select></td> </tr>\n";
print &ui_table_row(&hlink($text{'form_template'},"template"),
	&ui_select("template", undef, \@opts, 1, 0,
		   0, 0, $config{'template_auto'} ? "" :
		"onChange='select_template(options[selectedIndex].value)'"),
	undef, \@tds);

if ($aliasdom) {
	# Show destination of alias
	print &ui_table_row(&hlink($text{'form_aliasdom'}, "aliasdom"),
		"<a href='edit_domain.cgi?dom=$parentdom->{'id'}'>".
		"$aliasdom->{'dom'}</a>",
		undef, \@tds);
	}
elsif ($parentdom) {
	# Show parent domain
	print &ui_table_row(&hlink($text{'form_parentdom'}, "parentdom"),
		"<a href='edit_domain.cgi?dom=$parentdom->{'id'}'>".
		"$parentdom->{'dom'}</a> (<tt>$parentuser</tt>)",
		undef, \@tds);
	}

print &ui_hidden_table_end("basic");

# Start of advanced section
$has_advanced = $aliasdom || $subdom ? 0 : 1;
if ($has_advanced) {
	print &ui_hidden_table_start($text{'form_advanced'}, "width=100%", 2,
				     "advanced", 0);
	}

# These settings are not needed for a sub-domain, as they come from the owner
if (!$parentuser) {
	# Contact email address
	print &ui_table_row(&hlink($text{'form_email'}, "ownersemail"),
		&ui_opt_textbox("email", undef, 30,
				$text{'form_email_def'},
				$text{'form_email_set'}),
		undef, \@tds);

	# Unix username
	print &ui_table_row(&hlink($text{'form_user'}, "unixusername"),
		&ui_opt_textbox("vuser", undef, 15,
				$text{'form_auto'}, $text{'form_nwuser'}),
		undef, \@tds);

	# Mail group name
	print &ui_table_row(&hlink($text{'form_mgroup'}, "mailgroupname"),
		&ui_opt_textbox("mgroup", undef, 15,
				$text{'form_auto'}, $text{'form_nwgroup'}),
		undef, \@tds);

	if (&can_choose_ugroup()) {
		# Group for Unix user
		local $ug = $deftmpl->{'ugroup'};
		$ug = "" if ($ug eq "none");
		print &ui_table_row(&hlink($text{'form_group'},"unixgroupname"),
			&ui_opt_textbox("group", $ug, 15,
					$text{'form_crgroup'},
					$text{'form_exgroup'}).
			&group_chooser_button("group"),
			undef, \@tds);
		}
	}

if (!$aliasdom && &max_username_length()) {
	# Show input for mail username prefix, if needed
	print &ui_table_row(&hlink($text{'form_prefix'}, "prefixname"),
		&ui_opt_textbox("prefix", undef, 15,
				$text{'form_auto'}),
		undef, \@tds);
	}
else {
	print &ui_hidden("prefix_def", 1),"\n";
	}

if (!$aliasdom && &database_feature() && &can_edit_databases() && !$subdom) {
	# Show database name field, iff this is not an alias or sub domain
	print &ui_table_row(&hlink($text{'form_dbname'},"dbname"),
		&ui_opt_textbox("db", undef, 15,
				$text{'form_auto'}),
		undef, \@tds);
	}

if ($has_advanced) {
	print &ui_hidden_table_end("advanced");
	}

# Show hidden section for limits
if (!$parentuser && !$config{'template_auto'}) {
	print &ui_hidden_table_start($text{'form_limits'}, "width=100%", 2,
				     "limits", 0);
	}

# Only display quota inputs if enabled, and if not creating a subdomain
if (&has_home_quotas() && !$parentuser && !$config{'template_auto'}) {
	print &ui_table_row(&hlink($text{'form_quota'}, "websitequota"),
		&quota_input("quota", $config{'defquota'}, "home"),
		undef, \@tds);

	print &ui_table_row(&hlink($text{'form_uquota'}, "unixuserquota"),
		&quota_input("uquota", $config{'defuquota'}, "home"),
		undef, \@tds);
	}

if (!$parentdom && $config{'bw_active'} && !$config{'template_auto'}) {
	# Show bandwidth limit field
	print &ui_table_row(&hlink($text{'edit_bw'}, "bwlimit"),
			    &bandwidth_input("bwlimit", 0),
			    undef, \@tds);
	}

if (!$parentuser && !$config{'template_auto'}) {
	# Show input for limit on number of mailboxes, aliases and DBs
	foreach $l ("mailbox", "alias", "dbs") {
		print &ui_table_row(
			&hlink($text{'form_'.$l.'limit'}, $l.'limit'),
			&ui_opt_textbox($l.'limit', $config{'def'.$l.'limit'},
					4, $text{'form_unlimit'},
					$text{'form_atmost'}),
			undef, \@tds);
		}

	# Show input for restriction of number of sub-domains this domain
	# owner can create
	local $dlm = $config{'defdomslimit'} eq "" ? 1 :
		     $config{'defdomslimit'} eq "*" ? 2 : 0;
	print &ui_table_row(&hlink($text{'form_domslimit'}, "domslimit"),
		&ui_radio("domslimit_def", $dlm,
			  [ [ 1, $text{'form_nocreate'} ],
			    [ 2, $text{'form_unlimit'} ],
			    [ 0, $text{'form_atmost'} ] ])."\n".
		&ui_textbox("domslimit",
			    $dlm == 0 ? $config{'defdomslimit'} : "", 4),
		undef, \@tds);

	# Show input for default database name limit
	print &ui_table_row(&hlink($text{'limits_nodbname'}, "nodbname"),
		&ui_radio("nodbname", $config{'defnodbname'} ? 1 : 0,
			  [ [ 0, $text{'yes'} ], [ 1, $text{'no'} ] ]),
		undef, \@tds);
	}

if (!$parentuser && !$config{'template_auto'}) {
	print &ui_hidden_table_end("limits");
	}

# Show section for custom fields, if any
$fields = &show_custom_fields(undef, \@tds);
if ($fields) {
	print &ui_hidden_table_start($text{'edit_customsect'}, "width=100%", 2,
				     "custom", 0);
	print $fields;
	print &ui_hidden_table_end("custom");
	}

# Show checkboxes for features
print &ui_hidden_table_start($text{'edit_featuresect'}, "width=100%", 2,
			     "feature", 0);
@grid = ( );
$i = 0;
foreach $f ($aliasdom ? @opt_alias_features :
	    $subdom ? @opt_subdom_features : @opt_features) {
	# Don't allow access to features that this user hasn't been
	# granted for his subdomains.
	next if (!&can_use_feature($f));
	next if ($parentdom && $f eq "webmin");
	next if ($parentdom && $f eq "unix");
	next if ($aliasdom && !$aliasdom->{$f});
	next if (!$config{$f} && defined($config{$f}));		# Not enabled
	$can_feature{$f}++;

	if ($config{$f} == 3) {
		# This feature is always on, so don't show it
		print &ui_hidden($f, 1),"\n";
		next;
		}

	local $txt = $parentdom ? $text{'form_sub'.$f} : undef;
	$txt ||= $text{'form_'.$f};
	push(@grid, &ui_checkbox($f, 1, "", $config{$f} == 1).
		    "<b>".&hlink($txt, $f)."</b>");
	}

# Show checkboxes for plugins
%inactive = map { $_, 1 } split(/\s+/, $config{'plugins_inactive'});
foreach $f (@feature_plugins) {
	next if (!&plugin_call($f, "feature_suitable",
				$parentdom, $aliasdom, $subdom));
	next if (!&can_use_feature($f));
	next if ($aliasdom && !$aliasdom->{$f});

	$label = &plugin_call($f, "feature_label", 0);
	$label = "<b>$label</b>";
	$hlink = &plugin_call($f, "feature_hlink");
	$label = &hlink($label, $hlink, $f) if ($hlink);
	push(@grid, &ui_checkbox($f, 1, "", !$inactive{$f})." ".$label);
	}
$ftable = &ui_grid_table(\@grid, 2, 100,
	[ "width=30% align=left", "width=70% align=left" ]);
print &ui_table_row(undef, $ftable, 4);
print &ui_hidden_table_end("feature");

# Start section for proxy and IP
if (!$aliasdom) {
	print &ui_hidden_table_start($text{'form_proxysect'}, "width=100%", 2,
				     "proxy", 0);
	}

# Show inputs for setting up a proxy-only virtual server
if ($config{'proxy_pass'} && !$aliasdom) {
	print &frame_fwd_input();
	}

# Show field for mail forwarding
if ($can_feature{'mail'} && !$aliasdom && !$subdom) {
	print &ui_table_row(&hlink($text{'form_fwdto'}, "fwdto"),
		&ui_opt_textbox("fwdto", undef, 30, $text{'form_fwdto_none'}),
		undef, \@tds);
	}

# Show IP address allocation section
$resel = $parentdom ? $parentdom->{'reseller'} :
	 &reseller_admin() ? $base_remote_user : undef;
if (!$aliasdom && &can_select_ip()) {
	print &ui_table_row(&hlink($text{'form_iface'}, "iface"),
		&virtual_ip_input(\@cantmpls, $resel),
		undef, \@tds);
	}

print &ui_hidden_end();
print &ui_table_end();

if (!$aliasdom && $config{'web'} && $virtualmin_pro) {
	# Show field for initial content
	print &ui_hidden_table_start($text{'form_park'}, "width=100%", 2,
				     "park", 0);

	# Initial content
	print &ui_table_row(&hlink($text{'form_content'},"form_content"),
			    &ui_radio("content_def", 1, 
				      [ [ 1, $text{'form_content1'} ] ,
					[ 0, $text{'form_content0'} ] ])."<br>".
			    &ui_textarea("content", undef, 5, 70),
			    3, \@tds);

	# Style for content
	print &ui_table_row(&hlink($text{'form_style'}, "form_style"),
			    &content_style_chooser("style", undef),
			    3, \@tds);

	print &ui_hidden_end();
	print &ui_table_end();
	}

print &ui_form_end([ [ "ok", $text{'form_ok'} ] ]);
if (!$config{'template_auto'}) {
	print "<script>select_template($firsttemplate->{'id'});</script>\n";
	}

&ui_print_footer("", $text{'index_return'});

