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
import marbles.core

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

#Metadata Clean Testing
from src.utils.metadatos_utils import C_testing_clean_columns,C_testing_clean_rangos
from src.utils.metadatos_utils import Linaje_clean_columns_testing, Linaje_clean_rangos_testing

#Pruebas unitarias Clean
from src.orquestadores.tasks.testing.test_clean_columns import Test_Columns_Case
from src.orquestadores.tasks.testing.test_clean_rangos import Test_Ranges_Case

#Metadata Semantic Testing
from src.utils.metadatos_utils import Linaje_extract_testing, EL_testing_extract
from src.utils.metadatos_utils import Linaje_load_testing, EL_testing_load
from src.utils.metadatos_utils import Linaje_semantic1_testing, Linaje_semantic2_testing, FE_testing_semantic

#Pruebas unitarias Semantic
from src.orquestadores.tasks.testing.test_semantic_columns import TestSemanticColumns
from src.orquestadores.tasks.testing.test_semantic_column_types import TestSemanticColumnsTypes


# Dependencias de Tasks previos =======
from src.orquestadores.tasks.extract import Extraction
from src.orquestadores.tasks.load_test import Load_Testing
from src.orquestadores.tasks.load import Load
from src.orquestadores.tasks.clean_column_testing import CleanColumn_Testing
from src.orquestadores.tasks.clean_rango_testing import CleanRango_Testing
from src.orquestadores.tasks.clean import GetCleanData
from src.orquestadores.tasks.semantic_column_testing import Semantic_Testing_col
from src.orquestadores.tasks.semantic_type_testing import Semantic_Testing


#-----------------------------------------------------------------------------------------------------------------------------
#FEATURE ENGINERING------------------------------------------------------------------------------------------------------------
# Crear caracteristicas DATOS
CURRENT_DIR = os.getcwd()


#metadata FE
MiLinajeSemantic = Linaje_semantic()

#Creamos features nuevas
class GetFEData(luigi.Task):

	def requires(self):
		return Semantic_Testing()

	def output(self):
		dir = "./target/data_semantic.txt"
		return luigi.local_target.LocalTarget(dir)

	def run(self):
		df_util = crear_features()#CACHE.get_clean_data()
		meta_semantic = [] # arreglo para reunir tuplas de metadatos

		MiLinajeSemantic.ip_ec2 = str(df_util.count())
		MiLinajeSemantic.fecha =  str(datetime.now())
		MiLinajeSemantic.nombre_task = 'GetFEData'
		MiLinajeSemantic.usuario = str(getpass.getuser())
		MiLinajeSemantic.year = str(datetime.today().year)
		MiLinajeSemantic.month = str(datetime.today().month)
		MiLinajeSemantic.ip_ec2 =  str(socket.gethostbyname(socket.gethostname()))
		MiLinajeSemantic.variables = "findesemana,quincena,dephour,seishoras"
		MiLinajeSemantic.ruta_s3 = "s3://test-aws-boto/semantic"
		MiLinajeSemantic.task_status = 'Successful'
		# Insertamos metadatos a DB
		print(MiLinajeSemantic.to_upsert())
		#semantic_metadata(MiLinajeSemantic.to_upsert())
		meta_semantic.append(MiLinajeSemantic.to_upsert())
		# Escritura de csv para carga de metadatos
		df = pd.DataFrame(meta_semantic, columns=["num_filas_modificadas",\
		"fecha","nombre_task","usuario","year","month","ip_ec2",\
		"variables","ruta_s3","task_status"])
		df.to_csv("metadata/semantic_metadata.csv",index=False,header=False)

		## Inserta archivo y elimina csv
		#os.system('bash ./src/utils/inserta_semantic_rita_to_rds.sh')
		#os.system('rm semantic.csv')

		z = "CreaFeaturesDatos"
		with self.output().open('w') as output_file:
			output_file.write(z)
