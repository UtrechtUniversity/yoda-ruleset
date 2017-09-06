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
       <identifier identifierType="DOI"><xsl:value-of select="system/Persistent_Identifier_Datapackage" /></identifier>
        <titles>
          <xsl:apply-templates select="metadata/Title" />
        </titles>
        <descriptions>
          <description descriptionType="Abstract">
          <xsl:value-of select="metadata/Description" />
          </description>
        </descriptions>
        <publisher>Utrecht University</publisher>
        <publicationYear>
	   <xsl:apply-templates select="system/Publication_Date" />
	</publicationYear>

        <subjects>
          <xsl:apply-templates select="metadata/Discipline" />
	  <xsl:apply-templates select="metadata/Tag" />
        </subjects>

        <creators>
          <xsl:apply-templates select="metadata/Creator" />
        </creators>

        <contributors>
          <xsl:apply-templates select="metadata/Contributor" />
        </contributors>

        <xsl:apply-templates select="metadata/Version" />

        <dates>
          <xsl:if test="system/Last_Modified_Date">
            <date dateType="Updated"><xsl:value-of select="system/Last_Modified_Date" /></date>
          </xsl:if>
          <xsl:if test="metadata/Embargo_End_Date">
            <date dateType="Available"><xsl:value-of select="metadata/Embargo_End_Date" /></date>
          </xsl:if>
          <xsl:if test="metadata/Start_Collection_Date">
            <date dateType="Collected"><xsl:value-of select="metadata/Start_Collection_Date" />/<xsl:value-of select="metadata/End_Collection_Date" /></date>
          </xsl:if>
        </dates>
          
 	<rightsList>
          <xsl:apply-templates select="metadata/License" />
        </rightsList>
	
        <resourceType resourceTypeGeneral="Dataset">
            <xsl:text>Dataset</xsl:text>
        </resourceType>
      </resource>
  </xsl:template>

  <xsl:template match="metadata/Version">
    <xsl:copy />
  </xsl:template>

  <xsl:template match="metadata/Creator">
      <creator>
         <creatorName><xsl:value-of select="Name" /></creatorName>
         <xsl:apply-templates select="Properties/Persistent_Identifier" />
         <xsl:apply-templates select="Properties/Affiliation" />
      </creator>
  </xsl:template>

  <xsl:template match="system/Publication_Date">
      <!-- 
        The date is in YYYY-MM-DD form, so we need to extract the first 4 digits for the year.
	xslt substring indexes start at 1 -->
      <xsl:value-of select="substring(., 1, 4)" />
  </xsl:template>

  <xsl:template match="metadata/Title">
    <title xml:lang="en-us"><xsl:value-of select="." /></title>
  </xsl:template>

  <xsl:template match="metadata/Discipline">
    <subject subjectScheme="OECD FOS 2007"><xsl:value-of select="." /></subject>
  </xsl:template>

  <xsl:template match="metadata/Tag">
    <subject subjectScheme="Keyword"><xsl:value-of select="." /></subject>
  </xsl:template>

  <xsl:template match="metadata/Contributor">
    <contributor contributorType="Researcher">
      <contributorName><xsl:value-of select="Name" /></contributorName>
      <xsl:apply-templates select="Properties/Persistent_Identifier" /> 
    </contributor>
  </xsl:template>

  <xsl:template match="Properties/Persistent_Identifier">
        <xsl:variable name="identifierScheme"><xsl:value-of select="../Persistent_Identifier_Type" /></xsl:variable>
        <nameIdentifier nameIdentifierScheme="{$identifierScheme}"><xsl:value-of select="." /></nameIdentifier>
  </xsl:template>
  
  <xsl:template match="Properties/Affiliation">
	<Affiliation><xsl:value-of select="." /></Affiliation>
  </xsl:template>
 
<xsl:template match="metadata/License">
    <rights>
       <xsl:attribute name="rightsURI">
           <xsl:value-of select="./Properties/URL" />
       </xsl:attribute>
       <xsl:value-of select="./Name" />
    </rights>
</xsl:template>

</xsl:stylesheet>
