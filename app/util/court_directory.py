"""
court_directory.py - Download and cache a court directory for Texas

Copyright (c) 2020 by Thomas J. Daley, J.D. All Rights Reserved.
"""
import csv
import json
import requests
from datetime import date, time

URL = 'https://card.txcourts.gov/ExcelExportPublic.aspx?type=P&export=E&SortBy=tblCounty.Sort_ID,%20tblCourt.Court_Identifier&Active_Flg=true&Court_Type_CD=0&Court_Sub_Type_CD=0&County_ID=0&City_CD=0&Court=&DistrictPrimaryLocOnly=1&AdminJudicialRegion=0&COADistrictId=0'  # noqa
URL = 'https://card.txcourts.gov/ExcelExportPublic.aspx?type=P&export=E&CommitteeID=0&Court=&SortBy=tblCounty.Sort_ID,%20Last_Name&Active_Flg=true&Last_Name=&First_Name=&Court_Type_CD=0&Court_Sub_Type_CD=0&County_ID=0&City_CD=0&Address_Type_CD=0&Annual_Report_CD=0&PersonnelType1=&PersonnelType2=&DistrictPrimaryLocOnly=0&AdminJudicialRegion=0&COADistrictId=0'  # noqa

DIRECTORY_FILE = 'util/data/directory.json'
CACHE_FILE = 'util/data/court_directory_cache.tsv'


class Entry(object):
    def __init__(self, fields: list) -> dict:
        try:
            self.court_type = fields[0]
            self.court = fields[1]
            self.county = fields[2]
            self.prefix = fields[3]
            self.first_name = fields[4]
            self.middle_name = fields[5]
            self.last_name = fields[6]
            self.suffix = fields[7]
            self.title = fields[8]
            self.address = fields[9]
            self.city = fields[10]
            self.state = "TX"
            self.postal_code = fields[11]
            self.telephone = fields[12]
            self.email = fields[13]
        except IndexError:
            pass


class CourtDirectory(object):
    directory = None

    def __init__(self):
        """
        Load the cached court directory.
        """
        if not CourtDirectory.directory:
            with open(DIRECTORY_FILE, 'r') as fp:
                CourtDirectory.directory = json.load(fp)

    def get_counties(self) -> list:
        """
        Get a list of counties
        """
        return list(CourtDirectory.directory.keys())

    def get_county_tuples(self) -> list:
        """
        Get a list of counties
        """
        counties = self.get_counties()
        return [(c, c) for c in counties]

    def get_court_types(self, county: str) -> list:
        """
        Get a list of types of courts for the given county.
        """
        return list(CourtDirectory.directory.get(county, {}).keys())

    def get_court_type_tuples(self, county: str) -> list:
        """
        Get a list of court types as a list of tuples.
        """
        court_types = self.get_court_types(county)
        return [(c, c) for c in court_types]

    def get_courts(self, county: str, court_type: str) -> list:
        """
        Get a list of courts of the given type for the given county.
        """
        try:
            return list(CourtDirectory.directory[county][court_type].keys())
        except KeyError:
            pass
        return list()

    def get_court_tuples(self, county: str, court_type: str) -> list:
        """
        Get a list of courts as a list of tuples.
        """
        courts = self.get_courts(county, court_type)
        return [(c, c) for c in courts]

    def get_court_personnel(self, county: str, court_type: str, court: str) -> list:
        """
        Get a list of people who work in the given court.
        """
        try:
            return list(CourtDirectory.directory[county][court_type][court])
        except KeyError:
            pass
        return list()

    @staticmethod
    def process():
        """
        This method will download a refreshed personnel list and update the
        cache files.
        """
        CourtDirectory.retrieve()
        directory = CourtDirectory.parse()
        CourtDirectory.save(directory)

    @staticmethod
    def retrieve():
        """
        Retrieve court directory and save it to a set of cached files.
        """
        result = requests.get(URL)
        with open(CACHE_FILE, 'w') as fp:
            for chunk in result.iter_content(chunk_size=1024):
                fp.write(chunk.decode())

    @staticmethod
    def parse():
        counties = {}

        with open(CACHE_FILE, newline='') as tsvfile:
            reader = csv.reader(tsvfile, delimiter='\t', quotechar='"')
            for row in reader:
                # Skip blank rows
                if not row:
                    continue

                # Create object with named fields
                entry = Entry(row)
                if not entry.county or not entry.court or len(entry.court.strip()) == 0:
                    continue

                # Update list of counties if we have not seen this one before
                if entry.county and entry.county not in counties:
                    counties[entry.county] = {}

                # Add to the court types for this county
                if entry.court_type not in counties[entry.county]:
                    counties[entry.county][entry.court_type] = {}

                # Add to the courts of this type for this county
                if entry.court not in counties[entry.county][entry.court_type]:
                    counties[entry.county][entry.court_type][entry.court] = []

                # Add to to this court's personnel
                counties[entry.county][entry.court_type][entry.court].append(entry)

        return counties

    @staticmethod
    def save(directory: dict):
        with open(DIRECTORY_FILE, 'w') as fp:
            json.dump(directory, fp, indent=4, default=serialize, sort_keys=True)


def serialize(obj):
    if isinstance(obj, date):
        serial = obj.isoformat()
        return serial

    if isinstance(obj, time):
        serial = obj.isoformat()
        return serial

    return obj.__dict__


if __name__ == '__main__':
    print("Processing . . .", end='')
    CourtDirectory.process()
    print("Done")
    mydir = CourtDirectory()
    print("COUNTIES".center(80, "="))
    print(mydir.get_counties())
    print("COURT TYPES".center(80, "="))
    print(mydir.get_court_types('Collin'))
    print("COURTS".center(80, "="))
    print(mydir.get_courts('Collin', 'District'))
    print("PERSONNEL".center(80, "="))
    print(json.dumps(mydir.get_court_personnel('Collin', 'District', '416th District Court'), indent=4))
