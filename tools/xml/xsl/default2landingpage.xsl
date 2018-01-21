<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
                xmlns:str="http://exslt.org/strings"
                xmlns:date="http://exslt.org/dates-and-times"
                extension-element-prefixes="str date"
                xmlns="http://www.w3.org/1999/xhtml"
                version="1.0">
    <xsl:output method="xml" version="1.0" encoding="UTF-8" omit-xml-declaration="yes" indent="yes"/>
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
                    <xsl:apply-templates select="Title"/>
                    <xsl:apply-templates select="Description"/>
                    <hr />
                    <h3>Descriptive</h3>
                    <dl class="dl-horizontal">
                        <xsl:apply-templates select="Discipline | Version | Related_Datapackage | Language"/>
                        <xsl:if test="Tag">
                            <dt>Tag(s)</dt>
                            <dd>
                                <xsl:apply-templates select="Tag"/>
                            </dd>
                        </xsl:if>
                    </dl>
                    <h3>Geolocation</h3>
		    <xsl:if test="geoLocation">	
		    	<dl class="dl-horizontal">
				<xsl:apply-templates select="geoLocation"/>
                    	</dl>
		    </xsl:if>	
                    <h3>Administrative</h3>
                    <dl class="dl-horizontal">
                        <xsl:apply-templates select="Collection_Name | Data_Classification | Funding_Reference"/>
                    </dl>
                    <h3>System</h3>
                    <dl class="dl-horizontal">
                        <xsl:apply-templates select="System"/>
                    </dl>
                    <h3>Rights</h3>
                    <dl class="dl-horizontal">
                        <xsl:apply-templates select="Creator | Contributor | License"/>
                    </dl>
                    <xsl:apply-templates select="Data_Access_Restriction"/>
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
	<script async="async" defer="defer" src="//maps.googleapis.com/maps/api/js?key=AIzaSyB4FLR7gvdcA590_tNXU-0UKm-l7cgwJ5Y"></script>
	<script type="text/javascript" src="static/js/jquery-3.2.1.min.js"></script>
	<script type="text/javascript" src="static/js/main.js"></script>
	<script>alert('1');</script>
    </xsl:template>
    <xsl:template match="Tag">
        <u>
            <xsl:value-of select="."/>
        </u>
        <xsl:text> </xsl:text>
    </xsl:template>
    <xsl:template match="System">
        <dt>Persistent Identifier</dt>
        <dd><xsl:value-of select="./Persistent_Identifier_Datapackage/Identifier_Scheme"/>: <xsl:value-of select="./Persistent_Identifier_Datapackage/Identifier"/></dd>
        <xsl:apply-templates select="./Publication_Date"/>
        <xsl:apply-templates select="./Last_Modified_Date"/>
    </xsl:template>
    <xsl:template match="Title">
        <h1>
            <xsl:value-of select="."/>
        </h1>
    </xsl:template>
    <xsl:template match="Description">
        <p>
            <xsl:value-of select="."/>
        </p>
    </xsl:template>
    <xsl:template match="Discipline | Version | Language">
        <dt>
            <xsl:value-of select="local-name()"/>
        </dt>
        <dd>
            <xsl:value-of select="."/>
        </dd>
    </xsl:template>

    <xsl:template match="geoLocation">
        <xsl:variable name="mapCounter" select="position()-1" />
	<xsl:variable name="maxMaps" select="4" />
	<xsl:variable name="maxRest" select="3" />         
 
	<xsl:if test="($mapCounter mod $maxMaps) = 0">
		<!-- <div class="row">	-->
		<p>START NEW ROW</p>
	</xsl:if>	
	<br/>
        <div class="map-placeholder col-md-3">
           <div class="map-init google-maps"></div>
           <input type="text" class="west"  value="{westBoundLongitude}" />
           <input type="text" class="east"  value="{eastBoundLongitude}" />
           <input type="text" class="south" value="{southBoundLatitude}" />
           <input type="text" class="north" value="{northBoundLatitude}" />
        </div>

        <xsl:if test="(($mapCounter mod $maxMaps) = $maxRest) or (position()=last())">
        	<p>END OF ROW </p>
		<!-- </div> -->
        </xsl:if>
    </xsl:template>	
    <xsl:template match="Collection_Name | Data_Classification">
        <dt>
            <xsl:value-of select="translate(local-name(),'_',' ')"/>
        </dt>
        <dd>
            <xsl:value-of select="."/>
        </dd>
    </xsl:template>
    <xsl:template match="Related_Datapackage">
        <dt>Related Datapackage</dt>
        <dd>
            <xsl:value-of select="./Properties/Title"/>
        </dd>
        <dl class="dl-horizontal subproperties">
            <xsl:apply-templates select="Relation_Type"/>
            <xsl:apply-templates select="./Properties/Persistent_Identifier"/>
        </dl>
    </xsl:template>
    <xsl:template match="Creator | Contributor">
        <dt>
            <xsl:value-of select="local-name()"/>
        </dt>
        <dd>
            <xsl:value-of select="./Name"/>
        </dd>
        <dl class="dl-horizontal subproperties">
            <xsl:apply-templates select="./Properties/Person_Identifier"/>
            <xsl:apply-templates select="./Properties/Affiliation"/>
        </dl>
    </xsl:template>
    <xsl:template match="Funding_Reference">
        <dt>Funder</dt>
        <dd>
            <xsl:value-of select="./Funder_Name"/>
        </dd>
        <dt>Award Number</dt>
        <dd>
            <xsl:value-of select="./Properties/Award_Number"/>
        </dd>
    </xsl:template>
    <xsl:template match="License">
        <dt>License</dt>
        <dd>
            <xsl:choose>
                <xsl:when test="/metadata/System/License_URI">
                    <a>
                        <xsl:attribute name="href"><xsl:value-of select="/metadata/System/License_URI"/></xsl:attribute>
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
    <xsl:template match="Last_Modified_Date">
        <xsl:variable name="localtime" select="substring(.,0,20)"/>
        <xsl:variable name="utcoffset"  select="substring(.,20)"/>
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
    <xsl:template match="Publication_Date">
        <dt>Publication Date</dt>
        <dd>
            <xsl:value-of select="date:month-name(.)"/>
            <xsl:text> </xsl:text>
            <xsl:value-of select="date:day-in-month(.)"/>
            <xsl:text>, </xsl:text>
            <xsl:value-of select="date:year(.)"/>
        </dd>
    </xsl:template>

    <!--<xsl:template match="Data_Access_Restriction[starts-with(.,'Open')]">-->
        <!--<h3>Data Access</h3>-->
        <!--<p>The data is open access. Use this link <a><xsl:attribute name="href"><xsl:value-of select="str:encode-uri(/metadata/System/Open_Access_Link,false())"/></xsl:attribute><xsl:value-of select="/metadata/System/Open_Access_Link"/></a> to access this data package.</p>-->
    <!--</xsl:template>-->
    <xsl:template match="Data_Access_Restriction[starts-with(.,'Restricted')]">
        <h3>Data Access</h3>
        <p>The data is restricted. Contact datamanager.</p>
    </xsl:template>
    <xsl:template match="Data_Access_Restriction[.='Closed']">
        <h3>Data Access</h3>
        <p>The data is closed for access.</p>
    </xsl:template>
    <xsl:template match="Persistent_Identifier">
        <dt>Persistent Identifier</dt>
        <dd><xsl:value-of select="Identifier_Scheme"/><xsl:text>: </xsl:text><xsl:value-of select="Identifier"/></dd>
    </xsl:template>
    <xsl:template match="Person_Identifier">
        <dt>Person Identifier</dt>
        <dd><xsl:value-of select="Name_Identifier_Scheme"/><xsl:text>: </xsl:text><xsl:value-of select="Name_Identifier"/></dd>
    </xsl:template>
    <xsl:template match="Relation_Type">
        <dt>Type of relation</dt>
        <dd><xsl:value-of select="."/></dd>
    </xsl:template>
    <xsl:template match="Affiliation">
        <dt>Affiliation</dt>
        <dd>
            <xsl:value-of select="."/>
        </dd>
    </xsl:template>
</xsl:stylesheet>
