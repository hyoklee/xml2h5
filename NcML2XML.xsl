<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xs="http://www.w3.org/2001/XMLSchema" xmlns:nc="http://www.unidata.ucar.edu/namespaces/netcdf/ncml-2.2" xmlns:eml="eml://ecoinformatics.org/eml-2.1.1" xmlns:stmml="http://www.xml-cml.org/schema/stmml-1.1" xmlns:xlink="http://www.w3.org/1999/xlink" xmlns:wml2="http://www.opengis.net/waterml/2.0" xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:om="http://www.opengis.net/om/2.0"
    xmlns:sa="http://www.opengis.net/sampling/2.0" xmlns:sams="http://www.opengis.net/samplingSpatial/2.0" xmlns:swe="http://www.opengis.net/swe/2.0" exclude-result-prefixes="xs" version="2">
    <!--
    This stylesheet translates NcML created with XML2NCML.xsl back into original XML.
    It is designed to use in a workflow that reproduces original XML from NcML
    -->
    <xsl:output method="xml" indent="yes"/>
    <xsl:strip-space elements="*"/>
    <xsl:variable name="rootNode" select="/"/>
    <xsl:template match="/">
        <xsl:apply-templates/>
    </xsl:template>
    <xsl:template match="nc:group[not(nc:attribute[@name = '__value'])]">
        <!-- 
            groups without attributes named __value hold values of original xml
            elements that have only XML attributes or only values. 
            XML like <x att='AAA'/> becomes a group named x with a single
            attribute called @att with a value = AAA.
            XML like <x>XXX</x> becomes an attribute named x with a value = XXX.
        -->
        <xsl:variable name="elementName">
            <xsl:choose>
                <xsl:when test="contains(@name, '__')">
                    <!--
                        the characters "__" are used to separate element names from identifiers that are appended 
                        to element names to ensure uniqueness in situations with repeated elements. These identifiers
                        need to be removed on the way out.
                    -->
                    <xsl:value-of select="substring-before(@name, '__')"/>
                </xsl:when>
                <xsl:otherwise>
                    <xsl:value-of select="@name"/>
                </xsl:otherwise>
            </xsl:choose>
        </xsl:variable>
        <xsl:element name="{$elementName}">
            <!-- The root node is always processed here. Create the namespaces. -->
            <xsl:if test=". = $rootNode">
                <xsl:for-each select="//nc:group[contains(@name, 'namespace_')]">
                    <xsl:variable name="prefix" select="nc:attribute[@name = 'prefix']/@value"/>
                    <xsl:variable name="uri" select="nc:attribute[@name = 'uri']/@value"/>
                    <xsl:namespace name="{$prefix}" select="$uri"/>
                </xsl:for-each>
            </xsl:if>
            <xsl:apply-templates/>
        </xsl:element>
    </xsl:template>
    <xsl:template match="nc:group[nc:attribute[@name = '__value']]">
        <!-- 
            groups with attributes named __value hold values of original xml
            elements that have XML attributes and values. 
            So xml like <x att='AAA'>XXX</x> becomes a group named x with two 
            attributes named @att and __value. The aaa attribute has value = AAA
            and the __value attribute has the value XXX.
        -->
        <xsl:variable name="elementName">
            <xsl:choose>
                <xsl:when test="contains(@name, '_')">
                    <xsl:value-of select="substring-before(@name, '_')"/>
                </xsl:when>
                <xsl:otherwise>
                    <xsl:value-of select="@name"/>
                </xsl:otherwise>
            </xsl:choose>
        </xsl:variable>
        <xsl:element name="{$elementName}">
            <xsl:apply-templates select="nc:attribute[contains(@name, '@')]"/>
            <xsl:value-of select="nc:attribute[@name = '__value']/@value"/>
        </xsl:element>
    </xsl:template>
    <xsl:template match="nc:attribute[not(contains(@name, '@'))]">
        <!--
            attributes that do not contain @ become xml elements
        -->
        <xsl:variable name="elementName">
            <xsl:choose>
                <xsl:when test="contains(@name, '_')">
                    <xsl:value-of select="substring-before(@name, '_')"/>
                </xsl:when>
                <xsl:otherwise>
                    <xsl:value-of select="@name"/>
                </xsl:otherwise>
            </xsl:choose>
        </xsl:variable>
        <xsl:element name="{$elementName}">
            <xsl:value-of select="@value"/>
        </xsl:element>
    </xsl:template>
    <xsl:template match="nc:attribute[contains(@name, '@')]">
        <xsl:attribute name="{substring-after(@name,'@')}">
            <xsl:value-of select="@value"/>
        </xsl:attribute>
    </xsl:template>
    <xsl:template match="nc:attribute[@name = '__value']">
        <xsl:value-of select="."/>
    </xsl:template>
    <!-- Empty template to avoid namespace_# groups -->
    <xsl:template match="nc:group[contains(@name, 'namespace_')]" priority="2"/>
    <!-- Empty template to avoid atributes with names = __value -->
    <xsl:template match="nc:attribute[@name = '__value']"/>
    <xsl:template match="comment()">
        <xsl:comment><xsl:value-of select="."/></xsl:comment>
    </xsl:template>
</xsl:stylesheet>
