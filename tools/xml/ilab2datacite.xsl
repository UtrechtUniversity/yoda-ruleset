<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
   xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
   xmlns="http://datacite.org/schema/kernel-4">
  <xsl:output method="xml" version="1.0" encoding="UTF-8" indent="yes"/>

  <xsl:template match="/">
     <resource 
       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
       xsi:schemaLocation="http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4/metadata.xsd"
       >
       <identifier identifierType="DOI"><xsl:value-of select="metadata/PI_Datapackage" /></identifier>
        <creators>
          <xsl:apply-templates select="metadata/Creator" />
        </creators>
        <titles>
          <xsl:apply-templates select="metadata/Datapackage_Title" />
        </titles>
        <publisher>Utrecht University</publisher>
        <publicationYear>
	   <xsl:apply-templates select="metadata/Publication_Date" />
	</publicationYear>
        <subjects>
          <xsl:apply-templates select="metadata/Discipline" />
        </subjects>
        <contributors>
          <xsl:apply-templates select="metadata/Primary_Investigator" />
          <xsl:apply-templates select="metadata/ContributorName" />
        </contributors>
        <resourceType resourceTypeGeneral="Dataset">
          <xsl:choose>
          <xsl:when test="string-length(metadata/Research_Type)&lt;1">
            <xsl:text>Dataset</xsl:text>
          </xsl:when>
          <xsl:otherwise>
            <xsl:value-of select="metadata/Research_Type" />
          </xsl:otherwise>
          </xsl:choose>
        </resourceType>
      </resource>
  </xsl:template>

  <xsl:template match="metadata/Creator">
      <creator>
         <creatorName><xsl:value-of select="./CreatorName" /></creatorName>
         <xsl:variable name="identifierScheme"><xsl:value-of select="./Properties/PI_Type" /></xsl:variable>
         <nameIdentifier nameIdentifierScheme="{$identifierScheme}"><xsl:value-of select="./Properties/PI" /></nameIdentifier>
      </creator>
  </xsl:template>

  <xsl:template match="metadata/Publication_Date">
      <!-- 
        The date is in YYYY-MM-DD form, so we need to extract the first 4 digits for the year.
	xslt substring indexes start at 1 -->
      <xsl:value-of select="substring(., 1, 4)" />
  </xsl:template>

  <xsl:template match="metadata/Datapackage_Title">
    <title xml:lang="en-us"><xsl:value-of select="." /></title>
  </xsl:template>

  <xsl:template match="metadata/Discipline">
    <subject xml:lang="en-us"><xsl:value-of select="." /></subject>
  </xsl:template>

  <xsl:template match="metadata/Primary_Investigator">
    <contributor contributorType="ProjectLeader">
      <contributorName><xsl:value-of select="." /></contributorName>
    </contributor>
  </xsl:template>

  <xsl:template match="metdata/ContributorName">
    <contributor contributorType="Researcher">
      <contributorName><xsl:value-of select="." /></contributorName>
    </contributor>
  </xsl:template>

</xsl:stylesheet>
