# Quick'n'dirty mini benchmark used to compare memory and time performance of
# array() vs standard list for the _line_offsets attribute of class CSVDataFile
#
# Early 2015 results: array is much more efficient in term of memory, and doesn't
# seem slower => array wins.
import resource

from dwca.read import DwCAReader


def sizeof_fmt(num, suffix='B'):
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def show_memory_usage():
    bytes = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    print sizeof_fmt(bytes)


# print "Time before: "
# print time.ctime()

# print "Memory before:"
# show_memory_usage()

def test():
    with DwCAReader('dwca-florabank1-occurrences') as dwca:
        # print "Time after open:"
        # print time.ctime()

        # print "Memory after open:"
        # show_memory_usage()

        i = 0
        for row in dwca:
            #tmp = row.data[qn('locality')]
            i = i +1
            if (i % 100000 == 0):
                print "in loop mem: "
                show_memory_usage()

    #     print "Time after loop"
    #     print time.ctime()

    #     print "Memory after loop:"
    #     show_memory_usage()

    # print "Memory at the end:"
    # show_memory_usage()


if (__name__ == '__main__'):
    from timeit import Timer
    t = Timer("test()", "from __main__ import test")
    print t.timeit(number=3)

