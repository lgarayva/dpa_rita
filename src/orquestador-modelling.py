# PYTHONPATH='.' AWS_PROFILE=dpa luigi --module orquestador RunTables --local-scheduler --filename metada_extract.sql --update-id 4

import luigi
import luigi.contrib.s3
from luigi import Event, Task, build # Utilidades para acciones tras un task exitoso o fallido
import os

from pyspark.sql import SparkSession
from src.models.train_model import get_processed_train_test, init_data_luigi

from luigi.contrib.postgres import CopyToTable,PostgresQuery



# ===============================
CURRENT_DIR = os.getcwd()
# ===============================

class DataLocalStorage(): 
    def __init__(self, X_train, X_test, y_train, y_test):
        self.X_train = None
        self.X_test = None
        self.y_test = None
        self.y_train = None
    
CACHE = DataLocalStorage()
    
    
class GetDataSets(luigi.Task):

    def output(self):
        dir = CURRENT_DIR + "/target/gets_data_sets.txt"
        return luigi.local_target.LocalTarget(dir)

    def run(self):
        X_train, X_test, y_train, y_test = init_data_luigi()
        CACHE.X_train = X_train
        CACHE.X_test = X_test
        CACHE.y_train = y_train
        CACHE.y_test = y_test
        
        z = str(self.bucname)
        with self.output().open('w') as output_file:
            output_file.write(z)

# Create RDS.
class CreateRDS(luigi.Task):
    rdsname = luigi.Parameter()

    def output(self):
        dir = CURRENT_DIR + "/target/create_rds_" + str(this.rdsname) + ".txt"
        return luigi.local_target.LocalTarget(dir)

    def run(self):
        create_db(str(this.rdsname))
        z = str(self.rdsname)
        with self.output().open('w') as output_file:
            output_file.write(z)

# Create tables and squemas
# "metada_extract.sql"
class CreateTables(PostgresQuery):
    filename = luigi.Parameter()
    update_id = luigi.Parameter()

    user = MY_USER
    password = MY_PASS
    database = MY_DB
    host = MY_HOST
    table = "metadatos"

    file_dir = "./utils/sql/metada_extract.sql"
    query = open(file_dir, "r").read()



class RunTables(luigi.Task):
    filename = luigi.Parameter()
    update_id = luigi.Parameter()

    def requires(self):
        return CreateTables(self.filename, self.update_id)

    def run(self):
        z = str(self.filename) + " " + str(self.update_id)

        with self.output().open('w') as output_file:
            output_file.write(z)

    def output(self):
        dir = CURRENT_DIR + "/target/create_tables.txt"
        return luigi.local_target.LocalTarget(dir)



# Create EC2
class CreateEC2(luigi.Task):
    def output(self):
        dir = CURRENT_DIR + "/target/create_ec2.txt"
        return luigi.local_target.LocalTarget(dir)

    def run(self):
        resp = create_ec2()

        with self.output().open('w') as output_file:
            output_file.write(resp)
