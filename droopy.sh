#!/bin/bash
python droopy -m "Please upload your XML (ISO, SensorML, WaterML, TimeSeriesML, etc.) to convert it into HDF5 groups and attributes. Or upload your NcML to convert it to XML." --dl -d /home/ec2-user/xml2h5/upload 9000
# java -cp saxon9he.jar net.sf.saxon.Transform -t -s:measurement-timeseries-example.xml -xsl:ISO-12NCML.xsl -o:measurement-timeseries-example.ncml
