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
       <identifier identifierType="DOI">
          <xsl:value-of select="metadata/system/Persistent_Identifier_Datapackage[Identifier_Scheme='DOI']/Identifier"/>
       </identifier>

        <titles>
          <xsl:apply-templates select="metadata/Title"/>
        </titles>
        <descriptions>
          <description descriptionType="Abstract">
          <xsl:value-of select="metadata/Description"/>
          </description>
        </descriptions>
        <publisher>Utrecht University</publisher>
        <publicationYear>
	   <xsl:apply-templates select="metadata/system/Publication_Date"/>
	</publicationYear>

        <subjects>
          <xsl:apply-templates select="metadata/Discipline"/>
	  <xsl:apply-templates select="metadata/Tag"/>
        </subjects>

        <creators>
          <xsl:apply-templates select="metadata/Creator"/>
        </creators>
	
	<xsl:if test="metadata/Contributor">
		<contributors>
		  <xsl:apply-templates select="metadata/Contributor"/>
		</contributors>
	</xsl:if>


        <dates>
          <xsl:if test="metadata/system/Last_Modified_Date">
            <date dateType="Updated"><xsl:value-of select="metadata/system/Last_Modified_Date"/></date>
          </xsl:if>
          <xsl:if test="metadata/Embargo_End_Date">
            <date dateType="Available"><xsl:value-of select="metadata/Embargo_End_Date"/></date>
          </xsl:if>
          <xsl:if test="metadata/Collected">
            <date dateType="Collected"><xsl:value-of select="metadata/Collected/Start_Date" />/<xsl:value-of select="metadata/Collected/End_Date"/></date>
          </xsl:if>
        </dates>
        <xsl:apply-templates select="metadata/Version"/>
 	<rightsList>
          <xsl:apply-templates select="metadata/License"/>
        </rightsList>
	
        <resourceType resourceTypeGeneral="Dataset">
            <xsl:text>Dataset</xsl:text>
        </resourceType>

        <xsl:if test="metadata/Related_Datapackage">
          <relatedIdentifiers>
            <xsl:apply-templates select="metadata/Related_Datapackage"/>
          </relatedIdentifiers>
        </xsl:if>
	
	<xsl:if test="metadata/Covered_Geolocation_Place">
          <geoLocations>
            <xsl:apply-templates select="metadata/Covered_Geolocation_Place"/>
          </geoLocations>
        </xsl:if>

	<xsl:if test="metadata/Funding_Reference">
	  <fundingReferences>
	    <xsl:apply-templates select="metadata/Funding_Reference"/>
	  </fundingReferences>
	</xsl:if>
      </resource>
  </xsl:template>

  <xsl:template match="metadata/Version">
    <version><xsl:value-of select="."/></version>
  </xsl:template>

  <xsl:template match="metadata/Creator">
      <creator>
         <creatorName><xsl:value-of select="Name"/></creatorName>
         <xsl:apply-templates select="Properties/Persistent_Identifier"/>
         <xsl:apply-templates select="Properties/Affiliation"/>
      </creator>
  </xsl:template>

  <xsl:template match="metadata/system/Publication_Date">
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
           <xsl:value-of select="Identifier" />
        </nameIdentifier>
  </xsl:template>
  
  <xsl:template match="Properties/Affiliation">
	<affiliation><xsl:value-of select="." /></affiliation>
  </xsl:template>
 
<xsl:template match="metadata/License">
    <rights>
       <xsl:attribute name="rightsURI">
           <xsl:value-of select="/metadata/system/License_URL" />
       </xsl:attribute>
       <xsl:value-of select="." />
    </rights>
</xsl:template>

<xsl:template match="metadata/Language">
 <language><xsl:value-of select="substring(., 1, 2)"/></language>    
</xsl:template>

<xsl:template match="metadata/Related_Datapackage">
  <relatedIdentifier>
     <xsl:attribute name="relatedIdentifierType">
       <xsl:value-of select="Properties/Persistent_Identifier/Identifier_Scheme" />
     </xsl:attribute>
     <xsl:attribute name="relationType"><xsl:value-of select="substring-before(Relation_Type, ':')"/></xsl:attribute>
     <xsl:value-of select="Properties/Persistent_Identifier/Identifier" />
  </relatedIdentifier>
</xsl:template>

<xsl:template match="metadata/Covered_Geolocation_Place">
  <geoLocation>
    <geoLocationPlace><xsl:value-of select="." /></geoLocationPlace>
  </geoLocation>
</xsl:template>

<xsl:template match="metadata/Funding_Reference">
   <fundingReference>
     <funderName><xsl:value-of select="./Funder_Name"/></funderName>
     <xsl:if test="./Properties/Award_Number">
       <awardNumber><xsl:value-of select="./Properties/Award_Number"/></awardNumber>
     </xsl:if>
   </fundingReference>
</xsl:template>

</xsl:stylesheet>
