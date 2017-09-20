<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
   xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
   xmlns="http://datacite.org/schema/kernel-4">
  <xsl:output method="html" version="4.0" encoding="UTF-8" indent="yes"/>
  <xsl:strip-space elements="*"/>
<xsl:template match="/metadata">
<html lang="en">
	<head>
		<meta name="viewport" content="width=device-width, initial-scale=1"/>
		<meta charset="utf-8"/>
    	<meta http-equiv="X-UA-Compatible" content="IE=edge"/>
    	<meta name="description" content=""/>
    	<meta name="author" content=""/>
		
		<title>Yoda Datapackage</title>

		<link href="css/bootstrap.min.css" rel="stylesheet"/>
		<link href="css/custom.css" rel="stylesheet"/>
	</head>
	<body>
		<div class="container">
			<h1>Yoda Datapackage</h1>
			<div class="row">
  				<div class="col-md-12">
					<h2>System</h2>
					<dl class="dl-horizontal">
						<xsl:apply-templates select="system" />
					</dl>
  					<h2>Descriptive</h2>
  					<dl class="dl-horizontal">
						<xsl:apply-templates select="Title | Description | Discipline | Research_Type | Version | Related_Datapackage | Language | Tag" />
					</dl>
					<h2>Rights</h2>
					<dl class="dl-horizontal">
						<xsl:apply-templates select="Owner | Creator | Contributor | License" />
					</dl>
					<xsl:apply-templates select="Access_Restriction"/>
  				</div>
			</div>
		</div>
	</body>
</html>	
</xsl:template>

<xsl:template match="system">
	<dt>Persistent Identifier</dt>
	<dd><xsl:value-of select="./Persistent_Identifier_Datapackage_Type"/>:<xsl:value-of select="./Persistent_Identifier_Datapackage"/></dd>
	<dt>Last Modification</dt>
	<dd><value-of select="./Last_Modified_Date"/></dd>
	<dt>Publication Date</dt>
	<dd><value-of select="./Publication_Date"/></dd>
</xsl:template>

<xsl:template match="Title">
	<dt>Datapackage Title</dt>
	<dd><xsl:value-of select="."/></dd>
</xsl:template>

<xsl:template match="Description">
	<dt>Datapackage Description</dt>
	<dd><xsl:value-of select="."/></dd>
</xsl:template>

<xsl:template match="Discipline | Version | Language | Tag | Owner">
	<dt><xsl:value-of select="local-name()"/></dt>
	<dd><xsl:value-of select="."/></dd>
</xsl:template>

<xsl:template match="Research_Type">
	<dt>Research Type</dt>
	<dd><xsl:value-of select="."/></dd>
</xsl:template>


<xsl:template match="Related_Datapackage">
	<dt>Related Datapackage</dt>
	<dd><xsl:value-of select="./Title"/></dd>
	<dt>Persistent Identifier</dt>
	<dd><xsl:value-of select="./Properties/Persistent_Identifier_Type"/>:<xsl:value-of select="./Properties/Persistent_Identifier"/></dd>
</xsl:template>

<xsl:template match="Creator | Contributor">
	<dt><xsl:value-of select="local-name()"/> of Datapackage</dt>
	<dd><xsl:value-of select="./Name"/></dd>
	<dt>Persistent Identifier</dt>
	<dd><xsl:value-of select="./Properties/Persistent_identifier_Type"/>:<xsl:value-of select="./Properties/Persistent_Identifier"/></dd>
</xsl:template>

<xsl:template match="License">
	<dt>License</dt>
	<dd><a>
	<xsl:attribute name="href"><xsl:value-of select="./Properties/URL"/></xsl:attribute>
	<xsl:attribute name="target">blank</xsl:attribute>
	<xsl:value-of select="./Name"/>
	</a></dd>
</xsl:template>

<xsl:template match="Access_Restriction[.=Open]">
	<h2>Data Access</h2>
	<p>The data is open access. Use this <a><xsl:attribute name="href"><xsl:value-of select="/metadata/system/Open_Access_Link"/></xsl:attribute>link</a> to browse through this data with webDAV.</p> 	
</xsl:template>

<xsl:template match="Access_Restriction[starts-with(.,Restricted)]">
	<h2>Data Access</h2>
	<p>The data is restricted. Contact datamanager</p>
</xsl:template>

<xsl:template match="Access_Restriction[.=Closed]">
	<h2>Data Access</h2>
	<p>The data is closed for access</p>
</xsl:template>

</xsl:stylesheet>
