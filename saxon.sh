rm G1370017354-GES_DISC.echo10.xml.ncml.xml
java -cp /home/ec2-user/xml2h5/saxon9he.jar net.sf.saxon.Transform -t -s:G1370017354-GES_DISC.echo10.xml.ncml -xsl:NcML2XML.xsl -o:G1370017354-GES_DISC.echo10.xml.ncml.xml