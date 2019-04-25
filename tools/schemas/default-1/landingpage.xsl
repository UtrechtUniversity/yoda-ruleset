<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
 xmlns:str="http://exslt.org/strings"
 xmlns:date="http://exslt.org/dates-and-times"
 xmlns:yoda="https://yoda.uu.nl/schemas/default-1"
 extension-element-prefixes="str date"
 xmlns="http://www.w3.org/1999/xhtml"
 version="1.0">
  <xsl:output method="xml" version="1.0" encoding="UTF-8" omit-xml-declaration="yes" indent="yes"/>
  <xsl:strip-space elements="*"/>
  <xsl:template match="/">
    <xsl:text disable-output-escaping="yes">&lt;!DOCTYPE html&gt;
    </xsl:text>
    <xsl:apply-templates select="/yoda:metadata"/>
  </xsl:template>
  <xsl:template select="text()"/>
  <xsl:template match="/yoda:metadata">
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
              <xsl:apply-templates select="yoda:Title"/>
              <xsl:apply-templates select="yoda:Description"/>
              <hr />
              <h3>Descriptive</h3>
              <dl class="dl-horizontal">
                <xsl:apply-templates select="yoda:Discipline | yoda:Version | yoda:Related_Datapackage | yoda:Language"/>
                <xsl:if test="yoda:Tag">
                  <dt>Tag(s)</dt>
                  <dd>
                    <xsl:apply-templates select="yoda:Tag"/>
                  </dd>
                </xsl:if>
              </dl>
              <h3>Administrative</h3>
              <dl class="dl-horizontal">
                <xsl:apply-templates select="yoda:Collection_Name | yoda:Data_Classification | yoda:Funding_Reference"/>
              </dl>
              <h3>System</h3>
              <dl class="dl-horizontal">
                <xsl:apply-templates select="yoda:System"/>
              </dl>
              <h3>Rights</h3>
              <dl class="dl-horizontal">
                <xsl:apply-templates select="yoda:Creator | yoda:Contributor | yoda:License"/>
              </dl>
              <xsl:apply-templates select="yoda:Data_Access_Restriction"/>
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
  <xsl:template match="yoda:Tag">
    <u>
      <xsl:value-of select="."/>
    </u>
    <xsl:text> </xsl:text>
  </xsl:template>
  <xsl:template match="yoda:System">
    <dt>Persistent Identifier</dt>
    <dd><xsl:value-of select="./yoda:Persistent_Identifier_Datapackage/yoda:Identifier_Scheme"/>: <xsl:value-of select="./yoda:Persistent_Identifier_Datapackage/yoda:Identifier"/></dd>
    <xsl:apply-templates select="./yoda:Publication_Date"/>
    <xsl:apply-templates select="./yoda:Last_Modified_Date"/>
  </xsl:template>
  <xsl:template match="yoda:Title">
    <h1>
      <xsl:value-of select="."/>
    </h1>
  </xsl:template>
  <xsl:template match="yoda:Description">
    <p>
      <xsl:value-of select="."/>
    </p>
  </xsl:template>
  <xsl:template match="yoda:Discipline | yoda:Version | yoda:Language">
    <dt>
      <xsl:value-of select="local-name()"/>
    </dt>
    <dd>
      <xsl:value-of select="."/>
    </dd>
  </xsl:template>
  <xsl:template match="yoda:Collection_Name | yoda:Data_Classification">
    <dt>
      <xsl:value-of select="translate(local-name(),'_',' ')"/>
    </dt>
    <dd>
      <xsl:value-of select="."/>
    </dd>
  </xsl:template>
  <xsl:template match="yoda:Related_Datapackage">
    <dt>Related Datapackage</dt>
    <dd>
      <xsl:value-of select="./yoda:Properties/Title"/>
    </dd>
    <dl class="dl-horizontal subproperties">
      <xsl:apply-templates select="yoda:Relation_Type"/>
      <xsl:apply-templates select="./yoda:Properties/yoda:Persistent_Identifier"/>
    </dl>
  </xsl:template>
  <xsl:template match="yoda:Creator | yoda:Contributor">
    <dt>
      <xsl:value-of select="local-name()"/>
    </dt>
    <dd>
      <xsl:value-of select="./yoda:Name"/>
    </dd>
    <dl class="dl-horizontal subproperties">
      <xsl:apply-templates select="./yoda:Properties/yoda:Person_Identifier"/>
      <xsl:apply-templates select="./yoda:Properties/yoda:Affiliation"/>
    </dl>
  </xsl:template>
  <xsl:template match="yoda:Funding_Reference">
    <dt>Funder</dt>
    <dd>
      <xsl:value-of select="./yoda:Funder_Name"/>
    </dd>
    <dt>Award Number</dt>
    <dd>
      <xsl:value-of select="./yoda:Properties/yoda:Award_Number"/>
    </dd>
  </xsl:template>
  <xsl:template match="yoda:License">
    <dt>License</dt>
    <dd>
      <xsl:choose>
        <xsl:when test="/yoda:metadata/yoda:System/yoda:License_URI">
          <a>
            <xsl:attribute name="href"><xsl:value-of select="/yoda:metadata/yoda:System/yoda:License_URI"/></xsl:attribute>
            <xsl:attribute name="target">blank</xsl:attribute>
            <xsl:value-of select="."/>
          </a>
        </xsl:when>
        <xsl:otherwise>
          <xsl:value-of select="."/>
        </xsl:otherwise>
      </xsl:choose>
    </dd>
  </xsl:template>
  <xsl:template match="yoda:Last_Modified_Date">
    <xsl:variable name="localtime" as="xs:dateTime" select="substring(.,0,20)"/>
    <xsl:variable name="utcoffset" as="xs:string" select="substring(.,20)"/>
    <dt>Last Modification</dt>
   <dd>
      <xsl:value-of select="date:month-name($localtime)"/>
      <xsl:text> </xsl:text>
      <xsl:value-of select="date:day-in-month($localtime)"/>
      <xsl:text>, </xsl:text>
      <xsl:value-of select="date:year($localtime)"/>
      <xsl:text>, </xsl:text>
      <xsl:value-of select="date:hour-in-day($localtime)"/>
      <xsl:text>:</xsl:text>
      <xsl:value-of select="substring(string(100 + date:minute-in-hour($localtime)), 2)"/>
      <xsl:text> GMT</xsl:text>
      <xsl:value-of select="$utcoffset"/>
    </dd>
  </xsl:template>
  <xsl:template match="yoda:Publication_Date">
    <dt>Publication Date</dt>
    <dd>
      <xsl:value-of select="date:month-name(.)"/>
      <xsl:text> </xsl:text>
      <xsl:value-of select="date:day-in-month(.)"/>
      <xsl:text>, </xsl:text>
      <xsl:value-of select="date:year(.)"/>
    </dd>
  </xsl:template>

  <xsl:template match="yoda:Data_Access_Restriction[starts-with(.,'Open')]">
    <h3>Data Access</h3>
    <p>The data is open access. Use this link <a><xsl:attribute name="href"><xsl:value-of select="str:encode-uri(/yoda:metadata/yoda:System/yoda:Open_Access_Link,false())"/></xsl:attribute><xsl:value-of select="/yoda:metadata/yoda:System/yoda:Open_Access_Link"/></a> to access this data package.</p>
  </xsl:template>
  <xsl:template match="yoda:Data_Access_Restriction[starts-with(.,'Restricted')]">
    <h3>Data Access</h3>
    <p>The data is restricted. Contact datamanager.</p>
  </xsl:template>
  <xsl:template match="yoda:Data_Access_Restriction[.='Closed']">
    <h3>Data Access</h3>
    <p>The data is closed for access.</p>
  </xsl:template>
  <xsl:template match="yoda:Persistent_Identifier">
    <dt>Persistent Identifier</dt>
    <dd><xsl:value-of select="yoda:Identifier_Scheme"/><xsl:text>: </xsl:text><xsl:value-of select="yoda:Identifier"/></dd>
  </xsl:template>
  <xsl:template match="yoda:Person_Identifier">
    <dt>Person Identifier</dt>
    <dd><xsl:value-of select="yoda:Name_Identifier_Scheme"/><xsl:text>: </xsl:text><xsl:value-of select="yoda:Name_Identifier"/></dd>
  </xsl:template>
  <xsl:template match="yoda:Relation_Type">
    <dt>Type of relation</dt>
    <dd><xsl:value-of select="."/></dd>
  </xsl:template>
  <xsl:template match="yoda:Affiliation">
    <dt>Affiliation</dt>
    <dd>
      <xsl:value-of select="."/>
    </dd>
  </xsl:template>
</xsl:stylesheet>
