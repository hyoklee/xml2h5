<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:nc="http://www.unidata.ucar.edu/namespaces/netcdf/ncml-2.2" exclude-result-prefixes="xs" version="2">
    <!--
    This stylesheet translates simple XML into NcML so it can be included in HDF files
    -->
    <xsl:output method="xml" indent="yes"/>
    <xsl:variable name="rootNode" select="/*"/>
    <xsl:template match="/">
        <xsl:apply-templates/>
    </xsl:template>
    <xsl:template match="*[not(normalize-space(text()[1]) = '')]">
        
        <!-- 
        elements with text values become groups if they have XML attributes,
        nc:attributes if they do not
        -->        
        <xsl:choose>
            <xsl:when test="@*">
                <!-- XML attributes exist - make an nc:group -->
                <xsl:element name="nc:group">
                    <xsl:call-template name="makeName"/>
                    <xsl:call-template name="writeXMLAttributes"/>
                    <xsl:element name="nc:attribute">
                        <xsl:attribute name="name">
                            <xsl:value-of select="'__value'"/>
                        </xsl:attribute>
                        <xsl:attribute name="value">
                            <xsl:value-of select="."/>
                        </xsl:attribute>
                    </xsl:element>
                </xsl:element>
            </xsl:when>
            <xsl:otherwise>
                <!-- no XML attributes -->
                <xsl:element name="nc:attribute">
                    <xsl:call-template name="makeName"/>
                    <xsl:attribute name="value">
                        <xsl:value-of select="."/>
                    </xsl:attribute>
                </xsl:element>
            </xsl:otherwise>
        </xsl:choose>
    </xsl:template>
    <!-- Elements without text become groups -->
    <xsl:template match="*[normalize-space(text()[1]) = '']">
        <xsl:element name="nc:group">
            <xsl:call-template name="makeName"/>
            <xsl:if test=". = /">
                <xsl:for-each select="$rootNode/nc:group[contains(@name,'namespace_')]">
                    <xsl:namespace name="{nc:attribute[@name='prefix']/@value}" select="nc:attribute[@name='uri']/@value"/>
                </xsl:for-each>
            </xsl:if>
            <xsl:call-template name="writeXMLAttributes"/>
            <xsl:apply-templates/>
            <xsl:if test=". = /">
                <xsl:call-template name="writeNamespaces"/>
            </xsl:if>
        </xsl:element>
    </xsl:template>
    <xsl:template name="writeXMLAttributes">
        <xsl:for-each select="@*">
            <xsl:element name="nc:attribute">
                <xsl:attribute name="name">
                    <xsl:value-of select="concat('@', name())"/>
                </xsl:attribute>
                <xsl:attribute name="value">
                    <xsl:value-of select="."/>
                </xsl:attribute>
            </xsl:element>
        </xsl:for-each>
    </xsl:template>
    <xsl:template name="makeName">
        <xsl:attribute name="name">
            <!-- 
              The name of the group is the element name unless it is
              repeated name() = name(preceding-sibling::*[1]).
              In that case, an __id is appended to the name.              
            -->
            <xsl:value-of select="name(.)"/>
            <xsl:if test="name() = name(preceding-sibling::*[1])">
                <xsl:value-of select="concat('__', generate-id())"/>
            </xsl:if>
        </xsl:attribute>
    </xsl:template>
    <xsl:template name="writeNamespaces">
        <!--
          write out namespace prefixes and uri's as an nc:group with two attributes (prefix and uri)
          These are written out at the bottom of the metadata group so they are out of the way for human
          readers.
        -->
        <xsl:for-each select="in-scope-prefixes($rootNode)">
            <xsl:element name="nc:group">
                <xsl:attribute name="name" select="concat('namespace_', position())"/>
                <xsl:element name="nc:attribute">
                    <xsl:attribute name="name" select="'prefix'"/>
                    <xsl:attribute name="value" select="."/>
                </xsl:element>
                <xsl:element name="nc:attribute">
                    <xsl:attribute name="name" select="'uri'"/>
                    <xsl:attribute name="value" select="namespace-uri-for-prefix(., $rootNode)"/>
                </xsl:element>
            </xsl:element>
        </xsl:for-each>
    </xsl:template>
</xsl:stylesheet>
