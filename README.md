# DomeCat
## A Tool to Explore Astronomical Databases and Transform Data into Planetarium Formats

The Virtual Observatory provides a valuable source for presentations
in digital planetaria. However, importing data into planetaria can be
a time-consuming process because the data must be selected, downloaded
and transformed into a format used in digital planetaria. The later
step is typically done by means of ad-hoc scripts. DomeCat is
user-friendly tool that can perform such steps in a single graphical
user interface (GUI). Additionally, includes a database to keep track
of the transformed data and runtime of the procesess.

## Installation

### Compile under Linux and OSX

1. Install `Python 3.9` and `venv` 
2. Clone this repository.
```
git clone https://github.com/Venustiano/DomeCat.git
``` 
3. Run

```
source ./data2dot_env.sh
```  

This script will create and activate a virtual environment
`env`, install the required packages and run `DomeCat.py`

4. If everything went fine, you'll see the GUI.

5. When you are done close the app. Your current directory will be `(env)..:~/../data2dot/qtgui$`.  

6. Deactivate the environment.
```
deactivate
```
### Compile under Windows

### Binary file

- Linux (Ubuntu)
- Windows
- OSX

## Usage

## Credits

## License


[GNU](LICENSE)
<!-- DomeCat has been developed for two main purposes. First, to provide a -->
<!-- user friendly interface to explore and download data from different -->
<!-- astronomical catalogues. Second, to transform data into planetarium -->
<!-- formats. Currently, GAIA, SDSS and ESO catalogues are -->
<!-- supported. Because of the download limitations of the anonymous user, -->
<!-- authentication credentials are requested for SDSS and -->
<!-- GAIA. Appropriate links to sign up are provided when authentication is -->
<!-- required. -->



<!-- Given the appropriate columns or variables -->
<!-- such as `ra`, `dec`, and `parallax` or `redshift`, these data can be -->
<!-- used to generate file formats such as `speck`, `fits` and -->
<!-- `octrees`. Such file formats can be used for visual exploration of the -->
<!-- data using [OpenSpace](https://www.openspaceproject.com/). This tool -->
<!-- has the following features -->


## Acknowledgements

The development of DomeCat was undertaken as part of the Target Field
Lab, with financial contributions from Samenwerkingsverband Noord
Nederland (SNN), the European Regional Development Fund (ERDF), and
the Dutch Ministry of Economic Affairs and Climate Policy (EZK).


