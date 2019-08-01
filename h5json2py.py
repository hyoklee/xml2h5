import sys
from StringIO import StringIO
import json
from python import PyCode

if __name__ == "__main__":
    
    with open(sys.argv[1]) as data_file:
        try:
            h5json = json.load(data_file)
        except ValueError:
            print 'ERROR:Invalid json file'
    filename = sys.argv[2]            
    py = PyCode(h5json, filename)
    code = unicode(py.get_code())
    with open(filename, "w") as text_file:
        text_file.write(code)



