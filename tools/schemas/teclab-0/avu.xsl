<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
  xmlns:yoda="https://yoda.uu.nl/schemas/default-1"
  xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="xml" version="1.0" encoding="UTF-8" indent="yes"/>

  <!-- Apply templates on all nodes under metadata. -->
  <xsl:template match="/yoda:metadata">
    <metadata>
      <xsl:apply-templates/>
    </metadata>
  </xsl:template>

  <!-- Transform all nodes with children. -->
  <xsl:template match="*[*]">
    <xsl:variable name="attr" as="xs:string" select="local-name(.)" />
    <xsl:variable name="sn" as="xs:number" select="count(preceding-sibling::*[local-name()=$attr])" />

    <!-- Transform all child nodes without children. -->
    <xsl:for-each select="*[not(*)]">
      <xsl:variable name="subAttr" as="xs:string" select="local-name(.)" />
      <xsl:variable name="subSn" as="xs:number" select="count(preceding-sibling::*[local-name()=$subAttr])" />
      <AVU>
        <Attribute>usr_<xsl:number value="$sn" format="1" />_<xsl:value-of select="$attr" />_<xsl:number value="$subSn" format="1" />_<xsl:value-of select="$subAttr" /></Attribute>
        <Value><xsl:value-of select="." /></Value>
      </AVU>
    </xsl:for-each>

    <!-- Transform all child nodes with children. -->
    <xsl:for-each select="*[*]">
      <xsl:variable name="subAttr" as="xs:string" select="local-name(.)" />
      <xsl:variable name="subSn" as="xs:number" select="count(preceding-sibling::*[local-name()=$subAttr])" />
      <xsl:for-each select="*[not(*)]">
        <xsl:variable name="subSubAttr" as="xs:string" select="local-name(.)" />
        <AVU>
          <Attribute>usr_<xsl:number value="$sn" format="1" />_<xsl:value-of select="$attr" />_<xsl:number value="$subSn" format="1" />_<xsl:value-of select="$subAttr" />_<xsl:value-of select="$subSubAttr" /></Attribute>
          <Value><xsl:value-of select="." /></Value>
        </AVU>
      </xsl:for-each>
      <xsl:for-each select="*[*]">
        <xsl:variable name="subSubAttr" as="xs:string" select="local-name(.)" />
        <xsl:variable name="subSubSn" as="xs:number" select="count(preceding-sibling::*[local-name()=$subSubAttr])" />
        <xsl:for-each select="*[not(*)]">
          <xsl:variable name="subSubSubAttr" as="xs:string" select="local-name(.)" />
          <AVU>
            <Attribute>usr_<xsl:number value="$sn" format="1" />_<xsl:value-of select="$attr" />_<xsl:number value="$subSn" format="1" />_<xsl:value-of select="$subAttr" />_<xsl:number value="$subSubSn" format="1" />_<xsl:value-of select="$subSubAttr" />_<xsl:value-of select="$subSubSubAttr" /></Attribute>
            <Value><xsl:value-of select="." /></Value>
          </AVU>
        </xsl:for-each>
      </xsl:for-each>
    </xsl:for-each>
  </xsl:template>

  <!-- Transform all nodes without children. -->
  <xsl:template match="//*[not(*)]">
    <xsl:variable name="attr" as="xs:string" select="local-name(.)" />
    <xsl:variable name="sn" as="xs:number" select="count(preceding-sibling::*[local-name()=$attr])" />
    <AVU>
      <Attribute>usr_<xsl:number value="$sn" format="1" />_<xsl:value-of select="$attr" /></Attribute>
      <Value><xsl:value-of select="." /></Value>
    </AVU>
  </xsl:template>

  <xsl:template match="text()"/>

</xsl:stylesheet>
