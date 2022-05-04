import re
import sys
import SciServer
from SciServer import Authentication, CasJobs, SkyQuery
from astropy.io.votable import parse
from astroquery.gaia import Gaia
# from astroquery.sdss import SDSS
from pyvo.dal import tap
import pandas as pd
from datetime import datetime, timedelta
import io
from contextlib import redirect_stdout
import urllib

class qcatalogues(object):

    def __init__(self):
        super().__init__()
        self.ESO_TAP_CATS = "http://archive.eso.org/tap_cat"
        self.tapcats = tap.TAPService(self.ESO_TAP_CATS)
        self.sdss_context = "[myscratch:default]"

    def download(self,catalogue,datasetName,query,filename):
        return {
            "GAIA":self.qdownload_GAIA,
            "SDSS":self.qdownload_SDSS,
            "ESO_TAP_CAT":self.qdownload_ESO_TAP_CAT,
            "EUCLID":self.qdownload_EUCLID
        }.get(catalogue)(datasetName,query,filename)
    
    def get_tables(self,catalogue):
        return {
            "GAIA":self.qtables_GAIA,
            "SDSS":self.qtables_SDSS,
            "ESO_TAP_CAT":self.qtables_ESO_TAP_CAT,
            "EUCLID":self.qtables_EUCLID
        }.get(catalogue)

    def get_columns(self,catalogue):
        return {
            "GAIA":self.qcolumns_GAIA,
            "SDSS":self.qcolumns_SDSS,
            "ESO_TAP_CAT":self.qcolumns_ESO_TAP_CAT,
            "EUCLID":self.qcolumns_EUCLID
        }.get(catalogue)

    def qlogin(self,catalogue):
        return {
            "SDSS":self.qlogin_SDSS,
            "ESO_TAP_CAT":self.qlogin_ESO_TAP_CAT,
            "GAIA":self.qlogin_GAIA,
            "EUCLID":self.qlogin_EUCLID
        }.get(catalogue)

    def qdownload_GAIA(self, datasetName, query, filename):
        print(filename,query)
        Gaia.ROW_LIMIT = -1
        Gaia.launch_job_async(query=query, dump_to_file=True, output_format="csv",
                               output_file=filename,verbose=True)
    
    def qdownload_SDSS(self, datasetName, query, filename):
        # dr = int(datasetName[2:])
        # # TODO: validate or add exception
        # res = SDSS.query_sql_async(query,data_release=dr)
        # if res.ok:
        #     sk = 1
        #     print(res.text)
        #     if dr < 10:
        #         sk = 0
        #     qdata = pd.read_csv(io.StringIO(res.text),skiprows=sk)
        #     print(qdata)
        #     qdata.to_csv(filename, index=False, line_terminator='\r\n')
        # else:
        #     print(res)
        dr = datasetName
        tablename = filename

        # Fixme: use regular expresions to find 'FROM' and 'WHERE'

        spquery = query.split("FROM")

        newquery = spquery[0] + ", ROW_NUMBER() OVER(ORDER BY (Select 0)) AS row__id FROM "
        
        spquery = spquery[1].split("WHERE")
        
        newquery += spquery[0] + " INTO " + self.sdss_context + "." + tablename + "\n"
        newquery += "WHERE " + spquery[1]

        print("Submiting job")
        print(newquery)
        
        jobid = CasJobs.submitJob(sql=newquery, context=dr)
        print('Job submitted with jobId = ',jobid)
        waited = CasJobs.waitForJob(jobId=jobid)      # waited is a dummy variable; just print wait msg
        jobDescription = CasJobs.getJobStatus(jobid)
        extra_desc = self.jobDescriber(jobDescription)

        return(extra_desc)
        # TODO: validate or add exception

        pass

    def jobDescriber(self,jobDescription):
        # Prints the results of the CasJobs job status functions in a human-readable manner
        # Input: the python dictionary returned by getJobStatus(jobId) or waitForJob(jobId)
        # Output: prints the dictionary to screen with readable formatting

        if (jobDescription["Status"] == 0):
            status_word = 'Ready'
        elif (jobDescription["Status"] == 1):
            status_word = 'Started'
        elif (jobDescription["Status"] == 2):
            status_word = 'Cancelling'
        elif (jobDescription["Status"] == 3):
            status_word = 'Cancelled'
        elif (jobDescription["Status"] == 4):
            status_word = 'Failed'
        elif (jobDescription["Status"] == 5):
            status_word = 'Finished'
        else:
            status_word = 'Status not found!!!!!!!!!'

        jobDescription["status_word"] = status_word

        print('JobID: ', jobDescription['JobID'])
        print('Status: ', status_word, ' (', jobDescription["Status"],')')
        print('Target (context being searched): ', jobDescription['Target'])
        print('Message: ', jobDescription['Message'])
        print('Created_Table: ', jobDescription['Created_Table'])
        print('Rows: ', jobDescription['Rows'])
        wait = pd.to_datetime(jobDescription['TimeStart']) - pd.to_datetime(jobDescription['TimeSubmit'])
        duration = pd.to_datetime(jobDescription['TimeEnd']) - pd.to_datetime(jobDescription['TimeStart'])
        print('Wait time: ',wait.seconds,' seconds')
        print('Query duration: ',duration.seconds, 'seconds')
        jobDescription["wait_time"] = wait.seconds
        jobDescription["Query_duration"] = duration.seconds 
        return jobDescription
        


    
    def find_table_sdss(self, tablename):
        print("Searching table: {}".format(tablename))
        tables = CasJobs.getTables(context=self.sdss_context)
        for table in tables:
            if table['Name'] == tablename:
                print("Table found")
                print('Table name:\t',table['Name'])
                print('Rows:\t\t {:,.0f}'.format(table['Rows']))
                print('Size (kB):\t {:,.0f} '.format(table['Size']))

                cjCreateDate = table['Date']
                createsec = cjCreateDate / 10000000  # Divide by 10 million to get seconds elapsed since 1 AD
                firstday = datetime(1, 1, 1, 0, 0)   # Save 1 AD as "firstday"
                created = firstday + timedelta(seconds=createsec)  # Get calendar date on which table was created     
                print('Created time:\t',created.strftime('%Y-%m-%d %H:%M:%S'))
                print('\n')
                return True
        print("Table not found")
        return False

    def fetch_sdss_table(self, filename, tablename):
        max_rows = 499999

        print(self.sdss_context)

        myquery = 'SELECT count(*) as nrows ' # note the space at the end of this string - important
        myquery += 'FROM {}.{} '.format(self.sdss_context,tablename)

        print(myquery)
        
        df = CasJobs.executeQuery(sql=myquery, context=self.sdss_context)
        nrows = df["nrows"][0]

        print("Fetching {} rows".format(nrows))

        offset = 1

        myquery = 'select TOP 0 * ' # note the space at the end of this string - important
        myquery += 'FROM {}.{} '.format(self.sdss_context,tablename)
        df = CasJobs.executeQuery(sql=myquery, context=self.sdss_context,format="pandas")
        df[df.columns.difference(['row__id'])].to_csv(filename,sep=',', index=False,line_terminator='\r\n')

        while offset < nrows:

            if (nrows - offset < max_rows):
                next_rows = nrows - offset
            else:
                next_rows = max_rows

            myquery = 'SELECT *  ' # note the space at the end of this string - important
            myquery += 'FROM {}.{} '.format(self.sdss_context,tablename)
            myquery += 'WHERE row__id BETWEEN {} AND {} '.format(offset,offset+next_rows)
            
            df = CasJobs.executeQuery(sql=myquery, context=self.sdss_context,format="pandas")

            df[df.columns.difference(['row__id'])].to_csv(filename,mode='a', sep=',',
                                                          index=False,header=False, line_terminator='\r\n')

            offset += next_rows + 1

            print("Saved {} rows".format(offset-1))


    
    def qdownload_ESO_TAP_CAT(self, datasetName, query, filename):
        with self.tapcats.submit_job(query=query,maxrec=self.tapcats.hardlimit) as job:
            # job.execution_duration= 3600
            try:
                job.run()
                job.wait(timeout=3600)
                if job.phase == 'COMPLETED':
                    src = urllib.request.urlopen(job.result_uri)
                    print(self.tapcats.maxrec)
                    print(self.tapcats.hardlimit)
#                    while True:
#                        stuff = src.read(100)
#                        stuff = parse(stuff)
#                        print(stuff.get_first_table().to_table(use_names_over_ids=True))
#                        if not stuff:
#                            break
                    res = job.fetch_result()
                    res = pd.DataFrame(res)
                    print(res)
                    res.to_csv(filename, index=False, line_terminator='\r\n')
            finally:
                job.delete()
        pass
    
    def qdownload_EUCLID(self, datasetName, query, filename):
        pass
    
    def qlogin_GAIA(self,username, password):
        # f = io.StringIO() 
        # with redirect_stdout(f):
        Gaia.login(user=username, password=password)
        # s = f.getvalue()
        # print(s)
        # print(dir(Gaia))
        print(type(Gaia._TapPlus__isLoggedIn),Gaia._TapPlus__isLoggedIn)
        if Gaia._TapPlus__isLoggedIn:
            return True
        else:
            return(False)
 
            
    def qlogin_SDSS(self,username, password):
        try:
            token = Authentication.login(username, password)
            return token
        except Exception as e:
            print("SDSS auth error", e)
            
    def qlogin_ESO_TAP_CAT(self,username, password):
        pass

    def qlogin_EUCLID(self,username, password):
        pass
    
    def qtables_GAIA(self, context):
        print("So far, works")
        g_tables = Gaia.load_tables(only_names=True)
        # print(g_tables)
        tables = [ re.sub("^[^\.]*\.",'',table.get_qualified_name()) for table in g_tables]
        return sorted(tables)
        
    def qcolumns_GAIA(self,t_name,datasetName):
        table = Gaia.load_table(t_name)
        columns = [col.name for col in table.columns]
        return sorted(columns)
    
    def qtables_SDSS(self, context):
        dr = context

        print("Context from qtables_SDSS(): %s"%(dr))

        queryt = "SELECT TABLE_NAME from INFORMATION_SCHEMA.TABLES"
        # res = SDSS.query_sql_async(queryt,data_release=dr)
        # print(res.status_code)
        # # print(res.text)
        # print(res.ok)
        # print(dir(res))
        # if res.ok:
        #     sk = 1
        #     if dr < 10:
        #         sk = 0
        #     tables = pd.read_csv(io.StringIO(res.text),skiprows=sk)
        #     print(tables)
        #     tables = list(tables['TABLE_NAME'])
        # else:
        #     tables = []
        # g_tables = CasJobs.getTables(context=context)
        g_tables = CasJobs.executeQuery(sql=queryt, context=dr,format="pandas")
        # tables = [table["Name"] for table in g_tables]
        tables = list(g_tables['TABLE_NAME'])
        return sorted(tables)

    def qcolumns_SDSS(self,t_name,datasetName):
        # dt = CasJobs.executeQuery(sql=myquery, context=datasetName,format = "dict")
        # columns = [col[0] for col in dt["Result"][0]["Data"]]
        # print(columns)

        dr = datasetName

        myquery = 'SELECT COLUMN_NAME ' # note the space at the end of this string - important
        myquery += 'from INFORMATION_SCHEMA.COLUMNS '
        myquery += 'where table_name = \'{}\''.format(t_name)
        
        # res = SDSS.query_sql_async(myquery,data_release=dr)
        # print("Data release : %d"%(dr))
        # # print(res.text)
        # print(res.ok)
        # print(dir(res))        
        # if res.ok:
        #     # https://stackoverflow.com/questions/39213597/convert-text-data-from-requests-object-to-dataframe-with-pandas
        #     sk = 1
        #     if dr < 10:
        #         sk = 0            
        #     columns = pd.read_csv(io.StringIO(res.text),skiprows=sk)
        #     print(columns)
        #     columns = list(columns['COLUMN_NAME'])
        # else:
        #     columns = []
        # tables = [table["Name"] for table in g_tables]
        cols = CasJobs.executeQuery(sql=myquery, context=dr,format="pandas")
        
        columns = list(cols['COLUMN_NAME'])        
        return sorted(columns)
    
    def qtables_ESO_TAP_CAT(self,context):
        query = """SELECT schema_name, table_name, description from TAP_SCHEMA.tables"""
        res = self.tapcats.search(query=query)
        print(res)
        print(type(res))
        #TODO: validate that res is not null
        res = pd.DataFrame(res)

        print(res)
        tables =list(res["schema_name"] +"."+ res["table_name"])

        return sorted(tables)
    
    def qcolumns_ESO_TAP_CAT(self,t_name,datasetName):
        table_name = t_name.split('.')[1]
        query = """SELECT column_name from TAP_SCHEMA.columns where table_name = '%s'""" %(table_name)
        res = self.tapcats.search(query=query)
        #TODO: validate that res is not null
        res = pd.DataFrame(res)
        columns = list(res["column_name"])
        # print( columns)
        return sorted(columns)
    
    def qtables_EUCLID():
        pass
    
    def qcolumns_EUCLID():
        pass
 

cats = qcatalogues()
