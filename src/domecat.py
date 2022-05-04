import sys
import os
from shutil import copy
from appdirs import user_data_dir, user_config_dir
from PyQt5.QtWidgets import (QMainWindow, QApplication, QWidget, QVBoxLayout,QHBoxLayout,QFileDialog,
                             QLabel,QPushButton, QComboBox, QCompleter, QLineEdit, QDialog,QMessageBox,QStyle)
from PyQt5 import QtGui
from PyQt5.QtCore import QTimer, Qt, pyqtSlot
#from PyQt5.QtGui import QKeySequence
from PyQt5.QtGui import QDoubleValidator,QIntValidator, QMovie
from domecattabs import *
from SignInForm import Ui_Dialog as signInForm
from tableModel import tableModel, QueryModel
from qcatalogues import cats
import qtawesome as qta

from osformat  import data2osformat

from datetime import date, datetime
import time
import json
import jsonschema
import re
from jsonschema import validate
from dbmodel import Catalogue, Base, Cat_table, TColumn, CQuery, ColQueryAssociation, CrossTableAssociation, DomeFormat, ops, ftypes
from sqlalchemy.engine.url import URL
from sqlalchemy import create_engine, and_, func
from sqlalchemy.orm import sessionmaker


# https://stackoverflow.com/questions/42770719/pyqt-how-to-create-a-wait-popup-for-running-a-long-function-calulation
class downloadThread(QtCore.QThread):
    def __init__(self,catalogue, dataset, query,filename):
        super(downloadThread,self).__init__()
        self.query = query
        self.filename = filename
        self.catalogue = catalogue
        self.dataset = dataset
        # self.cat = qcatalogues()
        
    def run(self):
        if self.catalogue == "SDSS":
            pathname, _ = os.path.splitext(self.filename)
            tablename = pathname.split('/')[-1]
            if cats.find_table_sdss(tablename):
                # TODO: ask the user whether remove the current table in sciserver and submit a new query
                # or or just fetch the current table
                cats.fetch_sdss_table(self.filename,tablename)
            else:
                # submit the query to sciserver saved as tablename
                job = cats.download(self.catalogue,self.dataset, self.query,tablename)

                if (job["Status"] == 5):
                    # fetch the data
                    cats.fetch_sdss_table(self.filename,tablename)
                else:
                    msg = QMessageBox()
                    msg.setIcon(QMessageBox.Critical)

                    msg.setText("Job failed")
                    # msg.setInformativeText("This is additional information")
                    msg.setWindowTitle("Something went wrong!")
                    msg.setDetailedText(json.dumps(job,default = self.myconverter, indent=4))
                    msg.setStandardButtons(QMessageBox.Ok)
                    # msg.buttonClicked.connect(msgbtn)
	            # retval = msg.exec_()
                    # print "value of pressed message box button:", retval
                    return
        else:
            print("Downloading data from {} \
            and saving into {} ".format(self.catalogue, self.filename))
            # qcatalogues().download(self.catalogue,self.dataset, self.query,self.filename)
            cats.download(self.catalogue,self.dataset, self.query,self.filename)

# inspired from
# https://www.youtube.com/watch?reload=9&v=mYPNHoPwIJI
# https://www.learnpyqt.com/courses/start/dialogs/
class loadingScreen(QDialog):
    def __init__(self,parent=None,catalogue=None, dataset = None, query=None, filename=None):
        super(loadingScreen,self).__init__(parent)
        self.setFixedSize(200,200)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.CustomizeWindowHint)
        self.move(100, 100)

        self.label_animation = QLabel(self)

        #self.movie = QMovie('./pics/Loading_2.gif')
        self.movie = QMovie('./pics/download.gif')
        self.label_animation.setMovie(self.movie)

        # instantiate a QThread
        self.thread = downloadThread(catalogue,dataset, query,filename)
        self.startAnimation()
        self.thread.finished.connect(self.stopAnimation)
        self.thread.start()

    def startAnimation(self):
        self.movie.start()

    def stopAnimation(self):
        self.movie.stop()
        # https://stackoverflow.com/questions/28706651/pyqt-qdialog-returning-a-value-and-closing-from-dialog
        # self.close()
        self.accept()

class signIn(QDialog):
    def __init__(self,parent=None,catalogue=None,urlsignup=None):
        super(signIn,self).__init__(parent)
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.CustomizeWindowHint)
        link = '<a href={0}>{1}</a>'.format(urlsignup,'Create account')
        self.qcat = catalogue
        self.token=None
        self.dialog = QtWidgets.QDialog()
        self.dialog.ui = signInForm()
        self.dialog.ui.setupUi(self.dialog)
        self.dialog.setWindowTitle("Login")
        self.dialog.ui.lbl_signin.setText("Provide your " + catalogue + " credentials:")
        self.dialog.ui.lbl_signin.adjustSize()
        self.dialog.ui.buttonBox.accepted.connect(self.login)
        self.dialog.ui.buttonBox.rejected.connect(self.dialog.reject)
        self.dialog.ui.lbl_signup.setOpenExternalLinks(True)
        self.dialog.ui.lbl_signup.setText(link)
        # self.dialog.exec_()
        # self.dialog.show()

    def login(self):
        loginName = self.dialog.ui.lineEditUsername.text()
        loginPassword = self.dialog.ui.lineEditPassword.text()
        self.token = cats.qlogin(catalogue=self.qcat)(loginName, loginPassword)
        if self.token:
            # Gaia_ok = 'OK' in self.token
            # if (self.token and self.qcat == "SDSS") or (self.qcat == 'GAIA' and Gaia_ok):
            print("LOGIN",self.token)
            self.dialog.accept()
            return

        QtWidgets.QMessageBox.warning(
        self, 'Error', 'Bad user or password')

    def getToken(self):
        return self.token

        
class AppWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.appname = "domecat"
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        self.query_schema = {}
        
        self.new_query = {}
        
        self.schema_file = "./config/catalogue_schema.json"
        self.catalogue_file = "./config/catalogues.json"

        # TODO: Implement variable-match (cat-var <-> speck vars) functionality by means of the database
        # Potentially exclude column_defs
        self.col_defs = "./config/column_defs.json"
        self.column_defs = {}
        
        self.ui.listView.clicked.connect(self.on_table_clicked)
        self.text_tooltips()

        self.rdata = data2osformat()

        self.ui.Button_add_cond.setEnabled(False)

        self.treeModel = QtGui.QStandardItemModel()
        # self.root = self.treeModel.invisibleRootItem()
        self.ui.tablesTree.setModel(self.treeModel)
        self.ui.tablesTree.clicked.connect(self.on_tree_clicked)

        self.widget = QWidget()            # Widget that contains the collection of Vertical Box
        self.vbox = QVBoxLayout()          # The Vertical Box that contains the Horizontal Boxes of labels and buttons
        self.vbox.addStretch(1)

        self.ui.comboSelectSource.currentIndexChanged.connect(self.sourceCatalogueChange)
        self.ui.comboBox.currentTextChanged.connect(self.on_cb1_changed)
        self.ui.comboBox_3.currentTextChanged.connect(self.on_cb3_changed)
        self.ui.step_tabs.currentChanged.connect(self.on_convert)

        self.ui.lE_keyq.setValidator(QIntValidator())
        self.ui.lE_keyq.editingFinished.connect(self.update_disp_query_db)
        # self.ui.lE_desc_query.editingFinished.connect(self.update_disp_query_db)
        self.ui.Button_add_cond.clicked.connect(self.add_condition_across)
        self.ui.ButtonADQL.clicked.connect(self.generate_ADQL)
        self.ui.Button_submit.clicked.connect(self.run_ADQL)

        # Convert/Save
        self.ui.buttonGetFilename.clicked.connect(self.output_dst_name)


        self.ui.buttonSelectFile.clicked.connect(self.update_src_name)
        self.ui.cmb_dist_par.addItem("PARALLAX")
        self.ui.cmb_dist_par.addItem("DISTANCE")
        self.ui.cmb_dist_par.addItem("REDSHIFT")
        self.ui.cmb_dist_par.currentTextChanged.connect(self.update_rank)

        self.ui.lEdit_src_name.textChanged.connect(self.select_file)
        self.ui.comboBox_results.currentTextChanged.connect(self.update_results_tab)

        # self.ui.Button_convert.setEnabled(False)
        # self.ui.Button_convert.clicked.connect(self.collect_info_convert)
        
        self.widget.setLayout(self.vbox)

        #Scroll Area Properties
        #self.ui.scrollConditions.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        #self.ui.scrollConditions.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.ui.scrollConditions.setWidgetResizable(True)
        self.ui.scrollConditions.setWidget(self.widget)

        # scroll area for conditions across tables
        self.ac_widget = QWidget()                 # Widget that contains the collection of Vertical Box
        self.ac_vbox = QVBoxLayout()               # The Vertical Box that contains the Horizontal Boxes of tables
        self.ac_vbox.addStretch(1)

        self.ac_widget.setLayout(self.ac_vbox)

        #Scroll Area Properties
        #self.ui.scrollConditions.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        #self.ui.scrollConditions.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.ui.scroll_across.setWidgetResizable(True)
        self.ui.scroll_across.setWidget(self.ac_widget)

        self.ad_context = {"SDSS":{"auth":True, "token":None},"ESO_TAP_CAT":{"auth":False,"token":"yes"},
                           "EUCLID":{"auth":None,"token":"yes"},"GAIA":{"auth":True,"token":None}}

        self.session = None
        self.dbsetup()

        self.load_catalogues()
        

        self.ui.Button_delq.setEnabled(False)
        self.ui.Button_nextq.setEnabled(False)
        self.ui.Button_prevq.setEnabled(False)
        self.ui.Button_searchq.setEnabled(False)
        self.ui.cmb_filetype_aq.setEnabled(False)
        self.ui.format_tabs.setTabEnabled(1,False)
        self.ui.format_tabs.setTabEnabled(2,False)


    # overriding the closeEvent method
    def closeEvent(self, event):
        self.session.close()
        print("Close Event Called")
        
    def dbsetup(self):
        data_dir = user_data_dir(self.appname)

        if not os.path.isdir(data_dir):
            print("Data dir does not exist!")
            try:
                os.makedirs(data_dir)
            except OSError:
                print ("Creation of the data directory %s failed" % data_dir)
            else:
                print ("Successfully created the data directory %s " % data_dir)

        db = {'drivername':'sqlite','database':data_dir+'/'+self.appname+'.db'}
        db_uri=URL.create(**db)
        print(db_uri)

        # Disable echo for production mode
        dbengine = create_engine(db_uri, echo=True)

        Base.metadata.create_all(dbengine)
        Session = sessionmaker(bind=dbengine,expire_on_commit=False)
        self.session = Session()

        # Tables model
        # self.model = tableModel(session=self.session)

        # Queries model
        self.qmodel = QueryModel(session=self.session)
        completedescriptions = QCompleter()
        completedescriptions.setFilterMode(Qt.MatchContains)
        completedescriptions.setModel(self.qmodel)
        self.ui.lE_desc_query.setCompleter(completedescriptions)
        completedescriptions.activated[QtCore.QModelIndex].connect(self.update_disp_query_db)
                
        config_dir = user_config_dir(self.appname)

        numqueries = self.session.query(func.count(CQuery.id)).scalar()
        self.ui.lE_keyq.setToolTip(str("Number of records: %s" % (numqueries)))

        if not os.path.isdir(config_dir):
            print("Config dir does not exist!")
            try:
                os.makedirs(config_dir)
            except OSError:
                print ("Creation of the directory %s failed" % config_dir)
            else:
                print ("Successfully created the directory %s " % config_dir)

        ### Load catalogues from json files
        # self.copy_config_files(config_dir)   
        
        # read json schema, catalogues
        with open(self.resource_path(self.schema_file), 'r') as f:
            data = f.read()

        # Validate catalogue sechema
        catalogue_schema = {}
        if self.validateJSON(data):
            catalogue_schema = json.loads(data)
        else:
            print(json_error)
            # TODO: close app

        # read catalogue source names
        with open(self.resource_path(self.catalogue_file), 'r') as f:
            data = f.read()

        try:
            cats = self.session.query(Catalogue).all()
            catalogue_data = json.loads(data)
            # Validating
            if self.schema_validation(catalogue_data,catalogue_schema):
                print(len(cats),len(catalogue_data))
                if len(cats) < len(catalogue_data):
                    for catalogue in catalogue_data:
                        dbcat = self.session.query(Catalogue).filter_by(name = catalogue["catalogue_name"]).first()
                        if not dbcat:
                            new_cat = Catalogue(name = catalogue["catalogue_name"],
                                                authentication = catalogue["authentication"],
                                                url = catalogue["url"],
                                                signup = catalogue["signup"])
                            self.session.add(new_cat)                            
                            print(new_cat)
                    self.session.commit()
                    cats = self.session.query(Catalogue).all()
                else:
                    print("There are no new catalogues")

                # add cats to
                for cat in cats:
                    self.ui.comboSelectSource.addItem(cat.name,{"id":cat.catalogue_id, "sync": False, "url":cat.url,
                                                                "signup":cat.signup})
                    print(cat)

                print(self.session.new)
            else:
                print("Catalogue data do not meet the catalogue schema")
        except ValueError as err:
            json_error = str(err)
            print(json_error)
            # TODO close app
            
        
    def validateJSON(self, jsonData):
        try:
            json.loads(jsonData)
        except ValueError as err:
            json_error = str(err)
            print(json_error)
            return False
        return True
        
    def load_catalogues(self ):
        json_error = ""

        config_dir = user_config_dir(self.appname)

        self.ui.cmb_cross_ops.addItems(ops.enums)
        self.ui.cmb_filetype_aq.addItems(ftypes.enums)
        

        self.currentrecord = self.session.query(CQuery).filter_by(id = 1).one_or_none()
        if self.currentrecord:
            self.display_query_record()
            
        # read defined columns
        with open(self.resource_path(self.col_defs), 'r') as f:
            data = f.read()

        if self.validateJSON(data):
            # TODO: validate with json schema
            self.column_defs = json.loads(data)
        else:
            print("Error column_defs.json")



    def get_var_name(self,f_fmt, var_name, dvn):
        '''Gets the variable name according to the data source and table name

        Parameters
        ----------
        f_fmt : file format 'speck', 'single fits', 'multiple fits'
        var_name : variable name according to Openspace definitions 
                   'RA, 'DEC', etc.
        dvn : default var name 'ra', 'dec', etc.

        Returns
        -------

        String : the variable name according to data source, GAIA,
                 SDSS, etc or default

        '''
        # TODO: validate 'le_data_source' and 'le_table'
        # print(self.current_query["catalogue_name"])

        if self.currentrecord:
            # data_source = self.current_query["catalogue_name"].split()[1]
            data_source = self.currentrecord.catalogue.name.split()[1]
        else:
            print("No valid current record")
            return;
        
        # if len(self.current_query.get("tables")) > 0:
        #     table_name = self.current_query.get("tables")[0].get("table_name","default")
        if self.currentrecord.ctable:
            table_name = self.currentrecord.ctable[0].name
        else:
            table_name = "default"

        if self.column_defs[f_fmt].get(data_source).get(table_name):
            t_var_name = self.column_defs[f_fmt] \
                       .get(data_source,{}) \
                       .get(table_name,{}) \
                       .get(var_name,{}) \
                       .get("name",dvn)
        else:
            t_var_name = self.column_defs[f_fmt] \
                       .get(data_source,{}) \
                       .get("default",{}) \
                       .get(var_name,{}) \
                       .get("name",dvn)
        return t_var_name


    def set_var_name(self, cmb, var_name, gbox):
        """Set default variable names in the comboboxes and deactivates the
        groupbox 'gbox'

        Parameters
        ----------
        cmb : combobox to be updated.
        var_name : variable name returned by 'get_var_name'
        gbox : group box to be deactivated in case 'var_name' is not in 'cmb'


        Returns
        -------
        Boolean: True if 'var_name' is found in the combobox
        """
        
        index = cmb.findText(var_name)
        if index != -1:
            cmb.setCurrentIndex(index)
            print(var_name,"found")
            return True
        else:
            # gbox.enabled = False
            print(var_name,"not found")
            # TODO: hihglight variable label on the gui
            gbox.setChecked(False)
            return False
        
    
    def speck(self, format):
        """ Find and set appropriate variable names in the speck tab 
        """
        print(self.rdata.data_df.columns,self.rdata.data_df.shape)

        # self.ui.groupBox.enable_cb_ops=True
        # TODO: create a list of comboboxes and iterate on them
        if not self.rdata.data_df.empty:
            # BM25 best matches
            column_names = self.rdata.rank_columns("ra")
            self.ui.cmb_ra.addItems(column_names)
            column_names = self.rdata.rank_columns("dec")
            self.ui.cmb_dec.addItems(column_names)
            column_names = self.rdata.rank_columns(self.ui.cmb_dist_par.currentText().lower())
            self.ui.cmb_rs_par.addItems(column_names)
            column_names = self.rdata.rank_columns("pmra")
            self.ui.cmb_pmra.addItems(column_names)
            column_names = self.rdata.rank_columns("pmdec")
            self.ui.cmb_pmdec.addItems(column_names)
            column_names = self.rdata.rank_columns("radial_velocity")
            self.ui.cmb_rv.addItems(column_names)
            column_names = self.rdata.rank_columns("g_mean_mag")
            self.ui.cmb_gmean_mag.addItems(column_names)
            column_names = self.rdata.rank_columns("bp_mean_mag")
            self.ui.cmb_bp_mean_mag.addItems(column_names)
            # column_names = self.rdata.rank_columns("g_rp")
            # self.ui.cmb_g_rp.addItems(column_names)
            column_names = self.rdata.rank_columns("mean_mag")
            self.ui.cmb_meanmag.addItems(column_names)
            column_names = self.rdata.rank_columns("COLOR_GAAP_u_g")
            self.ui.cmb_gaap.addItems(column_names)

            
            # Default name variable matches from json file
            # x, y and z group box
            vname = self.get_var_name(format,"RA","ra")
            self.set_var_name(self.ui.cmb_ra, vname, self.ui.gbox_xyz)

            vname = self.get_var_name(format,"DEC","dec")
            self.set_var_name(self.ui.cmb_dec, vname, self.ui.gbox_xyz)

            vname = self.get_var_name(format,self.ui.cmb_dist_par.currentText(),"")
            self.set_var_name(self.ui.cmb_rs_par, vname, self.ui.gbox_xyz)

            # speed group box
            vname = self.get_var_name(format,"PMRA","pmra")
            self.set_var_name(self.ui.cmb_pmra, vname, self.ui.gbox_speed)

            vname = self.get_var_name(format,"PMDEC","pmdec")
            self.set_var_name(self.ui.cmb_pmdec, vname, self.ui.gbox_speed)

            vname = self.get_var_name(format,"RADIAL_VELOCITY","radial_velocity")
            self.set_var_name(self.ui.cmb_rv, vname, self.ui.gbox_speed)

            # color group box
            vname = self.get_var_name(format,"G_MEAN_MAG","g_mean_mag")
            self.set_var_name(self.ui.cmb_gmean_mag, vname, self.ui.gbox_color)

            vname = self.get_var_name(format,"BP_MEAN_MAG","bp_mean_mag")
            self.set_var_name(self.ui.cmb_bp_mean_mag, vname, self.ui.gbox_color)

            vname = self.get_var_name(format,"COLOR_GAAP_u_g","COLOR_GAAP_u_g")
            self.set_var_name(self.ui.cmb_gaap, vname, self.ui.gbox_color)


            # Absolute magnitude box
            self.set_var_name(self.ui.cmb_meanmag, vname, self.ui.gbox_mag)

            # vname = self.get_var_name(format,"G_RP","g_rp")
            # self.set_var_name(self.ui.cmb_g_rp, vname, self.ui.gbox_color)

            # TODO: verify that the three variables needed to estimate x, y and z are there
            # If not: disable the group box?.
            #     self.ui.Button_convert.setEnabled(True)
                
        print("Speck format")

    def sfits(self, format):
        print("Sfits")

    def mfits(self, format):
        print("mfits")

    def match_fields(self, file_format):
        """Calls the appropriate function to select variables/columns for
        speck, single fits or multiple fits formats.

        Parameters
        ----------

        file_format : String taken from the current active tab
                      'speck', 'single fits' or 'multiple fits'.

        """
        formats = {
            "Speck": self.speck,
            "Single fits": self.sfits,
            "Multiple fits": self.mfits
        }
        # Execute the function
        return formats.get(file_format)(file_format)
    
    def on_convert(self):
        ci = self.ui.step_tabs.currentIndex()
        if self.ui.step_tabs.tabText(ci) == "Convert":
            ## if self.current_query:
            if self.currentrecord:
                # print(json.dumps(self.current_query,default = self.myconverter, indent=4))
                #if self.current_query.get("filename"):
                self.clear_convert_tab();
                self.ui.lEdit_src_name.setText(self.currentrecord.filepath)
                self.ui.le_data_source.setText(self.currentrecord.catalogue.name)
                if self.currentrecord.ctable:
                    table_name = self.currentrecord.ctable[0].name
                    self.ui.le_table.setText(table_name)
                # self.ui.lEdit_src_name.setText(self.current_query.get("filename",""))
                # self.ui.le_data_source.setText(self.current_query.get("catalogue_name",""))
                # if len(self.current_query.get("tables",[])) > 0:
                #     table_name = self.current_query["tables"][0].get("table_name","")
                #     self.ui.le_table.setText(table_name)
                fnames = self.currentrecord.domeformat
                print("FNAMES:",type(fnames))
                if fnames:
                    # add filenames to combobox_results                    
                    for res in fnames:
                        additional_info = []
                        if res.starttime and res.endtime:
                            additional_info.append("Date:")
                            additional_info.append(str(res.endtime))
                            additional_info.append("Convertion time:")
                            additional_info.append(str(res.endtime - res.starttime))

                        self.ui.comboBox_results.addItem(res.filepath,{"desc":res.description,
                                                                       "info":' '.join(additional_info)})
                        # print(res)
                    idr = self.ui.comboBox_results.currentIndex()
                    self.ui.lE_output_desc.setText(self.ui.comboBox_results.itemData(idr)["desc"])
                    self.statusBar().showMessage(self.ui.comboBox_results.itemData(idr)["info"])
                else:
                    self.statusBar().showMessage("No files converted yet")
                    print("No files converted, fnames:",fnames)
            else:
                self.statusBar().showMessage("Current query not defined")
                print("Current query not defined")

    def update_results_tab(self):
        idr = self.ui.comboBox_results.currentIndex()
        #print("Index results:",idr,self.ui.comboBox_results.currentText())
        if idr != -1:
            self.ui.lE_output_desc.setText(self.ui.comboBox_results.itemData(idr).get("desc"))
            self.statusBar().showMessage(self.ui.comboBox_results.itemData(idr).get("info"))

    def collect_info_convert(self):
        ci = self.ui.format_tabs.currentIndex()
        current_format_tab = self.ui.format_tabs.tabText(ci)
        dest_filename = self.rdata.dest_filename

        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)

        msg.setText("The file {} will be created".format(dest_filename))
        msg.setInformativeText("The following variables will be used")
        msg.setWindowTitle("Convert")
        bdtime = datetime.now()
        # TODO: create new DomeFormat record and save columns converted in ColDomeFormatAssociation
        create_file =  self.create_appropriate_file_format(current_format_tab)
        if create_file:
            info = self.rdata.variables
            msg.setDetailedText("The details are as follows:\n {}".format(json.dumps(info,indent=4)))
            msg.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            #msg.buttonClicked.connect(msgbtn)
	
            retval = msg.exec_()
            if retval == 1024:
                print("Value of pressed message box button:", retval)
                self.rdata.transform(current_format_tab)
                ndf = DomeFormat(query_id=self.currentrecord.id,starttime=bdtime,
                                 endtime=datetime.now(), filepath=dest_filename,
                                 filetype= current_format_tab,
                                 description=self.ui.lE_output_desc.text())
                self.session.add(ndf)
                self.session.commit()

                additional_info = []
                if ndf.starttime and ndf.endtime:
                    additional_info.append("Date:")
                    additional_info.append(str(ndf.endtime))
                    additional_info.append("Convertion time:")
                    additional_info.append(str(ndf.endtime - ndf.starttime))

                self.ui.comboBox_results.addItem(ndf.filepath,{"desc":ndf.description,
                                                               "info":' '.join(additional_info)})
        
            print(ci,current_format_tab)

    def create_appropriate_file_format(self, file_format):
        """
        Collect variable/column names from the current tab to create a
        speck, single fits or multiple fits format file.

        Parameters
        ----------

        file_format : String taken from the current active tab
                      'speck', 'single fits' or 'multiple fits'.

        """
        formats = {
            "Speck": self.speck_file_info,
            "Single fits": self.sfits_file_info,
            "Multiple fits": self.mfits_files_info
        }
        # Execute the function
        return formats.get(file_format)()

    def mfits_files_info(self):
        pass

    def sfits_file_info(self):
        pass

    # Estimates speck variables
    def speck_file_info(self):
        self.rdata.reset_data()
        if self.ui.gbox_speed.isChecked():
            pass
            #TODO: call function to estimate velocity and speed values
            # self.rdata.variables["PMRA"] = self.ui.cmb_pmra.currentText()
            # self.rdata.variables["PMDEC"] = self.ui.cmb_pmdec.currentText()
            # self.rdata.variables["RADIAL_VELOCITY"] = self.ui.cmb_rv.currentText()

        if self.ui.gbox_xyz.isChecked():
            self.rdata.variables["RA"] = self.ui.cmb_ra.currentText()
            self.rdata.variables["DEC"] = self.ui.cmb_dec.currentText()
            # Estimate distance
            self.rdata.est_dist(self.ui.cmb_dist_par.currentText(), # PARALLAX, RED_SHIFT, or DIST
                                  self.ui.cmb_rs_par.currentText())   # Variable name
            self.rdata.estimate_xyz()

            if self.ui.gbox_color.isChecked():
                if self.ui.cmb_gaap.currentText() == "COLOUR_GAAP_u_g":
                    self.rdata.variables["COLOUR_GAAP_u_g"] = "COLOUR_GAAP_u_g"
                    self.rdata.assign_color()
                elif self.ui.cmb_gmean_mag.currentText() == "psfMag_u":
                    self.rdata.variables["G_MEAN_MAG"] = self.ui.cmb_gmean_mag.currentText()
                    self.rdata.variables["BP_MEAN_MAG"] = self.ui.cmb_bp_mean_mag.currentText()
                    self.rdata.estimate_color_sdss()
                else:
                    self.rdata.variables["G_MEAN_MAG"] = self.ui.cmb_gmean_mag.currentText()
                    self.rdata.variables["BP_MEAN_MAG"] = self.ui.cmb_bp_mean_mag.currentText()
                    # self.rdata.variables["G_RP"] = self.ui.cmb_g_rp.currentText()
                    self.rdata.estimate_color()
            
            if self.ui.gbox_mag.isChecked():
                self.rdata.variables["G_MEAN_MAG"] = self.ui.cmb_meanmag.currentText()
                # Estimate absolute magnitude
                self.rdata.estimate_absmag()

        return self.ui.gbox_xyz.isChecked()

            
            
    def empty_keyq(self):
        self.ui.lE_keyq.clear()
        # self.current_query = {}
        self.currentrecord = None

    # def update_new_description(self):
    #     if not self.new_query:
    #         self.new_query = copy.deepcopy(self.current_query)
    #         self.ui.lE_keyq.setText("")
    #     self.new_query["description"]= self.ui.lE_desc_query.text()
    #     print(json.dumps(self.new_query,indent=4))

    # Set tooltips and icons
    def text_tooltips(self):
        cols = "<h2>Required columns</h2><pre><code>0 x \n" \
            "1 y\n" \
            "2 z\n" \
            "3 color\n" \
            "4 - not used\n" \
            "5 absmag\n" \
            "6 - not used\n" \
            "7 - not used\n" \
            "8 - not used\n" \
            "9 - not used\n" \
            "10 - not used\n" \
            "11 - not used\n" \
            "12 - not used\n" \
            "13 vx\n" \
            "14 vy\n" \
            "15 vz\n" \
            "16 speed\n" \
            "</code></pre>"
        self.ui.lbl_speck.setToolTip(cols)

        cols = "<h2>Required columns</h2><pre><code>" \
            "Position_X\n" \
            "Position_Y\n" \
            "Position_Z\n" \
            "Velocity_X\n" \
            "Velocity_Y\n" \
            "Velocity_Z\n" \
            "Gaia_Parallax\n" \
            "Gaia_G_Mag\n" \
            "Tycho_B_Mag\n" \
            "Tycho_V_Mag\n" \
            "Gaia_Parallax_Err\n" \
            "Gaia_Proper_Motion_RA\n" \
            "Gaia_Proper_Motion_RA_Err\n" \
            "Gaia_Proper_Motion_Dec\n" \
            "Gaia_Proper_Motion_Dec_Err\n" \
            "Tycho_B_Mag_Err\n" \
            "Tycho_V_Mag_Err\n" \
            "</code></pre>"
        self.ui.lbl_sfits.setToolTip(cols)
        
        cols = "<h2>Required columns</h2><pre><code>" \
            "ra\n" \
            "ra_error\n" \
            "dec\n" \
            "dec_error\n" \
            "parallax\n" \
            "parallax_error\n" \
            "pmra\n" \
            "pmra_error\n" \
            "pmdec\n" \
            "pmdec_error\n" \
            "phot_g_mean_mag\n" \
            "phot_bp_mean_mag\n" \
            "phot_rp_mean_mag\n" \
            "bp_rp\n" \
            "bp_g\n" \
            "g_rp\n" \
            "radial_velocity\n" \
            "radial_velocity_error\n" \
            "</code></pre>"
        self.ui.lbl_mfits.setToolTip(cols)

        self.ui.ButtonADQL.setToolTip("Generates a query based on" \
                                      " the selected columns and conditions")

        self.ui.Button_submit.setToolTip("Submits the query and saves the" \
                                      " result in a csv file")

        self.ui.Button_nextq.setIcon(qta.icon('fa5s.arrow-right'))
        self.ui.Button_prevq.setIcon(qta.icon('fa5s.arrow-left'))
        self.ui.Button_searchq.setIcon(qta.icon('fa5s.search'))
        self.ui.Button_add_cond.setIcon(qta.icon('fa5.plus-square'))
        self.ui.Button_submit.setIcon(qta.icon('fa5s.download'))
        self.ui.Button_delq.setIcon(qta.icon('fa5.trash-alt',color='blue'))
        self.ui.Button_delq.setToolTip("It is going to delete the current query record")

    def schema_validation(self,jsonData,schema_c):
        try:
            # print(jsonData)
            validate(instance=jsonData, schema=schema_c)
        except jsonschema.exceptions.ValidationError as err:
            json_error = str(err)
            print("schema validation:",json_error)
            return False
        return True


    def resource_path(self, relative_path):
        """ Get absolute path to resource, works for dev and for PyInstaller """
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base_path, relative_path)
    
    def copy_config_files(self,config_dir):
        # catalogue schema
        tmp = self.schema_file 
        self.schema_file = os.path.join(config_dir, self.schema_file)
        if os.path.isfile(self.schema_file):
            print("Catalogue schema %s exists" % self.schema_file)
        else:
            print("Catalogue schema %s does not exist" % self.schema_file)
            try:
                copy(self.resource_path(os.path.join("./config/", tmp)),self.schema_file)
            except OSError as error:
                print(error)
                print ("Copying  %s file failed" % self.schema_file)
            else:
                print ("Config file  %s successfully copied" % self.schema_file)

                    
        tmp = self.catalogue_file
        self.catalogue_file = os.path.join(config_dir, self.catalogue_file)
        if os.path.isfile(self.catalogue_file):
            print("Catalogue file %s exists" % self.catalogue_file)
            # compare creation date
            sc_file = os.path.getmtime(self.catalogue_file)
            gc_file = os.path.getmtime(self.resource_path(os.path.join("./config/", tmp)))
            print(sc_file,gc_file)
            if sc_file < gc_file:
                print("Updating catalogue file %s" % self.catalogue_file)
                try:
                    copy(self.resource_path(os.path.join("./config/", tmp)),self.catalogue_file)
                except OSError as error:
                    print(error)
                    print ("Updating  %s file failed" % self.catalogue_file)
                else:
                    print ("Config file  %s successfully updated" % self.catalogue_file)        
        else:
            print("Catalogue file %s does not exist" % self.catalogue_file)
            try:
                copy(self.resource_path(os.path.join("./config/", tmp)),self.catalogue_file)
            except OSError as error:
                print(error)
                print ("Copying  %s file failed" % self.catalogue_file)
            else:
                print ("Config file  %s successfully copied" % self.catalogue_file)


        tmp = self.col_defs
        self.col_defs = os.path.join(config_dir, self.col_defs)
        if os.path.isfile(self.col_defs):
            print("Column definition file %s exists" % self.col_defs)
            # compare creation date
            sc_file = os.path.getmtime(self.col_defs)
            gc_file = os.path.getmtime(self.resource_path(os.path.join("./config/", tmp)))
            print(sc_file,gc_file)
            if sc_file < gc_file:
                print("Updating column definition file %s" % self.col_defs)
                try:
                    copy(self.resource_path(os.path.join("./config/", tmp)),self.col_defs)
                except OSError as error:
                    print(error)
                    print ("Updating  %s file failed" % self.col_defs)
                else:
                    print ("Column definition file  %s successfully updated" % self.col_defs)
        else:
            print("Column definition file %s does not exist" % self.col_defs)
            try:
                copy(self.resource_path(os.path.join("./config/", tmp)),self.col_defs)
            except OSError as error:
                print(error)
                print ("Copying  %s file failed" % self.col_defs)
            else:
                print ("Config file  %s successfully copied" % self.col_defs)
                    

            
            
    def sourceCatalogueChange(self):
        '''
        Updates the tables according to the selected catalogue
        '''

        s_context = self.ui.comboSelectSource.currentText()
        tables_sync = self.ui.comboSelectSource.currentData()
        print("Selected catalogue: ",s_context,tables_sync)
        self.clean_ui_items()
        print("Context",s_context)
        tables = []
        context = s_context.split()[0]
        cat = s_context.split()[1]
        print(cat,context)
        if self.ad_context[cat]["auth"] and not self.ad_context[cat]["token"]:
            print("Authentication required")
            login = signIn(parent=self,catalogue=cat,urlsignup = tables_sync["signup"])
            if login.dialog.exec_():
                if login.getToken():
                    self.ad_context[cat]["token"] = login.getToken()
                else:
                    self.ad_context[cat]["token"] = "Authenticated"

        if self.ad_context[cat]["token"] and not tables_sync["sync"]:
            # Query catalogue tables from local database
            dbtabs = self.session.query(Cat_table).join(Catalogue).filter(Catalogue.name==s_context).count()

            # Download tables from astronomical database server
            tabs = cats.get_tables(cat)(context)

            # If there are new tables, add them to the database
            # check length of tabs and number of elements in database
            print("dbtabs: ",dbtabs,"online tabs:",len(tabs))
            if dbtabs < len(tabs):
                dbcat = self.session.query(Catalogue).filter(Catalogue.name == s_context).one_or_none()
                print("From the database:",dbcat)
                for item in tabs:
                    isnewtab = self.session.query(Cat_table).filter(and_(Cat_table.name==item,
                                                       Cat_table.catalogue_id==dbcat.catalogue_id)).one_or_none()
                    if isnewtab is None:
                        isnewtab = Cat_table(catalogue_id=dbcat.catalogue_id,name=item)
                        self.session.add(isnewtab)
                        print(isnewtab,"--",item)
                self.session.commit()
            # Set sync flag to true
            ci = self.ui.comboSelectSource.currentIndex()
            tables_sync["sync"] = True
            self.ui.comboSelectSource.setItemData(ci,tables_sync)               

        # Update listView data tables
        self.model = tableModel(session=self.session,catname=s_context)
        self.ui.listView.setModel(self.model)

    def clear_convert_tab(self):
        # convert tab
        # Source file to convert to -speck file
        self.ui.lEdit_src_name.clear()

        # Source catalog line edit
        self.ui.le_data_source.clear()

        # Table name
        self.ui.le_table.clear()

        # output file description
        self.ui.lE_output_desc.clear()

        self.ui.comboBox_results.clear()
        self.statusBar().clearMessage()
        
    def clear_shared_items(self):
        
        # self.ui.lE_keyq.clear()
        self.treeModel.clear()
        self.root = self.treeModel.invisibleRootItem()
        self.treeModel.layoutChanged.emit()
        self.clearBoxLayout(self.vbox)
        self.ui.comboBox_3.clear()
        self.ui.comboBox.clear()
        self.clearBoxLayout(self.ac_vbox)
        self.ui.plainTextEdit_2.clear()
        self.ui.lE_filepath_ad.clear()
        self.statusBar().clearMessage()

    def clean_ui_items(self):
        # self.model.clear()
        # self.model.layoutChanged.emit()
        self.ui.lE_desc_query.clear()
        self.clear_shared_items()

    def display_query_record(self):
        '''
        Displays a query record called in a function, not a signal
        '''
        print(self.currentrecord.catalogue.name)

        # Source catalogue
        index = self.ui.comboSelectSource.findText(self.currentrecord.catalogue.name)
        if index != self.ui.comboSelectSource.currentIndex():
            self.ui.comboSelectSource.setCurrentIndex(index)

        # Description
        self.ui.lE_desc_query.setText(self.currentrecord.description)
        # key
        self.ui.lE_keyq.setText(str(self.currentrecord.id))

        
        # Tables
        for ctab in self.currentrecord.ctable:
            print("TABLE:", ctab)
            self.add_treeItem(ctab.name)
        
        # Column conditions
        for cond in self.currentrecord.colqassoc:
            print("Condition:",cond)
            print("Column:",cond.column)
            if  cond.value:
                self.add_condition(cond.column.ctable.name, cond.column.name,
                                   cond.operator, str(cond.value))
            else:
                self.add_condition(cond.column.ctable.name, cond.column.name)
            
        # Cross column conditions
        for croscond in self.currentrecord.ccquery:
            print("CROSS QUERY CONDITION:",croscond)
            print("LEFT:",croscond.lc.ctable.name, croscond.lc.name)
            print("Condition:",croscond.operator)
            print("RIGHT:",croscond.rc.ctable.name,croscond.rc.name)
            self.add_condition_across_table(' '.join(['.'.join([croscond.lc.ctable.name, croscond.lc.name]),
                                                     croscond.operator,
                                                      '.'.join([croscond.rc.ctable.name,croscond.rc.name])])
            )

        # Query
        self.ui.plainTextEdit_2.insertPlainText(self.currentrecord.adql)

        # File name
        self.ui.lE_filepath_ad.setText(self.currentrecord.filepath)

        index = self.ui.cmb_filetype_aq.findText(self.currentrecord.filetype)
        if index >= 0:
            self.ui.cmb_filetype_aq.setCurrentIndex(index)

        additional_info = []
        if self.currentrecord.starttime and self.currentrecord.endtime:
            additional_info.append("Date:")
            additional_info.append(str(self.currentrecord.endtime))
            additional_info.append("Execution time:")
            additional_info.append(str(self.currentrecord.endtime - self.currentrecord.starttime))
            self.statusBar().showMessage(' '.join(additional_info))
        


    def update_disp_query_db(self):
        '''
        Displays a query record called by a signal
        '''
        print("SENDER:",type(self.sender()))
        # print("Object name:",self.sender().objectName())
        if isinstance(self.sender(),QCompleter):
            self.currentrecord = self.qmodel.currentrecord
        elif self.sender().objectName() == 'lE_desc_query':
            print("--- QLineEdit--")
            self.currentrecord = None
            # TODO: clear key lineedit
            # self.clear_shared_items()
        elif self.ui.lE_keyq.text().isnumeric():
            q_key = int(self.ui.lE_keyq.text())
            print("q_key:",q_key)
            self.currentrecord = self.session.query(CQuery).filter_by(id = q_key).one_or_none()
            # self.clear_shared_items()
        else:
            self.currentrecord = None

        self.clear_shared_items()
        
        if not self.currentrecord:
            print("No record found")
            # self.clear_shared_items()
            return
        # print(cr)

        self.display_query_record()
        


    def collect_query_elements(self):
        self.new_query = {}

        self.new_query["description"] = self.ui.lE_desc_query.text()
        self.new_query["catalogue_name"] = self.ui.comboSelectSource.currentText()
        self.new_query["tables"] = []
        self.new_query["cross_conditions"] = []
        # self.new_query["authentication"] perhaps not needed
        
        print(range(self.vbox.count()))
        for i in range(self.vbox.count()):
            hlayout = self.vbox.itemAt(i)
            print(i,type(hlayout))
            if hlayout.spacerItem() is None:
                print("ItemAt 0:",str(hlayout.itemAt(0).widget()))
                if hlayout.itemAt(1) is not None:
                    table = hlayout.itemAt(1).widget().text()
                    col_name = hlayout.itemAt(2).widget().text()
                    print("ItemAt 1:",table," ItemAt 2:",col_name)
                    cond = {"column": col_name}
                    if hlayout.itemAt(4).widget().text():
                        cond["q_condition"] = hlayout.itemAt(3).widget().currentText()
                        cond["value"] = hlayout.itemAt(4).widget().text()

                    # find the index position of the table
                    pt = next((i for i, item in enumerate(self.new_query["tables"]) if item["table_name"] == table), None)
                
                    if pt is not None:  # Table is at position pt
                        print("Table found at position",pt)
                        if (self.new_query["tables"][pt]["query_conditions"]):
                            self.new_query["tables"][pt]["query_conditions"].append(cond)
                        else:
                            self.new_query["tables"][pt]["query_conditions"] = [cond]
                    else:  # Table is not there
                        self.new_query["tables"].append({"table_name":table,"query_conditions":[cond]})

        conds = []
        for i in range(self.ac_vbox.count()):
            hlayout = self.ac_vbox.itemAt(i)
            print(type(hlayout),end=' ')
            if hlayout.spacerItem() is None:
                if hlayout.itemAt(1) is not None:
                    cond = hlayout.itemAt(2).widget().text()
                    c_cond = {}
                    if cond not in conds:
                        conds.append(cond)
                        s = cond.split(' ')
                        print("What is in s: ",s)
                        c_cond["col_left"] = s[0]
                        if len(s) == 3:
                            c_cond["c_condition"] = s[1]
                            c_cond["col_right"] = s[2]
                        else:
                            c_cond["c_condition"] = ' '.join([s[1], s[2]])
                            c_cond["col_right"] = s[3]

                        self.new_query["cross_conditions"].append(c_cond)

        print(json.dumps(self.new_query,default = self.myconverter,indent=4))        

    def generate_ADQL(self):
        self.ui.plainTextEdit_2.clear()
        
        self.collect_query_elements()
        qtables = []
        qcols = []
        qconds = []
        for table in self.new_query["tables"]:
            qtables.append(table["table_name"])
            for qcond in table["query_conditions"]:
                qcols.append(qcond["column"])
                if "q_condition" in qcond.keys():
                    qconds.append(' '.join([qcond["column"],qcond["q_condition"],qcond["value"]]) )

        if "cross_conditions" in self.new_query.keys():
            for c_cond in self.new_query["cross_conditions"]:
                qconds.append(' '.join([c_cond["col_left"], c_cond["c_condition"], c_cond["col_right"]]))
        
        self.ui.plainTextEdit_2.insertPlainText("SELECT TOP 1000 " + ', '.join(qcols))
        self.ui.plainTextEdit_2.insertPlainText(" FROM " + ', '.join(qtables))

        if qconds:
            self.ui.plainTextEdit_2.insertPlainText(" WHERE " + ' AND '.join(qconds))
        # self.ui.plainTextEdit_2.moveCursor (QTextCursor.End)

    # Filename to save the converted data
    def output_dst_name(self):
        filename,_ = QFileDialog.getSaveFileName(self, 'Save File', filter='*.speck')
        # query = self.ui.plainTextEdit_2.toPlainText()
        
        if filename:
            speck_ext = re.search(".speck$",filename,flags=re.IGNORECASE)
            if (speck_ext == None):
                filename = filename + ".speck" 
            self.rdata.dest_filename = filename
            self.collect_info_convert()
            # TODO: after successfully converting the file add the file to combobox_results
            #if self.ui.lEdit_src_name.text():
                # TODO: processing screen
                # busy_screen = loadingScreen(parent=self,query=query,filename=filename)
                # activate convert button
            #    self.ui.Button_convert.setEnabled(True)
                # self.collect_info_convert
                # if busy_screen.exec_():
                #     print("Success")
                # else:
                #     print("Cancel")

            
    def update_src_name(self):
        fname,_ = QFileDialog.getOpenFileName(self, 'Open file',filter="csv files (*.csv)")
        if fname:
            self.ui.lEdit_src_name.setText(fname)
        
    def select_file(self):

        if self.ui.lEdit_src_name.text():
            source_filename = self.ui.lEdit_src_name.text()
            # TODO: do not load the complete file yet, perhaps only the header to get the columnames
            self.rdata.read("csv")(source_filename)
            # Add items to combo boxes
            self.ui.cmb_ra.clear()
            self.ui.cmb_dec.clear()
            self.ui.cmb_rs_par.clear()

            self.ui.cmb_pmra.clear()
            self.ui.cmb_pmdec.clear()
            self.ui.cmb_rv.clear()

            self.ui.cmb_gmean_mag.clear()
            self.ui.cmb_bp_mean_mag.clear()
            # self.ui.cmb_g_rp.clear()
            self.ui.cmb_gaap.clear()

            self.ui.cmb_meanmag.clear()

            self.ui.gbox_xyz.setChecked(True)
            self.ui.gbox_speed.setChecked(True)
            self.ui.gbox_color.setChecked(True)
            self.ui.gbox_mag.setChecked(True)
            
            print(source_filename)
            id_file_format = self.ui.format_tabs.currentIndex()
            file_format = self.ui.format_tabs.tabText(id_file_format)
            self.match_fields(file_format)


            # TODO: verify that the file 'lEdit_src_name.text()'  exists or use a label
            if not self.ui.lEdit_src_name.text():
                pass
                # self.ui.Button_convert.setEnabled(False)

    def update_rank(self):
        if self.ui.cmb_rs_par.count() > 0:
            self.ui.cmb_rs_par.clear()
            column_names = self.rdata.rank_columns(self.ui.cmb_dist_par.currentText().lower())
            self.ui.cmb_rs_par.addItems(column_names)
            vname = self.get_var_name("Speck",self.ui.cmb_dist_par.currentText(),"")
            self.set_var_name(self.ui.cmb_rs_par, vname, self.ui.gbox_xyz)

    # https://code-maven.com/serialize-datetime-object-as-json-in-python
    def myconverter(self,o):
        if isinstance(o, datetime):
            return o.__str__()
            
    def run_ADQL(self):
        filename,_ = QFileDialog.getSaveFileName(self, 'Save File', filter='*.csv')
        query = self.ui.plainTextEdit_2.toPlainText()
        print(filename,query)
        
        if filename and query:
            self.collect_query_elements()
            csv_ext = re.search(".csv$",filename,flags=re.IGNORECASE)
            if (csv_ext == None):
                filename = filename + ".csv" 

            begin_time = time.time()
            bddtime = datetime.now()
            cat = self.new_query["catalogue_name"].split()[1]
            datasetName = self.new_query["catalogue_name"].split()[0]
            busy_screen = loadingScreen(parent=self,
                                        catalogue = cat,
                                        dataset = datasetName,
                                        query=query,filename=filename)
            # new_key = max(self.queries_data.keys())+1
            if busy_screen.exec_():
                self.new_query["query"] = query
                self.new_query["execution_time"] = time.time() - begin_time
                self.new_query["filetype"] = self.ui.cmb_filetype_aq.currentText()
                self.new_query["filename"] = filename
                self.new_query["date"] = datetime.now()
                # self.queries_data[new_key]=self.new_query
                # print(json.dumps(self.queries_data,default = self.myconverter,indent=4))

                dbcat = self.session.query(Catalogue).filter_by(name=self.new_query["catalogue_name"]).one()

                dbnewquery = CQuery(bddtime, datetime.now(), filename, self.new_query["filetype"],
                                    self.new_query["description"], query, dbcat)
                self.session.add(dbnewquery)
                self.session.commit()
                # Add tables involved in the query
                for jtable in self.new_query["tables"]:
                    dbtab = self.session.query(Cat_table).filter_by(name=jtable["table_name"],
                                                                      catalogue_id=dbcat.catalogue_id).one()
                    dbnewquery.ctable.append(dbtab)
                    # Add column conditions
                    for jcol in jtable["query_conditions"]:
                        op = jcol.get("q_condition")
                        if op:
                            cond = ColQueryAssociation(cquery_id=dbnewquery.id,operator=op, value = jcol["value"])
                        else:
                            cond = ColQueryAssociation(cquery_id=dbnewquery.id)

                        cond.column = self.session.query(TColumn).filter_by(name=jcol["column"],
                                                                               table_id=dbtab.id).one()
                        dbnewquery.colqassoc.append(cond)

                # TODO: store column keys in the GUI, in a hidden label (the code below can be greatly reduced)
                for cconds in self.new_query["cross_conditions"]:
                    tab_col = cconds["col_left"].rsplit(".",1)
                    dbtab = self.session.query(Cat_table).filter_by(name=tab_col[0],
                                                                    catalogue_id=dbcat.catalogue_id).one()                    
                    lcol =  cond.column = self.session.query(TColumn).filter_by(name=tab_col[1],
                                                                                table_id=dbtab.id).one()

                    tab_col = cconds["col_right"].rsplit(".",1)
                    dbtab = self.session.query(Cat_table).filter_by(name=tab_col[0],
                                                                    catalogue_id=dbcat.catalogue_id).one()                    
                    rcol =  cond.column = self.session.query(TColumn).filter_by(name=tab_col[1],
                                                                               table_id=dbtab.id).one()
                    newcross_cond = CrossTableAssociation(lcolumn_id=lcol.id, rcolumn_id=rcol.id,
                                                          operator=cconds["c_condition"])
                    dbnewquery.ccquery.append(newcross_cond)
                    
                self.session.add(dbnewquery)
                self.session.commit()
                self.currentrecord = dbnewquery
                self.ui.lE_keyq.setText(str(dbnewquery.id))
                numqueries = self.session.query(func.count(CQuery.id)).scalar()
                self.ui.lE_keyq.setToolTip(str("Number of records: %s" % (numqueries)))
                print("Success")
            else:
                print("Cancel")

    def add_condition_across(self):
        self.add_condition_across_table(self.ui.comboBox.currentText() + ' ' + \
                                        self.ui.cmb_cross_ops.currentText() + ' ' + \
                                        self.ui.comboBox_3.currentText())


    def on_cb1_changed(self, value):
        text_cb3 = self.ui.comboBox_3.currentText()
        if value != text_cb3:
            self.ui.Button_add_cond.setEnabled(True)
        else:
            self.ui.Button_add_cond.setEnabled(False)

    def on_cb3_changed(self, value):
        text_cb = self.ui.comboBox.currentText()
        if value != text_cb:
            self.ui.Button_add_cond.setEnabled(True)
        else:
            self.ui.Button_add_cond.setEnabled(False)

    def add_treeItem(self,tab_name):
        # TODO load tree items from the database
        if not self.treeModel.findItems(tab_name, QtCore.Qt.MatchExactly):
            parent = QtGui.QStandardItem(tab_name)
            self.root.appendRow(parent)
            s_context = self.ui.comboSelectSource.currentText()
            print("S_CONTEXT:",s_context)
            # context = s_context.split()[0]
            cat = s_context.split()[1]
            datasetName = s_context.split()[0]
            # The following line should be replaced by a call to the database
            x_table = cats.get_columns(cat)(tab_name,datasetName)
            print("TABLE NAME:",tab_name)
            # Update columns of the selected table in the database
            catid = self.ui.comboSelectSource.currentData()["id"]
            dbtab = self.session.query(Cat_table).filter(and_(Cat_table.name == tab_name,Cat_table.catalogue_id==catid)).one_or_none()
            ndbcols = self.session.query(TColumn).join(Cat_table).filter(Cat_table.id==dbtab.id).count()
            print("server table:",len(x_table),"local table:",ndbcols)
            if len(x_table) > ndbcols:
                for column in x_table:
                    isnewcol = self.session.query(TColumn).filter(and_(TColumn.table_id==dbtab.id,
                                                                        TColumn.name==column)).one_or_none()
                    if isnewcol is None:
                        isnewcol = TColumn(table_id=dbtab.id,name=column)
                        self.session.add(isnewcol)
                        print(isnewcol,"--")
                self.session.commit()
            
            # TODO: Load tree from the database
            for column in x_table:
                # print(column,end=' ')
                child = QtGui.QStandardItem(column)
                parent.appendRow(child)
                self.ui.comboBox.addItem(tab_name+'.'+column)
                self.ui.comboBox_3.addItem(tab_name+'.'+column)
            self.treeModel.layoutChanged.emit()
            
    def on_table_clicked(self):
        indexes = self.ui.listView.selectedIndexes()  # get lines that are selected
        if indexes:  # if any were actually selected
            #index = indexes[0]  # in single select mode, will only be the first index
            table_name = indexes[0].data()
            print(indexes[0].row(),table_name)
            self.add_treeItem(table_name)
            
    def on_tree_clicked(self):
        indexes = self.ui.tablesTree.selectedIndexes()  # get lines that are selected
        if indexes:  # if any were actually selected
            if indexes[0].parent().data():   # if the selected index is not a table
                tab_name = indexes[0].parent().data()
                col_name = indexes[0].data()
                print("parent name: ",tab_name," index data: ",col_name)
                self.add_condition( tab_name,col_name)
                # self.empty_keyq()

    def add_condition_across_table(self,condition):
        hbox = QHBoxLayout()
        button = QPushButton(qta.icon('fa5.trash-alt',color='blue'),"")
        button.clicked.connect(lambda: self.remove_condition(hbox))
        var_name = QLabel(condition)
        hbox.addWidget(button)
        hbox.addStretch()
        hbox.addWidget(var_name)
        self.ac_vbox.addLayout(hbox)

    def clearBoxLayout(self,layout):
        print("-- -- input layout: "+str(layout))
        for i in reversed(range(layout.count())):
            layoutItem = layout.itemAt(i)
            if layoutItem.widget() is not None:
                widgetToRemove = layoutItem.widget()
                print("found widget: " + str(widgetToRemove))
                widgetToRemove.setParent(None)
                layout.removeWidget(widgetToRemove)
            elif layoutItem.spacerItem() is not None:
                print("found spacer: " + str(layoutItem.spacerItem()))
            else:
                layoutToRemove = layout.itemAt(i)
                print("-- found Layout: "+str(layoutToRemove))
                self.clearBoxLayout(layoutToRemove)
        # for i in reversed(range(self.vbox.count())):
        #     layoutItem = self.vbox.itemAt(i)
        #     if layoutItem.spacerItem() is None:
        #         self.remove_condition(layoutItem)
            

    def add_condition(self, parent_name,column_name,operator=None,f_value=None):
        hbox = QHBoxLayout()
        hbox.addStretch(1)
        par_name = QLabel(parent_name)
        par_name.hide()
        var_name = QLabel(column_name)
        cb = QComboBox()
        # cb.addItems(self.cond_operators)
        cb.addItems(ops.enums)
        if operator is not None:
            index = cb.findText(operator)
            if index >= 0:
                cb.setCurrentIndex(index)
        cb.setEnabled(False)
        value  = QLineEdit()
        value.setValidator(QDoubleValidator())
        value.textChanged.connect(lambda: self.enable_cb_ops(cb,value.text()))
        if f_value is not None:
            value.setText(f_value)
            # cb.setEnabled(True)
        value.textEdited.connect(self.empty_keyq)
        # cb.currentIndexChanged.connect(lambda: self.empty_keyq_cond(value.text()))
        fa5_trash = qta.icon('fa5.trash-alt',color='blue')
        button = QPushButton(fa5_trash,"")
        # button.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_TrashIcon')))

        # value.textChanged.connect(lambda: self.update_value_new_query(parent_name,
        #                                                      column_name,cb.currentText(),value.text()))
        
        button.clicked.connect(lambda: self.remove_condition(hbox,parent_name,
                                                             column_name,cb.currentText(),value.text()))
        hbox.addWidget(par_name)
        hbox.addWidget(var_name)
        hbox.addWidget(cb)
        hbox.addWidget(value)
        hbox.addWidget(button)
        self.vbox.addLayout(hbox)

    def enable_cb_ops(self, combo_operators,value_cond):
        if value_cond:
            combo_operators.setEnabled(True)
        else:
            combo_operators.setEnabled(False)

        # def update_value_new_query(self,p_name,col_name,operator,val):
    #     pass

    def remove_condition(self,box,p_name,col_name,operator,val):
        print("Remove condition",p_name,col_name,operator,val)
        # if val:
        # https://stackoverflow.com/questions/8653516/python-list-of-dictionaries-search
        #     ps = next((i for i, item in enumerate(self.new_query["tables"][0]["query_conditions"]) \
        #            if item["column"] == col_name and item["value"]==val), None)
        # else:
        #     ps = next((i for i, item in enumerate(self.new_query["tables"][0]["query_conditions"]) \
        #            if item["column"] == col_name), None)
        # print("position: ",ps)
        layout_item = box.itemAt(1).widget()
        #print(layout_item.text())
        # https://stackoverflow.com/questions/4528347/clear-all-widgets-in-a-layout-in-pyqt/13103617
        for i in reversed(range(box.count())): 
            widgetToRemove = box.itemAt(i).widget()
            if widgetToRemove is not None:
                print("found widget: " + str(widgetToRemove))
                # remove it from the gui
                widgetToRemove.setParent(None)
                # remove it from the layout list
                box.removeWidget(widgetToRemove)
        # for i in range(box.count()):
        #     print(i, type(box.itemAt(i).widget()))

        self.vbox.removeItem(box)
        self.empty_keyq()
        

app = QApplication(sys.argv)
w = AppWindow()
w.show()
sys.exit(app.exec_())
