from dwca import DwCAReader

source = DwCAReader('./test/sample_files/dwca-simple-test-archive.zip')

for line in source.each_line():
    # line is an instance of DwCALine
    print line
