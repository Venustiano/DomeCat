# from PySide2.QtWidgets import *
# from PySide2.QtCore import *
# from PySide2.QtGui import *
from PyQt5 import QtCore, QtGui, QtWidgets 
from PyQt5.QtCore import Qt
from dbmodel import Catalogue, Cat_table, CQuery
from sqlalchemy.orm import sessionmaker

class tableModel(QtCore.QAbstractListModel):
#    def __init__(self, *args, tables=None, **kwargs):
    def __init__(self, *args, session, catname = 'DR GAIA', **kwargs):
        super(tableModel, self).__init__(*args, **kwargs)
        # tuples of (bool, str)
        self.session = session
        self.catname=catname
        self.count = None
        # self.tables = self.refresh() # tables or []  # self.todos = list that is passed or a blank list
        self.refresh()
        # self.tick = QImage('tick.png')

    def refresh(self):
        print("From tableModel:",self.session,self.catname)
        self.tables = self.session.query(Cat_table).join(Catalogue).filter(Catalogue.name==self.catname).all()

    # Have to implement this. QT will call it whenever it wants, e.g. if we say data is updated
    def data(self, index, role):
        # index: contains .row() and .column(). For this, column will be always 0
        # role: a flag from QT that indicates what is being requested.
        # role will be DisplayRole for the main data. Other things include
        # tooltips, status bars etc. See table in tutorial for options.
        # https://doc.qt.io/qt-5/qt.html#ItemDataRole-enum

        if role == Qt.DisplayRole:  # the main data view role, in this case expects a string (QString)
            #status, text = self.todos[index.row()]
            # print("From tableModel data()",self.tables)
            value = self.tables[index.row()]
            
            return "%s" % (value.name)

        # if role == Qt.DecorationRole: # a different role, this will update at the same time too
        #     status, _ = self.todos[index.row()]
        #     if status:
        #         return self.tick

    # Have to implement a way to determine how many items there are
    def rowCount(self, index):
        return len(self.tables)

    def clear(self):
        self.tables.clear()


class QueryModel(QtCore.QAbstractListModel):
    def __init__(self, *args, session, **kwargs):
        super(QueryModel, self).__init__(*args, **kwargs)
        # tuples of (bool, str)
        self.session = session
        self.count = None
        self.refresh()
        # self.tick = QImage('tick.png')

    def refresh(self):
        print("From queryModel:",self.session)
        self.queries = self.session.query(CQuery).all()
        # print("From queryModel:",self.queries[1])

    # Have to implement this. QT will call it whenever it wants, e.g. if we say data is updated
    def data(self, index, role):
        # index: contains .row() and .column(). For this, column will be always 0
        # role: a flag from QT that indicates what is being requested.
        # role will be DisplayRole for the main data. Other things include
        # tooltips, status bars etc. See table in tutorial for options.
        # https://doc.qt.io/qt-5/qt.html#ItemDataRole-enum

        if role == Qt.DisplayRole or role == Qt.EditRole:  # the main role, in this case expects a string (QString)
            # print("From tableModel data()",self.tables)
            value = self.queries[index.row()]
            self.currentrecord = value

            print("VALUE.NAME:",value.description)
            # return  "%s : %s" % (value.description, value.id)
            return  "%s" % (value.description)

        # if role == Qt.DecorationRole: # a different role, this will update at the same time too
        #     status, _ = self.todos[index.row()]
        #     if status:
        #         return self.tick

    # Have to implement a way to determine how many items there are
    def rowCount(self, index):
        return len(self.queries)

    def clear(self):
        self.queries.clear()

