import pymysql
import mysql.connector
import pandas as pd
from mysql.connector import Error

class Connection():
    def __init__(self, user, password, database, host='localhost', port=3306):
        if not hasattr(self, 'connection'):  # Para evitar reinicializar
            self.user = user
            self.password = password
            self.database = database
            self.host = host
            self.port = port
            self.connection = None
    
    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=self.host,
                user=self.user,
                passwd=self.password,
                db=self.database,
                port=self.port
            )
            print("Connection to MySQL DB successful")
        except Error as e:
            print(f"The error '{e}' occurred")

    def close(self):
        if self.connection:
            self.connection.close()
            print("Connection to MySQL DB closed")
        else:
            print("Connection already closed")
    
    def fetchAllData(self, table):
        cursor = self.connection.cursor()
        query = f"SELECT * FROM {table};"
        cursor.execute(query)
        resultados = cursor.fetchall()

        # Obtén los nombres de las columnas de la consulta
        column_names = [desc[0] for desc in cursor.description]
        cursor.close()
        
        df = pd.DataFrame(resultados, columns=column_names)
        return df
    
    def fetchUniqueData(self, columnId, table):
        cursor = self.connection.cursor()
        query = f"SELECT DISTINCT {columnId} FROM {table};"
        cursor.execute(query)
        ids = [row[0] for row in cursor.fetchall()]
        cursor.close()
        return ids
    
    def tablaDesercion(self):
        cursor = self.connection.cursor()
        query = '''SELECT 
            YEAR(c.fecha_ultima_consulta) AS año,
            (COUNT(DISTINCT CASE WHEN c.activo = 1 THEN c.paciente_id END) / 
            COUNT(DISTINCT c.paciente_id)) * 100 AS tasa_retencion,
            (COUNT(DISTINCT CASE WHEN c.activo = 0 THEN c.paciente_id END) / 
            COUNT(DISTINCT c.paciente_id)) * 100 AS tasa_desercion,
            AVG(CASE WHEN c.activo = 1 THEN c.num_consultas ELSE NULL END) AS promedio_consultas
        FROM 
            cubo_dash_4 c
        GROUP BY 
            YEAR(c.fecha_ultima_consulta)
        ORDER BY 
            año DESC;
        '''
        cursor.execute(query)
        resultados = cursor.fetchall()
        # Obtén los nombres de las columnas de la consulta
        column_names = [desc[0] for desc in cursor.description]
        cursor.close()
        
        df = pd.DataFrame(resultados, columns=column_names)
        df = df.drop(columns=['promedio_consultas'])
        return df



