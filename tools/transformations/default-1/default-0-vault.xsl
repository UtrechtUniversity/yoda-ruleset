<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform"
    xmlns:yoda="https://yoda.uu.nl/schemas/default-0"
    xmlns="https://yoda.uu.nl/schemas/default-1" 
    exclude-result-prefixes="yoda">
   
  <xsl:output method="xml" version="1.0" encoding="UTF-8" omit-xml-declaration="no" indent="yes"/>

  <xsl:template match="/">
        <xsl:apply-templates select="/yoda:metadata"/>
  </xsl:template>

  <xsl:template match="/yoda:metadata">
    <metadata xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="https://yoda.uu.nl/schemas/default-1"  
            xsi:schemaLocation="https://yoda.uu.nl/schemas/default-1 vault.xsd">
        <xsl:if test="yoda:Title">
            <Title><xsl:value-of select="yoda:Title"/></Title>
        </xsl:if>
        <xsl:if test="yoda:Description">
            <Description><xsl:value-of select="yoda:Description"/></Description>
        </xsl:if>
       <xsl:if test="yoda:Discipline">
               <xsl:apply-templates select="yoda:Discipline"/>
    </xsl:if>
        <xsl:if test="yoda:Version">
            <Version>
               <xsl:value-of select="yoda:Version"/>
            </Version>
        </xsl:if>
        <xsl:if test="yoda:Language">
            <Language>
               <xsl:value-of select="yoda:Language"/>
            </Language>
        </xsl:if>
        <xsl:if test="yoda:Collected">
            <Collected>
               <Start_Date>
                    <xsl:value-of select="yoda:Collected/yoda:Start_Date"/>
               </Start_Date>
               <End_Date>
                    <xsl:value-of select="yoda:Collected/yoda:End_Date"/>
               </End_Date>
            </Collected>
        </xsl:if>
       <xsl:if test="yoda:Tag">
               <xsl:apply-templates select="yoda:Tag"/>
       </xsl:if>

        <xsl:if test="yoda:Related_Datapackage">
            <xsl:apply-templates select="yoda:Related_Datapackage"/>
        </xsl:if>

        <xsl:if test="yoda:Covered_Geolocation_Place">
            <xsl:apply-templates select="yoda:Covered_Geolocation_Place"/>
        </xsl:if>

        <xsl:if test="yoda:Retention_Period">
            <Retention_Period>
               <xsl:value-of select="yoda:Retention_Period"/>
           </Retention_Period>
        </xsl:if>
        <xsl:if test="yoda:Retention_Information">
            <Retention_Information>
               <xsl:value-of select="yoda:Retention_Information"/>
            </Retention_Information>
        </xsl:if>
        <xsl:if test="yoda:Embargo_End_Date">
            <Embargo_End_Date>
               <xsl:value-of select="yoda:Embargo_End_Date"/>
            </Embargo_End_Date>
        </xsl:if>
        <xsl:if test="yoda:Data_Classification">
            <Data_Classification>
               <xsl:value-of select="yoda:Data_Classification"/>
            </Data_Classification>
        </xsl:if>

        <Data_Type>Dataset</Data_Type>

        <xsl:if test="yoda:Collection_Name">
            <Collection_Name>
               <xsl:value-of select="yoda:Collection_Name"/>
            </Collection_Name>
        </xsl:if>
        <xsl:if test="yoda:Funding_Reference">
               <xsl:apply-templates select="yoda:Funding_Reference"/>
        </xsl:if>

        <xsl:if test="yoda:Creator">
            <xsl:apply-templates select="yoda:Creator"/>
        </xsl:if>

        <xsl:if test="yoda:Contributor">
            <xsl:apply-templates select="yoda:Contributor"/>
        </xsl:if>

        <xsl:if test="yoda:License">
            <License>
               <xsl:value-of select="yoda:License"/>
            </License>
        </xsl:if>
        <xsl:if test="yoda:Data_Access_Restriction">
            <Data_Access_Restriction>
               <xsl:value-of select="yoda:Data_Access_Restriction"/>
            </Data_Access_Restriction>
        </xsl:if>

        <xsl:if test="yoda:System">
            <System>
                <Last_Modified_Date><xsl:value-of select="yoda:System/yoda:Last_Modified_Date"/></Last_Modified_Date>
                <Persistent_Identifier_Datapackage>
                    <Identifier_Scheme><xsl:value-of select="yoda:System/yoda:Persistent_Identifier_Datapackage/yoda:Identifier_Scheme"/></Identifier_Scheme>
                    <Identifier><xsl:value-of select="yoda:System/yoda:Persistent_Identifier_Datapackage/yoda:Identifier"/></Identifier>
                </Persistent_Identifier_Datapackage>
                <Publication_Date><xsl:value-of select="yoda:System/yoda:Publication_Date"/></Publication_Date>
                <xsl:if test="yoda:System/yoda:Open_Access_Link">
                    <Open_Access_Link><xsl:value-of select="yoda:System/yoda:Open_Access_Link"/></Open_Access_Link>
                </xsl:if>                
                <xsl:if test="yoda:System/yoda:License_URI">
                    <License_URI><xsl:value-of select="yoda:System/yoda:License_URI"/></License_URI>
                </xsl:if>       
            </System>
        </xsl:if>

    </metadata>
  </xsl:template>

  <xsl:template match="yoda:Contributor">
      <Contributor>
          <Name><xsl:value-of select="yoda:Name" /></Name>
          <Properties>
              <Contributor_Type><xsl:value-of select="yoda:Properties/yoda:Contributor_Type" /></Contributor_Type>
              <xsl:apply-templates select="yoda:Properties/yoda:Affiliation" />
              <xsl:apply-templates select="yoda:Properties/yoda:Person_Identifier" />
          </Properties>
      </Contributor>
  </xsl:template>   

  <xsl:template match="yoda:Creator">
      <Creator>
          <Name><xsl:value-of select="yoda:Name" /></Name>
          <Properties>
             <xsl:apply-templates select="yoda:Properties/yoda:Affiliation" />
             <xsl:apply-templates select="yoda:Properties/yoda:Person_Identifier" />
          </Properties>
      </Creator>
  </xsl:template>   

  <xsl:template match="yoda:Properties/yoda:Affiliation">
      <Affiliation>
          <xsl:value-of select="." />
      </Affiliation>
  </xsl:template>

  <xsl:template match="yoda:Properties/yoda:Person_Identifier">
      <Person_Identifier>
          <Name_Identifier_Scheme><xsl:value-of select="yoda:Name_Identifier_Scheme" /></Name_Identifier_Scheme>
          <Name_Identifier><xsl:value-of select="yoda:Name_Identifier" /></Name_Identifier>
      </Person_Identifier>
  </xsl:template>

  <xsl:template match="yoda:Related_Datapackage">
      <Related_Datapackage>
          <Relation_Type><xsl:value-of select="yoda:Relation_Type" /></Relation_Type>
          <Properties>
              <Title><xsl:value-of select="yoda:Properties/yoda:Title" /></Title>
              <Persistent_Identifier>
                  <Identifier_Scheme><xsl:value-of select="yoda:Properties/yoda:Persistent_Identifier/yoda:Identifier_Scheme" /></Identifier_Scheme>
                  <Identifier><xsl:value-of select="yoda:Properties/yoda:Persistent_Identifier/yoda:Identifier" /></Identifier>
              </Persistent_Identifier>
          </Properties>
      </Related_Datapackage>
  </xsl:template> 

  <xsl:template match="yoda:Funding_Reference">
      <Funding_Reference>
          <Funder_Name><xsl:value-of select="yoda:Funder_Name" /></Funder_Name>
          <Properties>
              <Award_Number><xsl:value-of select="yoda:Properties/yoda:Award_Number" /></Award_Number>
          </Properties>
      </Funding_Reference>
  </xsl:template> 

  <xsl:template match="yoda:Tag">
      <Tag>
          <xsl:value-of select="." />
      </Tag>
  </xsl:template>

  <xsl:template match="yoda:Discipline">
      <Discipline>
          <xsl:value-of select="." />
      </Discipline>
  </xsl:template>

  <xsl:template match="yoda:Covered_Geolocation_Place">
       <Covered_Geolocation_Place>
           <xsl:value-of select="." />
       </Covered_Geolocation_Place>
  </xsl:template>

</xsl:stylesheet>
