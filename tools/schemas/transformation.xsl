<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

  <xsl:template match="/">
        <xsl:apply-templates select="/metadata"/>
  </xsl:template>

  <xsl:template match="/metadata">
    <metadata xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:noNamespaceSchemaLocation="https://utrechtuniversity.github.io/yoda-schemas/default research.xsd">
        <xsl:if test="Title">
            <Title><xsl:value-of select="Title"/></Title>
        </xsl:if>
        <xsl:if test="Description">
            <Description><xsl:value-of select="Description"/></Description>
        </xsl:if>
       <xsl:if test="Discipline">
               <xsl:apply-templates select="Discipline"/>
    </xsl:if>
        <xsl:if test="Version">
            <Version>
               <xsl:value-of select="Version"/>
            </Version>
        </xsl:if>
        <xsl:if test="Language">
            <Language>
               <xsl:value-of select="Language"/>
            </Language>
        </xsl:if>
        <xsl:if test="Collected">
            <Collected>
               <Start_Date>
                    <xsl:value-of select="Collected/Start_Date"/>
               </Start_Date>
               <End_Date>
                    <xsl:value-of select="Collected/End_Date"/>
               </End_Date>
            </Collected>
        </xsl:if>
       <xsl:if test="Tag">
               <xsl:apply-templates select="Tag"/>
       </xsl:if>

        <xsl:if test="Related_Datapackage">
            <xsl:apply-templates select="Related_Datapackage"/>
        </xsl:if>

        <xsl:if test="Covered_Geolocation_Place">
            <xsl:apply-templates select="Covered_Geolocation_Place"/>
        </xsl:if>

        <xsl:if test="Retention_Period">
            <Retention_Period>
               <xsl:value-of select="Retention_Period"/>
           </Retention_Period>
        </xsl:if>
        <xsl:if test="Retention_Information">
            <Retention_Information>
               <xsl:value-of select="Retention_Information"/>
            </Retention_Information>
        </xsl:if>
        <xsl:if test="Embargo_End_Date">
            <Embargo_End_Date>
               <xsl:value-of select="Embargo_End_Date"/>
            </Embargo_End_Date>
        </xsl:if>
        <xsl:if test="Data_Classification">
            <Data_Classification>
               <xsl:value-of select="Data_Classification"/>
            </Data_Classification>
        </xsl:if>
        <xsl:if test="Collection_Name">
            <Collection_Name>
               <xsl:value-of select="Collection_Name"/>
            </Collection_Name>
        </xsl:if>
        <xsl:if test="Funding_Reference">
               <xsl:apply-templates select="Funding_Reference"/>
        </xsl:if>

        <xsl:if test="Creator">
            <xsl:apply-templates select="Creator"/>
        </xsl:if>

        <xsl:if test="Contributor">
            <xsl:apply-templates select="Contributor"/>
        </xsl:if>

        <xsl:if test="License">
            <License>
               <xsl:value-of select="License"/>
            </License>
        </xsl:if>
        <xsl:if test="Data_Access_Restriction">
            <Data_Access_Restriction>
               <xsl:value-of select="Data_Access_Restriction"/>
            </Data_Access_Restriction>
        </xsl:if>

        <Data_Type>Dataset</Data_Type>

        <xsl:if test="System">
            <System>
                <Last_Modified_Date><xsl:value-of select="System/Last_Modified_Date"/></Last_Modified_Date>
                <Persistent_Identifier_Datapackage>
                    <Identifier_Scheme><xsl:value-of select="System/Persistent_Identifier_Datapackage/Identifier_Scheme"/></Identifier_Scheme>
                    <Identifier><xsl:value-of select="System/Persistent_Identifier_Datapackage/Identifier"/></Identifier>
                </Persistent_Identifier_Datapackage>
                <Publication_Date><xsl:value-of select="System/Publication_Date"/></Publication_Date>
                <xsl:if test="System/Open_Access_Link">
                    <Open_Access_Link><xsl:value-of select="System/Open_Access_Link"/></Open_Access_Link>
                </xsl:if>                
                <xsl:if test="System/License_URI">
                    <License_URI><xsl:value-of select="System/License_URI"/></License_URI>
                </xsl:if>       
            </System>
        </xsl:if>

    </metadata>
  </xsl:template>

  <xsl:template match="Contributor">
      <Contributor>
          <Name><xsl:value-of select="Name" /></Name>
          <Properties>
              <Contributor_Type><xsl:value-of select="Properties/Contributor_Type" /></Contributor_Type>
              <xsl:apply-templates select="Properties/Affiliation" />
              <xsl:apply-templates select="Properties/Person_Identifier" />
          </Properties>
      </Contributor>
  </xsl:template>   

  <xsl:template match="Creator">
      <Creator>
          <Name><xsl:value-of select="Name" /></Name>
          <Properties>
             <xsl:apply-templates select="Properties/Affiliation" />
             <xsl:apply-templates select="Properties/Person_Identifier" />
          </Properties>
      </Creator>
  </xsl:template>   

  <xsl:template match="Properties/Affiliation">
      <Affiliation>
          <xsl:value-of select="." />
      </Affiliation>
  </xsl:template>

  <xsl:template match="Properties/Person_Identifier">
      <Person_Identifier>
          <Name_Identifier_Scheme><xsl:value-of select="Name_Identifier_Scheme" /></Name_Identifier_Scheme>
          <Name_Identifier><xsl:value-of select="Name_Identifier" /></Name_Identifier>
      </Person_Identifier>
  </xsl:template>

  <xsl:template match="Related_Datapackage">
      <Related_Datapackage>
          <Relation_Type><xsl:value-of select="Relation_Type" /></Relation_Type>
          <Properties>
              <Title><xsl:value-of select="Properties/Title" /></Title>
              <Persistent_Identifier>
                  <Identifier_Scheme><xsl:value-of select="Properties/Persistent_Identifier/Identifier_Scheme" /></Identifier_Scheme>
                  <Identifier><xsl:value-of select="Properties/Persistent_Identifier/Identifier" /></Identifier>
              </Persistent_Identifier>
          </Properties>
      </Related_Datapackage>
  </xsl:template> 

  <xsl:template match="Funding_Reference">
      <Funding_Reference>
          <Funder_Name><xsl:value-of select="Funder_Name" /></Funder_Name>
          <Properties>
              <Award_Number><xsl:value-of select="Properties/Award_Number" /></Award_Number>
          </Properties>
      </Funding_Reference>
  </xsl:template> 

  <xsl:template match="Tag">
      <Tag>
          <xsl:value-of select="." />
      </Tag>
  </xsl:template>

  <xsl:template match="Discipline">
      <Discipline>
          <xsl:value-of select="." />
      </Discipline>
  </xsl:template>

  <xsl:template match="Covered_Geolocation_Place">
       <Covered_Geolocation_Place>
           <xsl:value-of select="." />
       </Covered_Geolocation_Place>
  </xsl:template>

</xsl:stylesheet>
