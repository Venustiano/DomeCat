import pandas as pd
from rank_bm25 import BM25Plus


class datasource(object):
    def __init__(self):
        self.data_df = pd.DataFrame()

    def read(self,filename):
        return {
            "csv":self.dread_csv,
            "fits":self.dread_fits
        }.get(filename)


    def dread_csv(self, filename):
        self.data_df = pd.read_csv(filename)
        pass

    def dread_fits(self, filename):
        pass

    def get_columns(self):
        return list(self.data_df.columns)

    # Returns column names ordered by similarity rank
    def rank_columns(self, var_name):
        column_names = self.get_columns()
        column_names = [x for x in column_names]
        tokenized_columns = [[char for char in name] for name in column_names]
        bm25_columns = BM25Plus(tokenized_columns)
        tokenized_var = [char for char in var_name]
        l = len(column_names)
        top_cols = bm25_columns.get_top_n(tokenized_var, column_names, n=l)
        # print(tokenized_var,top_cols)
        return top_cols


    
    
