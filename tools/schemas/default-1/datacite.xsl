<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
   xmlns:yoda="https://yoda.uu.nl/schemas/default-1"
   xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
   xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
   xmlns="http://datacite.org/schema/kernel-4">
  <xsl:output method="xml" version="1.0" encoding="UTF-8" indent="yes"/>

  <xsl:template match="/">
        <xsl:apply-templates select="/yoda:metadata"/>
  </xsl:template>

  <xsl:template match="/yoda:metadata">
     <resource
       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
       xsi:schemaLocation="http://datacite.org/schema/kernel-4 http://schema.datacite.org/meta/kernel-4/metadata.xsd"
       >
       <identifier identifierType="DOI">
          <xsl:value-of select="yoda:System/yoda:Persistent_Identifier_Datapackage[yoda:Identifier_Scheme='DOI']/yoda:Identifier"/>
       </identifier>

        <titles>
          <xsl:apply-templates select="yoda:Title"/>
        </titles>
        <descriptions>
          <description descriptionType="Abstract">
          <xsl:value-of select="yoda:Description"/>
          </description>
        </descriptions>
        <publisher>Utrecht University</publisher>
        <publicationYear>
           <xsl:apply-templates select="yoda:System/yoda:Publication_Date"/>
        </publicationYear>

        <xsl:if test="Discipline or Tag">
          <subjects>
            <xsl:apply-templates select="yoda:Discipline"/>
            <xsl:apply-templates select="yoda:Tag"/>
          </subjects>
        </xsl:if>

        <creators>
          <xsl:apply-templates select="yoda:Creator"/>
        </creators>

        <xsl:if test="Contributor">
                <contributors>
                  <xsl:apply-templates select="yoda:Contributor"/>
                </contributors>
        </xsl:if>

        <dates>
          <xsl:if test="System/Last_Modified_Date">
            <date dateType="Updated"><xsl:value-of select="yoda:System/yoda:Last_Modified_Date"/></date>
          </xsl:if>
          <xsl:if test="Embargo_End_Date">
            <date dateType="Available"><xsl:value-of select="yoda:Embargo_End_Date"/></date>
          </xsl:if>
          <xsl:if test="Collected">
            <date dateType="Collected"><xsl:value-of select="yoda:Collected/yoda:Start_Date" />/<xsl:value-of select="yoda:Collected/yoda:End_Date"/></date>
          </xsl:if>
        </dates>
        <xsl:apply-templates select="yoda:Version"/>
        <rightsList>
          <xsl:apply-templates select="yoda:License"/>
          <xsl:apply-templates select="yoda:Data_Access_Restriction"/>
        </rightsList>

        <resourceType resourceTypeGeneral="Dataset">
            <xsl:value-of select="yoda:Data_Type"/>
        </resourceType>

        <xsl:if test="(yoda:Related_Datapackage/yoda:Properties/yoda:Persistent_Identifier/yoda:Identifier) and (yoda:Related_Datapackage/yoda:Relation_Type)">
          <relatedIdentifiers>
            <xsl:apply-templates select="yoda:Related_Datapackage"/>
          </relatedIdentifiers>
        </xsl:if>

        <xsl:if test="yoda:Covered_Geolocation_Place">
          <geoLocations>
            <xsl:apply-templates select="yoda:Covered_Geolocation_Place"/>
          </geoLocations>
        </xsl:if>

        <xsl:if test="yoda:Funding_Reference">
          <fundingReferences>
            <xsl:apply-templates select="yoda:Funding_Reference"/>
          </fundingReferences>
        </xsl:if>
      </resource>
  </xsl:template>

  <xsl:template match="yoda:Version">
    <version><xsl:value-of select="."/></version>
  </xsl:template>

  <xsl:template match="yoda:Creator">
      <creator>
         <creatorName><xsl:value-of select="yoda:Name"/></creatorName>
         <xsl:apply-templates select="yoda:Properties/yoda:Person_Identifier"/>
         <xsl:apply-templates select="yoda:Properties/yoda:Affiliation"/>
      </creator>
  </xsl:template>

  <xsl:template match="yoda:System/yoda:Publication_Date">
      <!--
        The date is in YYYY-MM-DD form, so we need to extract the first 4 digits for the year.
        xslt substring indexes start at 1 -->
      <xsl:value-of select="substring(., 1, 4)" />
  </xsl:template>

  <xsl:template match="yoda:Title">
    <title xml:lang="en-us"><xsl:value-of select="." /></title>
  </xsl:template>

  <xsl:template match="yoda:Discipline">
    <subject subjectScheme="OECD FOS 2007"><xsl:value-of select="." /></subject>
  </xsl:template>

  <xsl:template match="yoda:Tag">
    <subject subjectScheme="Keyword"><xsl:value-of select="." /></subject>
  </xsl:template>

  <xsl:template match="yoda:Contributor">
    <contributor>
      <xsl:attribute name="contributorType">
        <xsl:value-of select="yoda:Properties/yoda:Contributor_Type"/>
      </xsl:attribute>
      <contributorName><xsl:value-of select="yoda:Name" /></contributorName>
      <xsl:apply-templates select="yoda:Properties/yoda:Person_Identifier" />
      <xsl:apply-templates select="yoda:Properties/yoda:Affiliation"/>
    </contributor>
  </xsl:template>

  <xsl:template match="yoda:Properties/yoda:Person_Identifier">
        <nameIdentifier>
           <xsl:attribute name="nameIdentifierScheme">
              <xsl:value-of select="yoda:Name_Identifier_Scheme" />
           </xsl:attribute>
           <xsl:value-of select="yoda:Name_Identifier" />
        </nameIdentifier>
  </xsl:template>

  <xsl:template match="yoda:Properties/yoda:Affiliation">
        <affiliation><xsl:value-of select="." /></affiliation>
  </xsl:template>

<xsl:template match="yoda:License">
  <rights>
     <xsl:if test="/yoda:metadata/yoda:System/yoda:License_URI">
       <xsl:attribute name="rightsURI"><xsl:value-of select="/yoda:metadata/yoda:System/yoda:License_URI"/></xsl:attribute>
     </xsl:if>
     <xsl:value-of select="." />
  </rights>
</xsl:template>

<xsl:template match="yoda:Data_Access_Restriction[starts-with(.,'Open')]">
  <rights><xsl:attribute name="rightsURI">info:eu-repo/semantics/openAccess</xsl:attribute>Open Access</rights>
</xsl:template>
<xsl:template match="yoda:Data_Access_Restriction[starts-with(.,'Restricted')]">
  <rights><xsl:attribute name="rightsURI">info:eu-repo/semantics/restrictedAccess</xsl:attribute>Restricted Access</rights>
</xsl:template>
<xsl:template match="yoda:Data_Access_Restriction[.='Closed']">
  <rights><xsl:attribute name="rightsURI">info:eu-repo/semantics/closedAccess</xsl:attribute>Closed Access</rights>
</xsl:template>

<xsl:template match="yoda:Language">
  <language><xsl:value-of select="substring(., 1, 2)"/></language>
</xsl:template>

<xsl:template match="yoda:Related_Datapackage">

   <xsl:if test="(yoda:Properties/yoda:Persistent_Identifier/yoda:Identifier) and (yoda:Relation_Type)">
      <relatedIdentifier>
         <xsl:attribute name="relatedIdentifierType">
           <xsl:value-of select="yoda:Properties/yoda:Persistent_Identifier/yoda:Identifier_Scheme" />
         </xsl:attribute>
         <xsl:attribute name="relationType"><xsl:value-of select="substring-before(yoda:Relation_Type, ':')"/></xsl:attribute>
         <xsl:value-of select="yoda:Properties/yoda:Persistent_Identifier/yoda:Identifier" />
      </relatedIdentifier>
    </xsl:if>
</xsl:template>

<xsl:template match="yoda:Covered_Geolocation_Place">
  <geoLocation>
    <geoLocationPlace><xsl:value-of select="." /></geoLocationPlace>
  </geoLocation>
</xsl:template>

<xsl:template match="yoda:Funding_Reference">
   <fundingReference>
     <funderName><xsl:value-of select="./yoda:Funder_Name"/></funderName>
     <xsl:if test="./yoda:Properties/yoda:Award_Number">
       <awardNumber><xsl:value-of select="./yoda:Properties/yoda:Award_Number"/></awardNumber>
     </xsl:if>
   </fundingReference>
</xsl:template>

</xsl:stylesheet>
