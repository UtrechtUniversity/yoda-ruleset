<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
 xmlns:str="http://exslt.org/strings"
 xmlns:date="http://exslt.org/dates-and-times"
 extension-element-prefixes="str date"
 xmlns="http://www.w3.org/1999/xhtml"
 version="1.0">
  <xsl:output method="html" version="1.0" encoding="UTF-8" omit-xml-declaration="yes" indent="yes"/>
  <xsl:strip-space elements="*"/>
  <xsl:template match="/">
    <xsl:text disable-output-escaping="yes">&lt;!DOCTYPE html&gt;
    </xsl:text>
    <xsl:apply-templates select="/metadata"/>
  </xsl:template>
  <xsl:template select="text()"/>
  <xsl:template match="/metadata">
    <html lang="en">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1"/>
        <meta charset="utf-8"/>
        <meta http-equiv="X-UA-Compatible" content="IE=edge"/>
        <meta name="description" content="Data Publication platform of Utrecht University"/>
        <meta name="author" content="Utrecht University"/>
        <title>Data Publication platform of Utrecht University</title>
	<link href="/static/css/yoda-landingpage.css" rel="stylesheet"/>
      </head>
      <body>
	<div class="brandbar container">
	  <div class="logo pull-left">
            <a href="http://www.uu.nl">
              <img src="/static/img/logo-uu.svg" />
            </a>
	  </div>
	</div>
	<nav class="navbar navbar-inverse navbar-static-top">
	  <div class="container">
            <div class="navbar-header">
	      <span class="navbar-brand">Data Publication platform of Utrecht University</span>
	    </div>
	  </div>
	</nav>
        <div class="container">
          <div class="row">
            <div class="col-md-10">
              <dl class="dl-horizontal">
		<dd>This data package (<xsl:value-of select="./System/Persistent_Identifier_Datapackage/Identifier"/>) has been made temporarily unavailable.</dd>
              </dl>
            </div>
          </div>
        </div>
	<footer class="footer">
	  <div class="container">
            <img src="/static/img/logo_footer.svg" />
	  </div>
	</footer>
      </body>
    </html>
  </xsl:template>
</xsl:stylesheet>
