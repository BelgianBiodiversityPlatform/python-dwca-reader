from dwca.files import CSVDataFile
from typing import List
from typing_extensions import Literal
import itertools


class StarRecordIterator(object):
    """ Object used to iterate over multiple DWCA-files joined on the coreid
    
        :param files_to_join: a list of the `dwca.files.CSVDataFile`s we'd like to join.
            May or may not include the core file (the core is not treated in a special way)
        :param how: indicates the type of join.  "inner" and "outer" correspond vaguely to 
            inner and full joins.  The outer join includes rows that don't match on all files,
            however, it doesn't create null fields to fill in when rows are missing in files.
            Attempts to conform to pandas.DataFrame.merge API.
    """
    def __init__(self, files_to_join: List[CSVDataFile], how: Literal["inner", "outer"] = "inner"):
        self.files_to_join = files_to_join

        # gather the coreids we want to join over.
        self.common_core = set(self.files_to_join[0].coreid_index)
        for data_file in self.files_to_join[1:]:
            # inner join: coreid must be in all files
            if how == "inner":
                self.common_core &= set(data_file.coreid_index)
            # outer join: coreid may be in any files
            elif how == "outer":
                self.common_core |= set(data_file.coreid_index)
                
        # initialize iterator variables
        self._common_core_iterator = iter(self.common_core)
        self._cross_product_iterator = iter([])

    
    def __next__(self):
        # the next combination of rows matching this coreid
        next_positions = next(self._cross_product_iterator, None)
        # we finished all the combinations for this coreid
        if not next_positions:
            # get the next coreid
            self._current_coreid = next(self._common_core_iterator)
            self._files_with_current_coreid = [
                csv_file for csv_file in self.files_to_join 
                    if self._current_coreid in csv_file.coreid_index]
            # this iterates over all combinations of rows matching a coreid from all files
            self._cross_product_iterator = itertools.product(
                *(
                    csv_file.coreid_index[self._current_coreid] 
                        for csv_file in self._files_with_current_coreid
                ))
            # go back and try to iterate over the rows for the new coreid
            return next(self)
        # zip up this combination of rows from all of the files.
        return (
            csv_file.get_row_by_position(position) for position, csv_file in zip(next_positions, self._files_with_current_coreid)
        )

    
    def __iter__(self): return self
