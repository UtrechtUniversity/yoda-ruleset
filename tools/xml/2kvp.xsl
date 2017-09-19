<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="text" encoding="UTF-8" indent="no"/>

  <!-- Apply templates on all nodes under metadata. -->
  <xsl:template match="/metadata">
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
        <xsl:text>usr_</xsl:text><xsl:number value="$sn" format="1" /><xsl:text>_</xsl:text><xsl:value-of select="$attr" /><xsl:text>_</xsl:text><xsl:number value="$subSn" format="1" />_<xsl:value-of select="$subAttr" /><xsl:text>=</xsl:text><xsl:value-of select="." /><xsl:if test="position() &lt; last()"><xsl:text>%</xsl:text></xsl:if>
    </xsl:for-each>

    <!-- Transform all child nodes with children. -->
    <xsl:for-each select="*[*]">
      <xsl:variable name="subAttr" as="xs:string" select="local-name(.)" />
      <xsl:variable name="subSn" as="xs:number" select="count(preceding-sibling::*[local-name()=$subAttr])" />
      <xsl:for-each select="*[not(*)]">
        <xsl:variable name="subSubAttr" as="xs:string" select="local-name(.)" />
          <xsl:text>usr_</xsl:text><xsl:number value="$sn" format="1" /><xsl:text>_</xsl:text><xsl:value-of select="$attr" /><xsl:text>_</xsl:text><xsl:number value="$subSn" format="1" /><xsl:text>_</xsl:text><xsl:value-of select="$subAttr" /><xsl:text>_</xsl:text><xsl:value-of select="$subSubAttr" /><xsl:text>=</xsl:text><xsl:value-of select="." />
	<xsl:if test="position() &lt; last()"><xsl:text>%</xsl:text></xsl:if>	
      </xsl:for-each>
    </xsl:for-each>
  </xsl:template>

  <!-- Transform all nodes without children. -->
  <xsl:template match="//*[not(*)]">
    <xsl:variable name="attr" as="xs:string" select="local-name(.)" />
    <xsl:variable name="sn" as="xs:number" select="count(preceding-sibling::*[local-name()=$attr])" />
      <xsl:text>usr_</xsl:text><xsl:number value="$sn" format="1" /><xsl:text>_</xsl:text><xsl:value-of select="$attr" />
      <xsl:text>=</xsl:text>
	<xsl:value-of select="." />
	<xsl:if test="position() &lt; last()"><xsl:text>%</xsl:text></xsl:if>
  </xsl:template>

  <xsl:template match="text()"/>

</xsl:stylesheet>

