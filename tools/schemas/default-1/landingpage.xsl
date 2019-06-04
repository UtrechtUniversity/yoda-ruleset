<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:str="http://exslt.org/strings"
    xmlns:date="http://exslt.org/dates-and-times"
    xmlns:yoda="https://yoda.uu.nl/schemas/default-1"
    extension-element-prefixes="str date"
    xmlns="http://www.w3.org/1999/xhtml"
    version="1.0">
    <xsl:output method="xml" version="1.0" encoding="UTF-8" omit-xml-declaration="yes" indent="yes"/>
    <xsl:strip-space elements="*"/>
    <xsl:template match="/">
        <xsl:text disable-output-escaping="yes">&lt;!doctype html&gt;
    </xsl:text>
    <xsl:apply-templates select="/yoda:metadata"/>
    </xsl:template>
    <xsl:template select="text()"/>
    <xsl:template match="/yoda:metadata">
        <html lang="en">
            <head>
                <meta charset="utf-8"/>
                <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no"/>
                <meta name="description" content="Data Publication platform of Utrecht University"/>
                <title><xsl:apply-templates select="yoda:Title"/> - Data Publication platform of Utrecht University</title>

                <link href="static/css/bootstrap.min.css?v=1559637767" rel="stylesheet"/>
                <link href="static/css/uu.css?v=1559637767" rel="stylesheet"/>
            </head>
            <body>
                <div class="container bg-white no-padding">
                    <header>
                        <div class="logo pt-2">
                            <img src="/static/img/logo.svg"/>
                        </div>
                        <div class="header-title">
                            <h1>Data publication platform of Utrecht University</h1>
                        </div>
                    </header>
                    <main>
                        <div class="creators">
                            <xsl:for-each select="yoda:Creator">
                                <xsl:value-of select="./yoda:Name"/>
                                <xsl:if test="position() != last()">
                                    &amp;
                                </xsl:if>
                            </xsl:for-each>
                        </div>
                        <section class="content">
                            <h2><xsl:apply-templates select="yoda:Title"/></h2>
                            <div class="meta">
                                <label>Publication Date:</label>
                                <span class="date"><xsl:apply-templates select="yoda:System/yoda:Publication_Date"/></span>
                                <label>Accessibility:</label>
                                <xsl:apply-templates select="yoda:Data_Access_Restriction"/>
                            </div>
                            <xsl:apply-templates select="yoda:Description"/>
                            <xsl:if test="yoda:Tag">
                                <div class="tags">
                                    <label>Tags</label>

                                    <xsl:apply-templates select="yoda:Tag"/>
                                </div>
                            </xsl:if>
                            <hr/>
                            <xsl:apply-templates select="yoda:Data_Access_Restriction" mode="button"/>
                        </section>
                        <section class="metadata">
                            <h2>Metadata</h2>
                            <div class="list">
                                <div class="group">
                                    <xsl:apply-templates select="yoda:Discipline | yoda:Version | yoda:Language"/>
                                </div>
                                <div class="group">
                                    <xsl:apply-templates select="yoda:Data_Classification"/>
                                    <xsl:apply-templates select="yoda:Data_Type"/>
                                    <xsl:apply-templates select="yoda:Collection_Name"/>
                                    <xsl:apply-templates select="yoda:Funding_Reference"/>
                                </div>
                                <div class="group">
                                    <xsl:apply-templates select="yoda:System/yoda:Persistent_Identifier_Datapackage"/>
                                    <div class="row">
                                        <div class="col-sm-2">
                                            <label>Publication Date</label>
                                        </div>
                                        <div class="col-sm-10">
                                            <span><xsl:apply-templates select="yoda:System/yoda:Publication_Date"/></span>
                                        </div>
                                    </div>
                                    <div class="row">
                                        <div class="col-sm-2">
                                            <label>Last Modification</label>
                                        </div>
                                        <div class="col-sm-10">
                                            <span><xsl:apply-templates select="yoda:System/yoda:Last_Modified_Date"/></span>
                                        </div>
                                    </div>
                                </div>
                                <div class="group">
                                    <xsl:apply-templates select="yoda:Related_Datapackage"/>
                                </div>
                                <div class="group">
                                    <xsl:apply-templates select="yoda:Creator"/>
                                    <xsl:apply-templates select="yoda:Contributor"/>
                                    <xsl:apply-templates select="yoda:License"/>
                                </div>
                            </div>
                        </section>
                        <section class="questions">
                            <h2>Questions?</h2>
                            <div class="col text-center">
                                <a href="https://www.uu.nl/en/research/research-data-management" class="btn btn-secondary support-btn" target="_blank">
                                    Research data management support
                                </a>
                            </div>
                        </section>
                    </main>
                    <footer>
                        <div class="logo">
                            <img src="/static/img/logo_footer.svg"/>
                        </div>
                    </footer>
                </div>
            </body>
        </html>
    </xsl:template>

    <xsl:template match="yoda:Title">
        <xsl:value-of select="."/>
    </xsl:template>

    <xsl:template match="yoda:System/yoda:Publication_Date">
        <xsl:value-of select="date:month-name(.)"/>
        <xsl:text> </xsl:text>

        <xsl:value-of select="date:day-in-month(.)"/>
        <xsl:text>, </xsl:text>

        <xsl:value-of select="date:year(.)"/>
    </xsl:template>

    <xsl:template match="yoda:Data_Access_Restriction">
        <span>
            <xsl:value-of select="."/>
        </span>
    </xsl:template>

    <xsl:template match="yoda:Data_Access_Restriction[starts-with(.,'Open')]" mode="button">
        <a class="btn btn-primary access-btn" target="_blank">
            <xsl:attribute name="href"><xsl:value-of select="str:encode-uri(/yoda:metadata/yoda:System/yoda:Open_Access_Link,false())"/></xsl:attribute>
            Acces datapackage
        </a>
    </xsl:template>

    <xsl:template match="yoda:Data_Access_Restriction[starts-with(.,'Restricted')]" mode="button">
        <p>The data is restricted. Contact datamanager.</p>
    </xsl:template>

    <xsl:template match="yoda:Data_Access_Restriction[.='Closed']" mode="button">
        <p>The data is closed for access.</p>
    </xsl:template>

    <xsl:template match="yoda:Description">
        <p class="description">
            <xsl:value-of select="."/>
        </p>
    </xsl:template>

    <xsl:template match="yoda:Tag">
        <span class="tag"><xsl:value-of select="."/></span>
    </xsl:template>

    <xsl:template match="yoda:System/yoda:Last_Modified_Date">
        <xsl:variable name="localtime" as="xs:dateTime" select="substring(.,0,20)"/>
        <xsl:variable name="utcoffset" as="xs:string" select="substring(.,20)"/>

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
    </xsl:template>

    <xsl:template match="yoda:Discipline | yoda:Version | yoda:Language | yoda:Affiliation | yoda:Data_Classification | yoda:Collection_Name | yoda:Data_Type">
        <div class="row">
            <div class="col-sm-2">
                <label><xsl:value-of select="translate(local-name(),'_',' ')"/></label>
            </div>
            <div class="col-sm-10">
                <span><xsl:value-of select="."/></span>
            </div>
        </div>
    </xsl:template>

    <xsl:template match="yoda:Funding_Reference">
        <div class="row">
            <div class="col-sm-2">
                <label>Funder</label>
            </div>
            <div class="col-sm-10">
                <span><xsl:value-of select="./yoda:Funder_Name"/></span>
            </div>
        </div>
        <div class="row">
            <div class="col-sm-2">
                <label>Award Number</label>
            </div>
            <div class="col-sm-10">
                <span><xsl:value-of select="./yoda:Properties/yoda:Award_Number"/></span>
            </div>
        </div>
    </xsl:template>

    <xsl:template match="yoda:Creator | yoda:Contributor">
        <div class="row">
            <div class="col-sm-2">
                <label><xsl:value-of select="local-name()"/></label>
            </div>
            <div class="col-sm-10">
                <span><xsl:value-of select="./yoda:Name"/></span>
            </div>
        </div>
        <xsl:apply-templates select="./yoda:Properties/yoda:Person_Identifier"/>
        <xsl:apply-templates select="./yoda:Properties/yoda:Affiliation"/>
    </xsl:template>

    <xsl:template match="yoda:Related_Datapackage">
        <div class="row">
            <div class="col-sm-2">
                <label><xsl:value-of select="translate(local-name(),'_',' ')"/></label>
            </div>
            <div class="col-sm-10">
                <span><xsl:value-of select="./yoda:Properties/yoda:Title"/></span>
            </div>
        </div>

        <xsl:apply-templates select="yoda:Relation_Type"/>

        <xsl:apply-templates select="./yoda:Properties/yoda:Persistent_Identifier"/>
    </xsl:template>

    <xsl:template match="yoda:Persistent_Identifier">
        <div class="row">
            <div class="col-sm-2">
                <label>Persistent Identifier</label>
            </div>
            <div class="col-sm-10">
                <span>
                    <xsl:value-of select="yoda:Identifier_Scheme"/>
                    <xsl:text>: </xsl:text><xsl:value-of select="yoda:Identifier"/>
                </span>
            </div>
        </div>
    </xsl:template>

    <xsl:template match="yoda:Person_Identifier">
        <div class="row">
            <div class="col-sm-2">
                <label>Person Identifier</label>
            </div>
            <div class="col-sm-10">
                <span>
                    <xsl:value-of select="yoda:Name_Identifier_Scheme"/>
                    <xsl:text>: </xsl:text><xsl:value-of select="yoda:Name_Identifier"/>
                </span>
            </div>
        </div>
    </xsl:template>

    <xsl:template match="yoda:Relation_Type">
        <div class="row">
            <div class="col-sm-2">
                <label>Type of relation</label>
            </div>
            <div class="col-sm-10">
                <span><xsl:value-of select="."/></span>
            </div>
        </div>
    </xsl:template>

    <xsl:template match="yoda:System/yoda:Persistent_Identifier_Datapackage">
        <div class="row">
            <div class="col-sm-2">
                <label>Persistent Identifier</label>
            </div>
            <div class="col-sm-10">
                <span>
                    <xsl:value-of select="yoda:Identifier_Scheme"/>
                    <xsl:text>: </xsl:text><xsl:value-of select="yoda:Identifier"/>
                </span>
            </div>
        </div>
    </xsl:template>

    <xsl:template match="yoda:License">
        <div class="row">
            <div class="col-sm-2">
                <label>License</label>
            </div>
            <div class="col-sm-10">
                <span>
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
                </span>
            </div>
        </div>
    </xsl:template>
</xsl:stylesheet>
