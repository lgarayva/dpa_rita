# PYTHONPATH='.' AWS_PROFILE=educate1 luigi --module alter_orq downloadDataS3 --local-scheduler

# PARA UN MODELO
#PYTHONPATH='.' AWS_PROFILE=dpa luigi --module alter_orq  RunModel --local-scheduler  --bucname models-dpa --numIt 2 --numPCA 3  --model LR --obj 0-1.5

# PARA TODOS LOS MODELOS
# PYTHONPATH='.' AWS_PROFILE=dpa luigi --module alter_orq  RunAllTargets --local-scheduler  --bucname models-dpa --numIt 1 --numPCA 2  --model LR

# CENTRAL scheduler
#PYTHONPATH='.' AWS_PROFILE=dpa luigi --module alter_orq  RunAllTargets  --bucname models-dpa --numIt 1 --numPCA 2  --model LR

###  Librerias necesarias
import luigi
import luigi.contrib.s3
from luigi import Event, Task, build # Utilidades para acciones tras un task exitoso o fallido
from luigi.contrib.postgres import CopyToTable,PostgresQuery
import boto3
from datetime import date, datetime
import getpass # Usada para obtener el usuario
from io import BytesIO
import socket #import publicip
import requests
import os, subprocess, ast
import pandas as pd
import psycopg2
from psycopg2 import extras
from zipfile import ZipFile
from pathlib import Path
###librerias para clean
from pyspark.sql import SparkSession
from src.features.build_features import clean, crear_features

###  Imports desde directorio de proyecto dpa_rita
## Credenciales
from src import(
MY_USER,
MY_PASS,
MY_HOST,
MY_PORT,
MY_DB,
)

## Utilidades
from src.utils.s3_utils import create_bucket
from src.utils.db_utils import create_db, execute_sql, save_rds
from src.utils.ec2_utils import create_ec2
from src.utils.metadatos_utils import EL_verif_query, EL_metadata, Linaje_raw,EL_load,clean_metadata_rds,Linaje_clean_data, Linaje_semantic, semantic_metadata, Insert_to_RDS, rita_light_query,Linaje_load,load_verif_query
from src.utils.db_utils import execute_sql
#from src.models.train_model import run_model
from src.models.save_model import parse_filename
from src.utils.metadatos_utils import Linaje_extract_testing, EL_testing_extract
from src.utils.metadatos_utils import Linaje_load_testing, EL_testing_load
from src.utils.metadatos_utils import Linaje_semantic1_testing, Linaje_semantic2_testing, FE_testing_semantic

from tasks.extract import Extraction
from tasks.load_test import Load_Testing
# ======================================================
# Etapa Load
# ======================================================

MiLinaje = Linaje_load()

class Load(luigi.Task):
    '''
    Carga hacia RDS los datos de la carpeta data
    '''
    def requires(self):
        return Load_Testing()

    # Recolectamos fecha y usuario para metadatos a partir de fecha actual
    MiLinaje.fecha =  datetime.now()
    MiLinaje.usuario = getpass.getuser()

    def run(self):
        # Ip metadatos
        MiLinaje.ip_ec2 = str(socket.gethostbyname(socket.gethostname()))

        #Subimos de archivos csv
        extension_csv = ".csv"
        dir_name="./src/data/"

        for item in os.listdir(dir_name):
            if item.endswith(extension_csv):
                table_name = "raw.rita"

                MiLinaje.nombre_archivo = item

                # Numero de columnas y renglones para metadatos
                df = pd.read_csv(dir_name + item, low_memory=False)
                MiLinaje.num_columnas = df.shape[1]
                MiLinaje.num_renglones = df.shape[0]

                MiLinaje.tamano_csv = Path(dir_name+item).stat().st_size

                try:
                    print(item)
                    save_rds(dir_name+item, table_name)
                    os.remove(dir_name+item)

                    EL_load(MiLinaje.to_upsert())
                    #cantidad_csv_insertados=cantidad_csv_insertados+1
                except:
                    print("Carga de "+item)

        #Cantidad de renglones en metadatos.load
        # tam1 = load_verif_query()

        os.system('echo "ok" >target/load_ok.txt')

    def output(self):
        # Ruta en donde se guarda el target del task
        output_path = "target/load_ok.txt"
        return luigi.LocalTarget(output_path)

#-----------------------------------------------------------------------------------------------------------------------------