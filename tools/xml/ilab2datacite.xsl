<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
   xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
   xmlns="http://datacite.org/schema/kernel-4">
  <xsl:output method="xml" version="1.0" encoding="UTF-8" indent="yes"/>

  <xsl:template match="/">
	<xsl:apply-templates select="/metadata"/>
  </xsl:template>

  <xsl:template match="/metadata">
     <resource 
       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
       xsi:schemaLocation="http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4/metadata.xsd"
       >
       <identifier identifierType="DOI">
          <xsl:value-of select="system/Persistent_Identifier_Datapackage[Identifier_Scheme='DOI']/Identifier"/>
       </identifier>

        <titles>
          <xsl:apply-templates select="Title"/>
        </titles>
        <descriptions>
          <description descriptionType="Abstract">
          <xsl:value-of select="Description"/>
          </description>
        </descriptions>
        <publisher>Utrecht University</publisher>
        <publicationYear>
	   <xsl:apply-templates select="system/Publication_Date"/>
	</publicationYear>

        <subjects>
          <xsl:apply-templates select="Discipline"/>
	  <xsl:apply-templates select="Tag"/>
        </subjects>

        <creators>
          <xsl:apply-templates select="Creator"/>
        </creators>
	
	<xsl:if test="Contributor">
		<contributors>
		  <xsl:apply-templates select="metadata/Contributor"/>
		</contributors>
	</xsl:if>


        <dates>
          <xsl:if test="system/Last_Modified_Date">
            <date dateType="Updated"><xsl:value-of select="system/Last_Modified_Date"/></date>
          </xsl:if>
          <xsl:if test="Embargo_End_Date">
            <date dateType="Available"><xsl:value-of select="Embargo_End_Date"/></date>
          </xsl:if>
          <xsl:if test="Collected">
            <date dateType="Collected"><xsl:value-of select="Collected/Start_Date" />/<xsl:value-of select="Collected/End_Date"/></date>
          </xsl:if>
        </dates>
        <xsl:apply-templates select="Version"/>
 	<rightsList>
          <xsl:apply-templates select="License"/>
        </rightsList>
	
        <resourceType resourceTypeGeneral="Dataset">
            <xsl:text>Dataset</xsl:text>
        </resourceType>

        <xsl:if test="Related_Datapackage">
          <relatedIdentifiers>
            <xsl:apply-templates select="Related_Datapackage"/>
          </relatedIdentifiers>
        </xsl:if>
	
	<xsl:if test="Covered_Geolocation_Place">
          <geoLocations>
            <xsl:apply-templates select="Covered_Geolocation_Place"/>
          </geoLocations>
        </xsl:if>

	<xsl:if test="Funding_Reference">
	  <fundingReferences>
	    <xsl:apply-templates select="Funding_Reference"/>
	  </fundingReferences>
	</xsl:if>
      </resource>
  </xsl:template>

  <xsl:template match="Version">
    <version><xsl:value-of select="."/></version>
  </xsl:template>

  <xsl:template match="Creator">
      <creator>
         <creatorName><xsl:value-of select="Name"/></creatorName>
         <xsl:apply-templates select="Properties/Person_Identifier"/>
         <xsl:apply-templates select="Properties/Affiliation"/>
      </creator>
  </xsl:template>

  <xsl:template match="system/Publication_Date">
      <!-- 
        The date is in YYYY-MM-DD form, so we need to extract the first 4 digits for the year.
	xslt substring indexes start at 1 -->
      <xsl:value-of select="substring(., 1, 4)" />
  </xsl:template>

  <xsl:template match="Title">
    <title xml:lang="en-us"><xsl:value-of select="." /></title>
  </xsl:template>

  <xsl:template match="Discipline">
    <subject subjectScheme="OECD FOS 2007"><xsl:value-of select="." /></subject>
  </xsl:template>

  <xsl:template match="Tag">
    <subject subjectScheme="Keyword"><xsl:value-of select="." /></subject>
  </xsl:template>

  <xsl:template match="Contributor">
    <contributor>
      <xsl:attribute name="contributorType">
	<xsl:value-of select="./Properties/Contributor_Type"/>
      </xsl:attribute>
      <contributorName><xsl:value-of select="Name" /></contributorName>
      <xsl:apply-templates select="Properties/Person_Identifier" /> 
    </contributor>
  </xsl:template>

  <xsl:template match="Properties/Person_Identifier">
        <nameIdentifier>
           <xsl:attribute name="nameIdentifierScheme">
              <xsl:value-of select="Name_Identifier_Scheme" />
           </xsl:attribute>
           <xsl:value-of select="Name_Identifier" />
        </nameIdentifier>
  </xsl:template>
  
  <xsl:template match="Properties/Affiliation">
	<affiliation><xsl:value-of select="." /></affiliation>
  </xsl:template>
 
<xsl:template match="License">
    <rights>
       <xsl:attribute name="rightsURI">
           <xsl:value-of select="/metadata/system/License_URL" />
       </xsl:attribute>
       <xsl:value-of select="." />
    </rights>
</xsl:template>

<xsl:template match="Language">
 <language><xsl:value-of select="substring(., 1, 2)"/></language>    
</xsl:template>

<xsl:template match="Related_Datapackage">
  <relatedIdentifier>
     <xsl:attribute name="relatedIdentifierType">
       <xsl:value-of select="Properties/Persistent_Identifier/Identifier_Scheme" />
     </xsl:attribute>
     <xsl:attribute name="relationType"><xsl:value-of select="substring-before(Relation_Type, ':')"/></xsl:attribute>
     <xsl:value-of select="Properties/Persistent_Identifier/Identifier" />
  </relatedIdentifier>
</xsl:template>

<xsl:template match="Covered_Geolocation_Place">
  <geoLocation>
    <geoLocationPlace><xsl:value-of select="." /></geoLocationPlace>
  </geoLocation>
</xsl:template>

<xsl:template match="Funding_Reference">
   <fundingReference>
     <funderName><xsl:value-of select="./Funder_Name"/></funderName>
     <xsl:if test="./Properties/Award_Number">
       <awardNumber><xsl:value-of select="./Properties/Award_Number"/></awardNumber>
     </xsl:if>
   </fundingReference>
</xsl:template>

</xsl:stylesheet>
