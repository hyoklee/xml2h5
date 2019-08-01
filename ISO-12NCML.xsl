<xsl:stylesheet xmlns:xsl="http://www.w3.org/1999/XSL/Transform" version="2.0" xmlns:nc="http://www.unidata.ucar.edu/namespaces/netcdf/ncml-2.2" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xmlns:cat="http://standards.iso.org/iso/19115/-3/cat/1.0" xmlns:cit="http://standards.iso.org/iso/19115/-3/cit/1.0" xmlns:gcx="http://standards.iso.org/iso/19115/-3/gcx/1.0"
  xmlns:gex="http://standards.iso.org/iso/19115/-3/gex/1.0" xmlns:lan="http://standards.iso.org/iso/19115/-3/lan/1.0" xmlns:srv="http://standards.iso.org/iso/19115/-3/srv/2.0"
  xmlns:mas="http://standards.iso.org/iso/19115/-3/mas/1.0" xmlns:mcc="http://standards.iso.org/iso/19115/-3/mcc/1.0" xmlns:mco="http://standards.iso.org/iso/19115/-3/mco/1.0"
  xmlns:mda="http://standards.iso.org/iso/19115/-3/mda/1.0" xmlns:mdb="http://standards.iso.org/iso/19115/-3/mdb/1.0" xmlns:mds="http://standards.iso.org/iso/19115/-3/mds/1.0"
  xmlns:mdt="http://standards.iso.org/iso/19115/-3/mdt/1.0" xmlns:mex="http://standards.iso.org/iso/19115/-3/mex/1.0" xmlns:mmi="http://standards.iso.org/iso/19115/-3/mmi/1.0"
  xmlns:mpc="http://standards.iso.org/iso/19115/-3/mpc/1.0" xmlns:mrc="http://standards.iso.org/iso/19115/-3/mrc/1.0" xmlns:mrd="http://standards.iso.org/iso/19115/-3/mrd/1.0"
  xmlns:mri="http://standards.iso.org/iso/19115/-3/mri/1.0" xmlns:mrl="http://standards.iso.org/iso/19115/-3/mrl/1.0" xmlns:mrs="http://standards.iso.org/iso/19115/-3/mrs/1.0"
  xmlns:msr="http://standards.iso.org/iso/19115/-3/msr/1.0" xmlns:mdq="http://standards.iso.org/iso/19115/-3/mdq/1.0" xmlns:mac="http://standards.iso.org/iso/19115/-3/mac/1.0"
  xmlns:gco="http://standards.iso.org/iso/19115/-3/gco/1.0" xmlns:gmx="http://www.isotc211.org/2005/gmx" 
  xmlns:gml="http://www.opengis.net/gml/3.2" xmlns:xlink="http://www.w3.org/1999/xlink"
  xmlns:eos="http://earthdata.nasa.gov/schema/eos" xmlns:wml2="http://www.opengis.net/waterml/2.0"
  exclude-result-prefixes="cat cit gcx gmx gex lan srv mas mcc mco mda mdb mds mdt mex mmi mpc mrc mrd mri mrl mrs msr mdq mac gco gml xlink eos">
  <xd:doc xmlns:xd="http://www.oxygenxml.com/ns/doc/xsl" scope="stylesheet">
    <xd:desc>
      <xd:p>This is a generic transform for translating ISO-compliant metadata from ISO19139, ISO19139-2 or ISO19115-3 into ISO-Compliant NcML. it is used as the first step in the process of inserting
        ISO-compliant metadata into HDF data files. </xd:p>
      <xd:p><xd:b>Modified on:</xd:b> Feb. 29, 2016</xd:p>
      <xd:p><xd:b>Author:</xd:b>thabermann@hdfgroup.org</xd:p>
    </xd:desc>
  </xd:doc>
  <xsl:output method="xml" indent="yes"/>
  <xsl:strip-space elements="*"/>
  <xsl:param name="allRoles" select="1"/>
  <xsl:variable name="rootNode" select="/*"/>
  <xsl:template match="/">
    <nc:netcdf xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns="http://www.unidata.ucar.edu/namespaces/netcdf/ncml-2.2">
      <xsl:apply-templates/>
    </nc:netcdf>
  </xsl:template>
  <xsl:template
    match=" 
    *[matches(name(),'[a-z1-9]*:[A-Z]*_[a-zA-Z]*')] |
    *[@codeList] |
    *[matches(name(),'gml:[A-Z]{1}.*')] |
    *[matches(name(),'gcx:[A-Z]{1}.*')] |   
    *[matches(name(),'gmx:[A-Z]{1}.*')] |   
    *[matches(name(),'gco:[A-Z]{1}.*') and (count(@*) or count(child::*))] |
    gco:MemberName | gco:TypeName"
    priority="2">
    <!-- 
    This is the match for creating groups.
    All UML objects are groups: *[matches(name(),'[a-z1-9]*:[A-Z]{2}_[a-zA-Z]*')]
    All codeLists are groups: *[ends-with(name(),'Code')]
    All gml objects are groups: *[matches(name(),'gml:[A-Z]{1}.*')] (needs to be tested)
    All gco objects that have attributes are groups: *[matches(name(),'gco:[A-Z]{1}.*') and count(@*)]
    -->
    <xsl:element name="nc:group">
      <xsl:attribute name="name">
        <xsl:choose>
          <xsl:when test=". = /">
            <!-- 
              The root element has no parent so the name of the group
              is the name of the root element
             -->
            <xsl:value-of select="name()"/>
          </xsl:when>
          <xsl:otherwise>
            <!-- 
              The name of the group is the role (parent::*) unless the role is
              repeated (name(parent::*)=name(parent::*/preceding-sibling::*[1])).
              In that case, an _id is appended to the name.              
            -->
            <xsl:value-of select="name(parent::*)"/>
            <xsl:if test="name(parent::*)=name(parent::*/preceding-sibling::*[1])">
              <xsl:value-of select="concat('_',generate-id())"/>
            </xsl:if>
          </xsl:otherwise>
        </xsl:choose>
      </xsl:attribute>
      <xsl:choose>
        <!-- The parameter allRoles dtermines whether all roles are explicitly defined (allRoles=1)
          or only those that are required for repeating elements (allRoles = 0
        -->
        <xsl:when test="$allRoles">
          <!-- Give all groups roles -->
          <xsl:call-template name="writeNcmlAttribute">
            <xsl:with-param name="name" select="'__role'"/>
            <xsl:with-param name="value">
              <xsl:choose>
                <xsl:when test=". = /">
                  <xsl:value-of select="'metadataRoot'"/>
                </xsl:when>
                <xsl:otherwise>
                  <xsl:value-of select="name(parent::node())"/>
                </xsl:otherwise>
              </xsl:choose>
            </xsl:with-param>
          </xsl:call-template>
        </xsl:when>
        <xsl:otherwise>
          <!-- roles only when necessary -->
          <xsl:if test="name(parent::*)=name(parent::*/preceding-sibling::*[1])">
            <xsl:call-template name="writeNcmlAttribute">
              <xsl:with-param name="name" select="'__role'"/>
              <xsl:with-param name="value" select="name(parent::*)"/>
            </xsl:call-template>
          </xsl:if>
        </xsl:otherwise>
      </xsl:choose>
      <xsl:call-template name="writeNcmlAttribute">
        <xsl:with-param name="name" select="'__type'"/>
        <xsl:with-param name="value" select="name()"/>
      </xsl:call-template>
      <xsl:call-template name="transferAttributes"/>
      <xsl:if test="text()">
        <!--
          If the object has a value (e.g. gco:Measure with a value, or codeLists),
          write it out as a value attribute
        -->
        <xsl:element name="nc:attribute">
          <xsl:attribute name="name" select="'value'"/>
          <xsl:attribute name="value" select="."/>
        </xsl:element>
      </xsl:if>
      <xsl:apply-templates/>
      <xsl:if test=". = /">
        <!--
          write out namespace prefixes and uri's as an nc:group with two attributes (prefix and uri)
          These are written out at the bottom of the metadata group so they are out of the way for human
          readers.
        -->
        <xsl:for-each select="in-scope-prefixes($rootNode)">
          <xsl:element name="nc:group">
            <xsl:attribute name="name" select="concat('namespace_',position())"/>
            <xsl:element name="nc:attribute">
              <xsl:attribute name="name" select="'prefix'"/>
              <xsl:attribute name="value" select="."/>
            </xsl:element>
            <xsl:element name="nc:attribute">
              <xsl:attribute name="name" select="'uri'"/>
              <xsl:attribute name="value" select="namespace-uri-for-prefix(.,$rootNode)"/>
            </xsl:element>
          </xsl:element>
        </xsl:for-each>
      </xsl:if>
    </xsl:element>
  </xsl:template>
  <xsl:template match="*[matches(name(),'gco:[A-Z]{1}.*')] | *[matches(name(),'gmd:URL')]">
    <!-- transform fundamental types (gco:CharacterString | gco:DateTime | gco:Integer | gco:Real | gco:Decimal | gco:Boolean | gco:RecordType | gco:Measure) -->
    <!-- without attributes -->
    <xsl:call-template name="transferAttributes"/>
    <xsl:call-template name="writeNcmlAttribute">
      <xsl:with-param name="name">
        <xsl:value-of select="name(parent::node())"/>
        <xsl:if test="name(parent::*)=name(parent::*/preceding-sibling::*[1])">
          <xsl:value-of select="concat('_',generate-id())"/>
        </xsl:if>
      </xsl:with-param>
      <xsl:with-param name="value" select="."/>
      <xsl:with-param name="type" select="name()"/>
    </xsl:call-template>
  </xsl:template>
  <xsl:template match="gml:*[text()]">
    <!-- Catch gml: attributes (fundamental types) that do not use gco:CharacterString -->
    <xsl:choose>
      <xsl:when test="count(@*)">
        <!-- if xml attributes exist this must be a group -->
        <xsl:element name="nc:group">
          <xsl:attribute name="name" select="name()"/>
          <xsl:call-template name="transferAttributes"/>
          <xsl:call-template name="writeNcmlAttribute">
            <xsl:with-param name="name" select="name()"/>
            <xsl:with-param name="value" select="."/>
            <xsl:with-param name="type" select="'attributeWithValue'"/>
          </xsl:call-template>
        </xsl:element>
      </xsl:when>
      <xsl:when test="count(child::*[@*])">
        <xsl:apply-templates/>
      </xsl:when>
      <xsl:otherwise>
        <xsl:call-template name="writeNcmlAttribute">
          <xsl:with-param name="name" select="name()"/>
          <xsl:with-param name="value" select="."/>
          <xsl:with-param name="type" select="'attributeWithValue'"/>
        </xsl:call-template>
        <xsl:apply-templates/>
      </xsl:otherwise>
    </xsl:choose>
  </xsl:template>
  <xsl:template match="*[string-length(.) = 0 and count(child::*) = 0]">
    <!-- empty elements -->
    <xsl:element name="nc:group">
      <!--<xsl:attribute name="name" select="name()"/>-->
      <xsl:attribute name="name">
        <xsl:choose>
          <xsl:when test=". = /">
            <!-- 
              The root element has no parent so the name of the group
              is the name of the root element
             -->
            <xsl:value-of select="name()"/>
          </xsl:when>
          <xsl:otherwise>
            <!--
              This template matches roles with attributes and no content, so the
              name has to come from this element rather than the parent (role)
              The name of the group is the role (name()) unless the role is
              repeated (name()=name(preceding-sibling::*[1])).
              In that case, an _id is appended to the name.              
            -->
            <xsl:value-of select="name()"/>
            <xsl:if test="name()=name(preceding-sibling::*[1])">
              <xsl:value-of select="concat('_',generate-id())"/>
            </xsl:if>
          </xsl:otherwise>
        </xsl:choose>
      </xsl:attribute>
      
      <xsl:choose>
        <xsl:when test="count(@*)">
          <!-- with attributes (e.g. xlinks or nilReason) -->
          <xsl:call-template name="transferAttributes"/>
        </xsl:when>
        <xsl:otherwise>
          <!-- without attributes: add gco:nilReason="unknown" -->
          <xsl:call-template name="writeNcmlAttribute">
            <xsl:with-param name="name" select="'gco:nilReason'"/>
            <xsl:with-param name="value" select="'unknown'"/>
          </xsl:call-template>
        </xsl:otherwise>
      </xsl:choose>
    </xsl:element>
  </xsl:template>
  <xsl:template name="transferAttributes">
    <!-- 
    This template converts XML attributes (@*) to nc:attributes. 
    The names of these nc:attributes start with @ to identify them as 
    XML attributes in the HDF paths.
    -->
    <xsl:for-each select="@*">
      <xsl:call-template name="writeNcmlAttribute">
        <xsl:with-param name="name" select="concat('@',name())"/>
        <xsl:with-param name="value" select="."/>
      </xsl:call-template>
    </xsl:for-each>
  </xsl:template>
  <xsl:template name="writeNcmlAttribute">
    <xsl:param name="name"/>
    <xsl:param name="value"/>
    <xsl:param name="type"/>
    <xsl:if test="$value">
      <xsl:element name="nc:attribute">
        <xsl:attribute name="name">
          <xsl:value-of select="$name"/>
        </xsl:attribute>
        <xsl:attribute name="value">
          <xsl:value-of select="$value"/>
        </xsl:attribute>
        <xsl:if test="$type">
          <xsl:attribute name="__isoType">
            <xsl:value-of select="$type"/>
          </xsl:attribute>
        </xsl:if>
      </xsl:element>
    </xsl:if>
  </xsl:template>
  <xsl:template match="text()"/>
  <xsl:template match="comment()">
    <xsl:comment><xsl:value-of select="."/></xsl:comment>
  </xsl:template>
  <xsl:template match="eos:EOS_AdditionalAttributes" priority="5">
    <!-- This template matches the RecordType (i.e. eos:additionalAttributes) 
      used to add eos:AdditionalAttributes to ISO metadata records.
      This RecordType requires a structure to embed multiple 
      eos:EOS_AdditionalAttributes in a single eos:additionalAttributes container. 
      Within the eos:EOS_AdditionalAttributes, the standard templates are used.
    -->
    <xsl:element name="nc:group">
      <xsl:attribute name="name" select="'eos:EOS_AdditionalAttributes'"/>
      <xsl:for-each select="eos:additionalAttribute">
        <xsl:element name="nc:group">
          <!-- add a unique identifier to handle multiple eos:AdditionalAttributes -->
          <xsl:attribute name="name" select="concat('eos:additionalAttribute_',generate-id())"/>
          <xsl:apply-templates/>
        </xsl:element>
      </xsl:for-each>
    </xsl:element>
  </xsl:template>
</xsl:stylesheet>
