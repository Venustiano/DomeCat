# Create a function to import this file

# https://realpython.com/python-sqlite-sqlalchemy/
# https://docs.sqlalchemy.org/en/14/orm/tutorial.html
# 

from sqlalchemy import Column, Integer, Float,  String, ForeignKey, Table, Sequence, Boolean, DateTime, Enum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship, backref
from sqlalchemy.ext.declarative import declarative_base

# DB_URL="mysql+mysqldb://<user>:<password>@<host>:<port>/<db_name>"
# scoped_engine = create_engine(DB_URL)
# Base = declarative_base()
# Base.metadata.create_all(scoped_engine)

Base = declarative_base()

class Catalogue(Base):
    __tablename__ = "catalogue"
    catalogue_id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
    name = Column(String(50))
    description = Column(String(2048))
    authentication = Column(Boolean,default=True)
    url = Column(String(512))
    signup = Column(String(512))
    template = Column(String(32))

    ctable = relationship("Cat_table", back_populates="catalogue")
    cquery = relationship("CQuery", back_populates="catalogue",lazy="dynamic")

    def __repr__(self):
        return "<Catalogue(name='%s', description='%s', authentication = '%r')>" % (
            self.name, self.description, self.authentication)

cquery_tables = Table('cquery_tables', Base.metadata,
                      Column('cquery_id',ForeignKey("cquery.id"), primary_key=True),
                      Column('ctable_id',ForeignKey("ctable.id"), primary_key=True),
)
    
class Cat_table(Base):
    __tablename__ = "ctable"
    id = Column(Integer, primary_key=True)
    catalogue_id = Column(Integer, ForeignKey('catalogue.catalogue_id'))
    name = Column(String(100))
    description = Column(String(4096))

    tcolumn = relationship("TColumn",back_populates ="ctable")
    catalogue = relationship("Catalogue", back_populates="ctable")

    cquery = relationship('CQuery', secondary = cquery_tables, back_populates='ctable')

    def __repr__(self):
        return "<Table(id = '%s', name='%s', description='%s')>" % (
            self.id, self.name, self.description)

label_var = Enum('RA','DEC','PARALLAX','DISTANCE','REDSCHIFT', 'RA-VELOCITY', 'DEC-VELOCITY','RADIAL_VELOCITY',
                 'MAG (Lo freq)','Mag (Hi freq)', 'color','Absolute Magnitude')
    
class TColumn(Base):
    __tablename__ = "tcolumn"
    id = Column(Integer, primary_key=True)
    table_id = Column(Integer, ForeignKey('ctable.id'))
    name = Column(String(100))
    description = Column(String(4096))
    as_var = Column(label_var,nullable=True)

    ctable = relationship("Cat_table", back_populates="tcolumn")

    aquery = relationship("ColQueryAssociation",back_populates="column")

    adome = relationship('ColDomeFormatAssociation',back_populates="column")

    ltcolumn = relationship("CrossTableAssociation",backref='lc',
                            primaryjoin="TColumn.id==CrossTableAssociation.lcolumn_id")
    rtcolumn = relationship("CrossTableAssociation",backref='rc',
                            primaryjoin="TColumn.id==CrossTableAssociation.rcolumn_id")
    
    def __repr__(self):
        return "<Column(id = '%s', name='%s', description='%s')>" % (
            self.id, self.name, self.description)


ftypes = Enum("csv","fits","json","vot")


# TODO: finish CQuery, ADD enum for comparisons, assosiation object
class CQuery(Base):
    __tablename__ = "cquery"
    id = Column(Integer, primary_key=True)
    catalogue_id = Column(Integer, ForeignKey('catalogue.catalogue_id'))
    # starttime = Column(DateTime(timezone=True), server_default=func.now())
    # endtime = Column(DateTime(timezone=True), onupdate=func.now())
    starttime = Column(DateTime(timezone=True))
    endtime = Column(DateTime(timezone=True))    
    filepath = Column(String(4096))
    filetype = Column(ftypes)
    description = Column(String)
    numrows = Column(Integer)
    adql = Column(String)

    catalogue = relationship("Catalogue", back_populates="cquery")
    ctable = relationship("Cat_table",secondary=cquery_tables,back_populates='cquery')

    colqassoc = relationship("ColQueryAssociation",back_populates="cquery")
    domeformat = relationship("DomeFormat",back_populates="cquery")

    ccquery = relationship("CrossTableAssociation",back_populates="cquery")

    def __init__(self, starttime, endtime, filepath, filetype, description, adql, catalogue, numrows = None):
        self.starttime = starttime
        self.endtime = endtime
        self.filepath = filepath
        self.filetype = filetype
        self.description = description
        self.numrows = numrows
        self.adql = adql
        self.catalogue = catalogue

    def __repr__(self):
        return "<Query(id = '%s', starttime='%s', endtime='%s', file path= '%s', description= '%s')>" % (
            self.id, self.starttime, self.endtime, self.filepath, self.description)

class DomeFormat(Base):
    '''
    Creates table to store records of transformed files into dome format
    '''
    __tablename__ = 'domeformat'
    df_id = Column(Integer, primary_key=True)
    query_id = Column(Integer, ForeignKey('cquery.id'),nullable=True)
    filepath = Column(String(4096))
    filetype = Column(Enum("Speck","Single fits","Multiple fits"))
    starttime = Column(DateTime(timezone=True))
    endtime = Column(DateTime(timezone=True))
    description = Column(String)
    
    acol = relationship("ColDomeFormatAssociation",back_populates="domeformat")
    cquery = relationship("CQuery",back_populates="domeformat")

    def __init__ (self, query_id,starttime, endtime, filepath, filetype, description):
        self.query_id = query_id
        self.starttime = starttime
        self.endtime = endtime
        self.filepath = filepath
        self.filetype = filetype
        self.description = description

    def __repr__(self):
        return "<DomeFormat(id = '%s', starttime='%s', endtime='%s', file path= '%s', description= '%s')>" % (
            self.df_id, self.starttime, self.endtime, self.filepath, self.description)
        
class ColDomeFormatAssociation(Base):
    __tablename__ = 'coldomeformatassociation'
    col_id = Column(ForeignKey('tcolumn.id'),primary_key=True)
    dformat_id = Column(ForeignKey('domeformat.df_id'),primary_key=True)
    as_var = Column(label_var)

    domeformat = relationship("DomeFormat",back_populates="acol")
    column = relationship("TColumn",back_populates="adome")

ops = Enum(">=",">","<=","<","!=","=")
    
class ColQueryAssociation(Base):
    __tablename__ = 'colqueryassociation'
    cquery_id = Column(ForeignKey('cquery.id'),primary_key=True)
    tcolumn_id = Column(ForeignKey('tcolumn.id'),primary_key=True)
    operator = Column(ops)
    value = Column(Float)

    cquery = relationship("CQuery",back_populates="colqassoc")
    column = relationship("TColumn",back_populates="aquery")

    def __repr__(self):
        return "<Condition (<Column_id> = '%s', operator = '%s', value = '%s')>" % (
            self.tcolumn_id, self.operator, self.value)

class CrossTableAssociation(Base):
    __tablename__ = 'crosstableassociation'
    id = Column(Integer, primary_key=True)
    lcolumn_id = Column(Integer, ForeignKey('tcolumn.id'))
    rcolumn_id = Column(Integer, ForeignKey('tcolumn.id'))
    cquery_id = Column(Integer, ForeignKey('cquery.id'))
    operator = Column(ops)

    cquery = relationship("CQuery", back_populates="ccquery")

    def __repr__(self):
        return "<Cross-condition (<Left column_id> = '%s', operator = '%s', Left column_id = '%s')>" % (
            self.lcolumn_id, self.operator, self.rcolumn_id)
    
# class User(Base):
#     __tablename__ = 'users'
#     __table_args__ = {'extend_existing': True}
#     id = Column(Integer, Sequence('user_id_seq'), primary_key=True)
#     name = Column(String(50))
#     fullname = Column(String(50))
#     nickname = Column(String(50))
#     def __repr__(self):
#         return "<User(name='%s', fullname='%s', nickname='%s')>" % (
#             self.name, self.fullname, self.nickname)
