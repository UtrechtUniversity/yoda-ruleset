<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
	xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
	<xsl:template match="metadata">
		<metadata>
			<xsl:for-each select="*[text() != '']">
				<xsl:variable name="attribute" as="xs:string" select="local-name(.)" />
				<xsl:variable name="serialnumber" as="xs:number" select="count(preceding-sibling::*[local-name()=$attribute])" />
					<AVU>
						<Attribute>usr_<xsl:number value="$serialnumber" format="1" />_<xsl:value-of select="$attribute" /></Attribute>
						<Value><xsl:value-of select="." /></Value>
					</AVU>
					<AVU>
						<Attribute>usr_lc<xsl:number value="$serialnumber" format="1" />_<xsl:value-of select="$attribute" /></Attribute>
						<Value><xsl:value-of select="translate(., 'ABCDEFGHIJKLMNOPQRSTUVWXYZÀÁÂÃÄÅÆÇÈÉÊËÌÍÎÏÐÑÒÓÔÕÖØÙÚÛÜÝÞŸŽŠŒ', 'abcdefghijklmnopqrstuvwxyzàáâãäåæçèéêëìíîïðñòóôõöøùúûüýþÿžšœ')" /></Value>
					</AVU>

			</xsl:for-each>
		</metadata>
	</xsl:template>
</xsl:stylesheet>
