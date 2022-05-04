import astropy.units as u
import pandas as pd
import numpy as np
import math
from astropy.coordinates.sky_coordinate import SkyCoord
from astropy.coordinates import Distance
from astropy.cosmology import Planck13 as cosmo

from datetime import date
# from functions2 import cfFile
# from druvw import uvw
from datasource import datasource


class data2osformat(datasource):
    """A class used to convert data to openspace format.

    Attributes
    ----------
    dftarget : DataFrame
        Dataframe used to store the transformed data
    variables: dictionary
        Dictionary that contains information about the variables to be used to transform the data.
        These variables are collected from the gui.
    
    Methods:
    set_variables(vars)

    transform(format)
        switch to select functions to generate different file formats:
    speck, single and multiple fits

    xyz(self, var):
        switch to select functions to estimate x,y, and z coordiantes using parallax 
        redshift and distance

    xyz_plx()
        estimates x, y and z from ra, dec and parallax

    xyz_shift()
        estimates x, y and z from ra, dec and red shift

    xyz_dist()
        estimates x, y and z from ra, dec and distance

    def create_speck_file():

    """
    def __init__(self):
        super().__init__()
        self.dftarget = pd.DataFrame()
        self.variables = {"speckcols":[]}
        self.dest_filename = ""

    def reset_data(self):
        self.dftarget = pd.DataFrame()
        self.variables = {"speckcols":[]}
        
    def transform(self, format):
        formats = {
            "Speck": self.create_speck_file,
            "Single fits": self.create_sfits_file,
            "Multiple fits": self.create_mfits_files
        }
        # Execute the function
        return formats.get(format)()

    def est_dist(self, var,varname):
        formats = {
            "PARALLAX": self.dist_plx,
            "REDSHIFT": self.dist_shift,
            "DISTANCE": self.dist
        }
        # Execute the function
        return formats.get(var)(varname)

    def dist_plx(self, pvarname):

        print(pvarname)
        # Removing not available parallaxes
        self.data_df.dropna(subset = [pvarname],inplace = True)

        # Removing negative parallaxes
        mask = self.data_df[pvarname] > 0
        self.data_df = self.data_df[mask]
        dist = Distance(parallax = np.array(self.data_df[pvarname]) * u.mas) #,
        self.dftarget["dist"] = np.array(dist)
        pass

    def dist_shift(self, shift_name):
        """
            Estimates distance from red shift values
        """
        print(shift_name)
        l = len(self.data_df.index)
        redshift_corr = self.data_df[shift_name] - 0.005 + (np.random.random_sample(l)*0.01)
        self.dftarget["dist"] = cosmo.comoving_distance(redshift_corr)
        pass

    
    def dist(self, distance):
        self.dftarget["dist"] = self.data_df[distance]
        pass

    def estimate_xyz(self):
        ra = self.variables["RA"]
        dec =self.variables["DEC"]

        xyz = SkyCoord(self.data_df[ra]*u.deg,self.data_df[dec]*u.deg,self.dftarget["dist"])
            
        self.dftarget['x'] = xyz.galactic.cartesian.x.value
        self.dftarget['y'] = xyz.galactic.cartesian.y.value
        self.dftarget['z'] = xyz.galactic.cartesian.z.value
        pass

    def estimate_color(self):
        gmmag = self.variables["G_MEAN_MAG"]
        pmmag = self.variables["BP_MEAN_MAG"]
        tmp_g_bp = self.data_df[gmmag] - self.data_df[pmmag]
        self.dftarget["color"]= self.data_df[self.variables["BP_MEAN_MAG"]] - tmp_g_bp
        self.variables["speckcols"].append("color")
        self.variables["speckcols"].append("lum")
        self.variables["speckcols"].append("gmag")
        self.dftarget["lum"] = 0
        self.dftarget["gmag"] = 0

    def estimate_color_sdss(self):
        psfMag_u = self.variables["G_MEAN_MAG"]
        psfMag_g = self.variables["BP_MEAN_MAG"]
        self.dftarget["color"]= psfMag_u - psfMag_g
        self.variables["speckcols"].append("color")
        self.variables["speckcols"].append("lum")
        self.variables["speckcols"].append("gmag")
        self.dftarget["lum"] = 0
        self.dftarget["gmag"] = 0
        

    def assign_color(self):
        self.dftarget["color"] = self.data_df[self.variables["COLOUR_GAAP_u_g"]]
        self.variables["speckcols"].append("color")
        self.variables["speckcols"].append("lum")
        self.variables["speckcols"].append("gmag")
        self.dftarget["lum"] = 0
        self.dftarget["gmag"] = 0

    def estimate_absmag(self):
        gmmag = self.variables["G_MEAN_MAG"]
        self.dftarget["absmag"] = self.data_df[gmmag] - 5 * np.log10(self.dftarget["dist"]/10)
        self.variables["speckcols"].append("absmag")

        # G_MEAN_MAG as MAG_GAAP_g

    def create_speck_file(self):
        if self.variables:
            print(self.variables)
            self.create_speck_header()
            speckcols = ['x', 'y', 'z']
            speckcols += self.variables["speckcols"]
            print(self.dftarget[speckcols])
            self.dftarget[speckcols].dropna().to_csv(self.dest_filename, mode='a',sep=' ', 
                            header=False, index=False,
                            line_terminator='\r\n')
        pass
    
    def create_speck_header(self):
        print("File name: {}".format(self.dest_filename))
        print('# Data2Dot Project\r\n')
        print('# University of Groningen\r\n#\n')
        for i in range(0,len(self.variables["speckcols"])):
            print("datavar {} {}\r\n".format(i,self.variables["speckcols"][i]))
 
        with open(self.dest_filename, 'w') as speckFile:
            speckFile.write('# Data2Dot Project\r\n')
            speckFile.write('# University of Groningen\r\n#\n')
            for i in range(0,len(self.variables["speckcols"])):
                speckFile.write("datavar {} {}\r\n".format(i,self.variables["speckcols"][i]))
        
    def create_sfits_file(self):
        pass

    def create_mfits_files(self):
        pass
