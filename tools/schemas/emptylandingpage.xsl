<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:str="http://exslt.org/strings"
    xmlns:date="http://exslt.org/dates-and-times"
    extension-element-prefixes="str date"
    xmlns="http://www.w3.org/1999/xhtml"
    version="1.0">
    <xsl:output method="xml" version="1.0" encoding="UTF-8" omit-xml-declaration="yes" indent="yes"/>
    <xsl:strip-space elements="*"/>
    <xsl:template match="/">
        <xsl:text disable-output-escaping="yes">&lt;!doctype html&gt;
    </xsl:text>
    <xsl:apply-templates select="*[local-name() = 'metadata']"/>
    </xsl:template>
    <xsl:template select="text()"/>
    <xsl:template match="*[local-name() = 'metadata']">
        <html lang="en">
            <head>
                <meta charset="utf-8"/>
                <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no"/>
                <meta name="description" content="Data Publication platform of Utrecht University"/>
                <title><xsl:apply-templates select="*[local-name()='System']/*[local-name()='Persistent_Identifier_Datapackage']"/> - Data Publication platform of Utrecht University</title>

                <link href="/static/css/bootstrap.min.css?v=1559637767" rel="stylesheet"/>
                <link href="/static/css/uu.css?v=1559637767" rel="stylesheet"/>
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
                        <section class="content">
                            <p>This data package (<xsl:apply-templates select="*[local-name()='System']/*[local-name()='Persistent_Identifier_Datapackage']"/>) has been made temporarily unavailable.</p>
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

    <xsl:template match="*[local-name()='System']/*[local-name() = 'Persistent_Identifier_Datapackage']">
        <xsl:value-of select="*[local-name()='Identifier_Scheme']"/>
        <xsl:text>: </xsl:text><xsl:value-of select="*[local-name()='Identifier']"/>
    </xsl:template>
</xsl:stylesheet>
