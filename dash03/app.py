from flask import Flask, request, jsonify, render_template
import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv
import logging
import pathlib
from datetime import datetime
from flask_cors import CORS
import decimal

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Ruta relativa al archivo .env desde app.py
current_dir = pathlib.Path(__file__).parent  # Esto apunta a 'dash3'
env_path = current_dir / 'config' / 'credenciales.env'
print("*****************************")
print(env_path)
# Cargar variables de entorno
load_dotenv(env_path)

app = Flask(__name__)
CORS(app) 

# Configuración de la base de datos 
DB_CONFIG = {
    'host': os.getenv('DB_HOST', 'localhost'),
    'database': os.getenv('DB_NAME', 'alimentacion_db'),
    'user': os.getenv('DB_USER', 'root'),
    'password': os.getenv('DB_PASSWORD', ''),
    'port': int(os.getenv('DB_PORT', '3306'))
}

@app.route('/')
def dashboard():
    return render_template('Balanced_Scorecard.html')

def conexionBD():
    try:
        logger.debug("Intentando conectar a la base de datos...")
        connection = mysql.connector.connect(**DB_CONFIG)
        logger.debug("Conexión exitosa a la base de datos")
        return connection
    except Error as e:
        logger.error(f"Error al conectar a MySQL: {e}")
        return None

@app.route('/api/crecimiento', methods=['GET'])
def obtener_crecimiento():
   try:
       connection = conexionBD()
       if not connection:
           return jsonify({'error': 'Error de conexión a la base de datos'}), 500

       cursor = connection.cursor(dictionary=True)
       
       query = """
       WITH PrimeraConsulta AS (
           SELECT 
               id_paciente,
               MIN(fecha) as primera_fecha
           FROM dim_consulta 
           GROUP BY id_paciente
       ),
       PacientesPorMes AS (
           SELECT 
               DATE_FORMAT(dc.fecha, '%Y-%m') as mes,
               COUNT(DISTINCT dc.id_paciente) as total_pacientes,
               COUNT(DISTINCT CASE 
                   WHEN DATE_FORMAT(dc.fecha, '%Y-%m') = DATE_FORMAT(pc.primera_fecha, '%Y-%m')
                   THEN dc.id_paciente 
               END) as pacientes_nuevos
           FROM dim_consulta dc
           JOIN PrimeraConsulta pc ON dc.id_paciente = pc.id_paciente
           GROUP BY DATE_FORMAT(dc.fecha, '%Y-%m')
       )
       SELECT 
           mes,
           total_pacientes,
           pacientes_nuevos,
           ROUND(((total_pacientes - LAG(total_pacientes) OVER (ORDER BY mes)) / 
               NULLIF(LAG(total_pacientes) OVER (ORDER BY mes), 0)) * 100, 2) as porcentaje_crecimiento,
           CASE 
               WHEN ((total_pacientes - LAG(total_pacientes) OVER (ORDER BY mes)) / 
                   NULLIF(LAG(total_pacientes) OVER (ORDER BY mes), 0)) * 100 >= 10 
               THEN 'Meta Alcanzada'
               ELSE 'Meta No Alcanzada'
           END as estado_meta
       FROM PacientesPorMes
       ORDER BY mes;
       """
       
       cursor.execute(query)
       resultados = cursor.fetchall()
       
       datos_formateados = []
       for row in resultados:
           datos_formateados.append({
               'mes': row['mes'],
               'totalPacientes': row['total_pacientes'],
               'pacientesNuevos': row['pacientes_nuevos'],
               'porcentajeCrecimiento': float(row['porcentaje_crecimiento']) if row['porcentaje_crecimiento'] else 0,
               'meta': 10.0,
               'estadoMeta': row['estado_meta']
           })

       cursor.close()
       connection.close()
       
       return jsonify({
           'success': True,
           'data': datos_formateados
       })

   except Error as e:
       logger.error(f"Error en la consulta: {str(e)}")
       return jsonify({'error': str(e)}), 500

@app.route('/api/retencion-mensual', methods=['GET'])
def obtener_retencion_mensual():
    try:
        connection = conexionBD()
        if not connection:
            return jsonify({'error': 'Error de conexión a la base de datos'}), 500

        cursor = connection.cursor(dictionary=True)
        
        query = """
        WITH ConsultasPacientes AS (
            SELECT 
                id_paciente,
                DATE_FORMAT(fecha, '%Y-%m') as mes,
                COUNT(*) as consultas_mes
            FROM dim_consulta
            GROUP BY id_paciente, DATE_FORMAT(fecha, '%Y-%m')
        ),
        RetencionMensual AS (
            SELECT 
                mes,
                COUNT(DISTINCT id_paciente) as pacientes_activos,
                LAG(COUNT(DISTINCT id_paciente)) OVER (ORDER BY mes) as pacientes_mes_anterior,
                COUNT(DISTINCT CASE WHEN consultas_mes > 0 THEN id_paciente END) as pacientes_retenidos
            FROM ConsultasPacientes
            GROUP BY mes
        )
        SELECT 
            mes,
            pacientes_activos,
            pacientes_retenidos,
            ROUND((pacientes_retenidos / NULLIF(pacientes_mes_anterior, 0)) * 100, 2) as tasa_retencion,
            CASE 
                WHEN (pacientes_retenidos / NULLIF(pacientes_mes_anterior, 0)) * 100 >= 95 THEN 'Meta Alcanzada'
                ELSE 'Meta No Alcanzada'
            END as estado_meta
        FROM RetencionMensual
        WHERE mes IS NOT NULL
        ORDER BY mes;
        """
        
        cursor.execute(query)
        resultados = cursor.fetchall()
        
        # Procesar los resultados para el formato deseado
        datos_formateados = []
        for row in resultados:
            datos_formateados.append({
                'mes': row['mes'],
                'tasa_retencion': float(row['tasa_retencion']) if row['tasa_retencion'] else 0,
                'meta': 95.0,  # Meta fija del 95%
                'estado_meta': row['estado_meta'],
                'pacientes_activos': row['pacientes_activos'],
                'pacientes_retenidos': row['pacientes_retenidos']
            })

        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True,
            'data': datos_formateados
        })

    except Error as e:
        logger.error(f"Error en la consulta: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/alertas-abandono', methods=['GET'])
@app.route('/api/alertas-abandono/<tipo>', methods=['GET'])
def obtener_alertas_abandono(tipo='general'):
    try:
        connection = conexionBD()
        if not connection:
            return jsonify({'error': 'Error de conexión a la base de datos'}), 500

        cursor = connection.cursor(dictionary=True)
        
        if tipo == 'satisfaccion':
            query = """
            WITH PacientesAltoRiesgo AS (
                SELECT 
                    c.id_paciente,
                    c.satisfaccion,
                    c.fecha
                FROM dim_consulta c
                WHERE c.id_paciente IN (
                    SELECT p.id
                    FROM pacientes p
                    JOIN dim_consulta c ON p.id = c.id_paciente
                    GROUP BY p.id
                    HAVING DATEDIFF(CURRENT_DATE, MAX(c.fecha)) > 30
                )
            )
            SELECT 
                DATE_FORMAT(fecha, '%Y-%m') as mes,
                ROUND(AVG(satisfaccion), 2) as promedio_satisfaccion
            FROM PacientesAltoRiesgo
            WHERE fecha BETWEEN '2023-06-01' AND '2024-10-31'
            GROUP BY DATE_FORMAT(fecha, '%Y-%m')
            ORDER BY mes DESC;
            """
            
            cursor.execute(query)
            resultados = cursor.fetchall()
            
            datos_formateados = [{
                'mes': row['mes'],
                'promedio_satisfaccion': float(row['promedio_satisfaccion']) if row['promedio_satisfaccion'] else 0
            } for row in resultados]
            
        else:  # tipo == 'general'
            query = """
            SELECT 
                MAX(c.fecha) as ultima_consulta,
                DATEDIFF(CURRENT_DATE, MAX(c.fecha)) as dias_sin_consulta,
                COUNT(c.id_consulta) as total_consultas,
                ROUND(((c.peso_logrado - c.peso_actual) / c.peso_actual) * 100, 2) as porcentaje_progreso,
                'Alto Riesgo' as nivel_riesgo_abandono
            FROM pacientes p
            JOIN dim_consulta c ON p.id = c.id_paciente
            GROUP BY p.id
            HAVING dias_sin_consulta > 30
            ORDER BY dias_sin_consulta DESC;
            """
            
            cursor.execute(query)
            resultados = cursor.fetchall()
            
            datos_formateados = []
            for row in resultados:
                row_dict = dict(row)
                if row_dict['ultima_consulta']:
                    row_dict['ultima_consulta'] = row_dict['ultima_consulta'].strftime('%Y-%m-%d')
                datos_formateados.append(row_dict)

        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True,
            'data': datos_formateados,
            'tipo': tipo
        })

    except Error as e:
        logger.error(f"Error en la consulta: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/efectividad-descuentos', methods=['GET'])
def obtener_efectividad_descuentos():
   try:
       connection = conexionBD()
       if not connection:
           return jsonify({'error': 'Error de conexión a la base de datos'}), 500

       cursor = connection.cursor(dictionary=True)
       
       query = """
       WITH ConsultasDescuento AS (
           SELECT 
               dc1.id_paciente,
               dc1.fecha as fecha_descuento,
               dc1.descuento,
               dc1.precio,
               dc1.precio_final,
               MIN(dc2.fecha) as siguiente_consulta
           FROM dim_consulta dc1
           LEFT JOIN dim_consulta dc2 ON 
               dc1.id_paciente = dc2.id_paciente AND
               dc2.fecha > dc1.fecha AND
               DATEDIFF(dc2.fecha, dc1.fecha) <= 90
           WHERE dc1.descuento > 0
           GROUP BY 
               dc1.id_paciente,
               dc1.fecha,
               dc1.descuento,
               dc1.precio,
               dc1.precio_final
       ),
       AnalisisRetencion AS (
           SELECT 
               DATE_FORMAT(fecha_descuento, '%Y-%m') as mes,
               COUNT(DISTINCT id_paciente) as pacientes_con_descuento,
               ROUND(AVG(descuento), 2) as descuento_promedio,
               ROUND(AVG(precio), 2) as precio_promedio_original,
               ROUND(AVG(precio_final), 2) as precio_promedio_final,
               COUNT(DISTINCT CASE 
                   WHEN siguiente_consulta IS NOT NULL 
                   THEN id_paciente 
               END) as pacientes_retenidos
           FROM ConsultasDescuento
           GROUP BY DATE_FORMAT(fecha_descuento, '%Y-%m')
       )
       SELECT 
           mes,
           pacientes_con_descuento,
           pacientes_retenidos,
           ROUND((pacientes_retenidos * 100.0 / pacientes_con_descuento), 2) as porcentaje_retencion,
           descuento_promedio,
           precio_promedio_original,
           precio_promedio_final,
           ROUND((precio_promedio_original - precio_promedio_final), 2) as ahorro_promedio,
           CASE 
               WHEN (pacientes_retenidos * 100.0 / pacientes_con_descuento) >= 80 THEN 'Alta'
               WHEN (pacientes_retenidos * 100.0 / pacientes_con_descuento) >= 50 THEN 'Media'
               ELSE 'Baja'
           END as efectividad_descuento
       FROM AnalisisRetencion
       ORDER BY mes;
       """
       
       cursor.execute(query)
       resultados = cursor.fetchall()
       
       # Procesar los resultados para asegurar tipos de datos correctos
       datos_formateados = []
       for row in resultados:
           datos_formateados.append({
               'mes': row['mes'],
               'pacientesConDescuento': row['pacientes_con_descuento'],
               'pacientesRetenidos': row['pacientes_retenidos'],
               'porcentajeRetencion': float(row['porcentaje_retencion']) if row['porcentaje_retencion'] else 0,
               'descuentoPromedio': float(row['descuento_promedio']) if row['descuento_promedio'] else 0,
               'precioPromedioOriginal': float(row['precio_promedio_original']) if row['precio_promedio_original'] else 0,
               'precioPromedioFinal': float(row['precio_promedio_final']) if row['precio_promedio_final'] else 0,
               'ahorroPromedio': float(row['ahorro_promedio']) if row['ahorro_promedio'] else 0,
               'efectividadDescuento': row['efectividad_descuento']
           })

       cursor.close()
       connection.close()
       
       return jsonify({
           'success': True,
           'data': datos_formateados
       })

   except Error as e:
       logger.error(f"Error en la consulta: {str(e)}")
       return jsonify({'error': str(e)}), 500
    
@app.route('/api/tendencia-ingresos', methods=['GET'])
def obtener_tendencia_ingresos():
    try:
        connection = conexionBD()
        if not connection:
            return jsonify({'error': 'Error de conexión a la base de datos'}), 500

        cursor = connection.cursor(dictionary=True)
        
        query = """
        WITH IngresosMensuales AS (
            SELECT 
                DATE_FORMAT(fecha, '%Y-%m') as mes,
                COUNT(DISTINCT id_paciente) as total_pacientes,
                COUNT(id_consulta) as total_consultas,
                SUM(precio) as ingreso_bruto,
                SUM(descuento) as total_descuentos,
                SUM(precio_final) as ingreso_neto,
                ROUND(AVG(precio_final), 2) as precio_promedio_consulta
            FROM dim_consulta
            GROUP BY DATE_FORMAT(fecha, '%Y-%m')
        ),
        AnalisisTendencia AS (
            SELECT 
                mes,
                total_pacientes,
                total_consultas,
                ingreso_bruto,
                total_descuentos,
                ingreso_neto,
                precio_promedio_consulta,
                LAG(ingreso_neto) OVER (ORDER BY mes) as ingreso_mes_anterior,
                ROUND(((ingreso_neto - LAG(ingreso_neto) OVER (ORDER BY mes)) / 
                    NULLIF(LAG(ingreso_neto) OVER (ORDER BY mes), 0)) * 100, 2) as variacion_porcentual
            FROM IngresosMensuales
        )
        SELECT 
            mes,
            total_pacientes,
            total_consultas,
            ROUND(total_consultas * 1.0 / total_pacientes, 2) as consultas_por_paciente,
            ingreso_bruto,
            total_descuentos,
            ingreso_neto,
            precio_promedio_consulta,
            variacion_porcentual,
            CASE 
                WHEN variacion_porcentual > 0 THEN 'Crecimiento'
                WHEN variacion_porcentual < 0 THEN 'Decrecimiento'
                ELSE 'Estable'
            END as tendencia,
            CASE 
                WHEN variacion_porcentual >= 10 THEN 'Meta Alcanzada'
                ELSE 'Meta No Alcanzada'
            END as estado_meta_crecimiento
        FROM AnalisisTendencia
        ORDER BY mes;
        """
        
        cursor.execute(query)
        resultados = cursor.fetchall()
        
        # Procesar los resultados para asegurar tipos de datos correctos
        datos_formateados = []
        for row in resultados:
            datos_formateados.append({
                'mes': row['mes'],
                'total_pacientes': row['total_pacientes'],
                'total_consultas': row['total_consultas'],
                'consultas_por_paciente': float(row['consultas_por_paciente']) if row['consultas_por_paciente'] else 0,
                'ingreso_bruto': float(row['ingreso_bruto']) if row['ingreso_bruto'] else 0,
                'total_descuentos': float(row['total_descuentos']) if row['total_descuentos'] else 0,
                'ingreso_neto': float(row['ingreso_neto']) if row['ingreso_neto'] else 0,
                'precio_promedio_consulta': float(row['precio_promedio_consulta']) if row['precio_promedio_consulta'] else 0,
                'variacion_porcentual': float(row['variacion_porcentual']) if row['variacion_porcentual'] else 0,
                'tendencia': row['tendencia'],
                'estado_meta_crecimiento': row['estado_meta_crecimiento']
            })

        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True,
            'data': datos_formateados
        })

    except Error as e:
        logger.error(f"Error en la consulta: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/satisfaccion-general', methods=['GET'])
def obtener_satisfaccion_general():
    try:
        connection = conexionBD()
        if not connection:
            return jsonify({'error': 'Error de conexión a la base de datos'}), 500

        cursor = connection.cursor(dictionary=True)
        
        query = """
        WITH SatisfaccionGeneral AS (
            SELECT 
                DATE_FORMAT(fecha, '%Y-%m') as mes,
                COUNT(id_consulta) as total_consultas,
                ROUND(AVG(satisfaccion), 2) as satisfaccion_promedio,
                COUNT(CASE WHEN satisfaccion >= 8 THEN 1 END) as consultas_satisfactorias,
                COUNT(CASE WHEN satisfaccion < 6 THEN 1 END) as consultas_insatisfactorias
            FROM dim_consulta
            GROUP BY DATE_FORMAT(fecha, '%Y-%m')
        )
        SELECT 
            mes,
            total_consultas,
            satisfaccion_promedio,
            ROUND((consultas_satisfactorias * 100.0 / total_consultas), 2) as porcentaje_satisfaccion,
            ROUND((consultas_insatisfactorias * 100.0 / total_consultas), 2) as porcentaje_insatisfaccion
        FROM SatisfaccionGeneral
        ORDER BY mes;
        """
        
        cursor.execute(query)
        resultados = cursor.fetchall()
        
        # Procesar los resultados para asegurar tipos de datos correctos
        datos_formateados = []
        for row in resultados:
            datos_formateados.append({
                'mes': row['mes'],
                'total_consultas': row['total_consultas'],
                'satisfaccion_promedio': float(row['satisfaccion_promedio']) if row['satisfaccion_promedio'] else 0,
                'porcentaje_satisfaccion': float(row['porcentaje_satisfaccion']) if row['porcentaje_satisfaccion'] else 0,
                'porcentaje_insatisfaccion': float(row['porcentaje_insatisfaccion']) if row['porcentaje_insatisfaccion'] else 0
            })

        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True,
            'data': datos_formateados
        })

    except Error as e:
        logger.error(f"Error en la consulta: {str(e)}")
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/exito-por-plan', methods=['GET'])
def obtener_exito_por_plan():
    try:
        connection = conexionBD()
        if not connection:
            return jsonify({'error': 'Error de conexión a la base de datos'}), 500

        cursor = connection.cursor(dictionary=True)
        
        query = """
        WITH ExitoPorPlan AS (
            SELECT 
                dp.id_plan,
                dp.información as tipo_plan,
                c.id_paciente,
                MIN(c.peso_actual) as peso_minimo,
                MAX(c.peso_actual) as peso_inicial,
                c.objetivo_peso,
                AVG(c.satisfaccion) as satisfaccion_promedio,
                COUNT(c.id_consulta) as total_consultas,
                CASE 
                    WHEN MIN(c.peso_actual) <= c.objetivo_peso THEN 1
                    ELSE 0
                END as objetivo_alcanzado
            FROM dim_consulta c
            JOIN dim_plan dp ON c.id_plan = dp.id_plan
            GROUP BY dp.id_plan, dp.información, c.id_paciente, c.objetivo_peso
        )
        SELECT 
            tipo_plan,
            COUNT(DISTINCT id_paciente) as total_pacientes,
            ROUND(AVG(objetivo_alcanzado) * 100, 2) as tasa_exito,
            ROUND(AVG(satisfaccion_promedio), 2) as satisfaccion_promedio,
            ROUND(AVG((peso_inicial - peso_minimo) / peso_inicial * 100), 2) as promedio_perdida_peso,
            ROUND(AVG(total_consultas), 1) as promedio_consultas,
            ROUND(COUNT(CASE WHEN objetivo_alcanzado = 1 THEN 1 END) * 100.0 / 
                COUNT(*), 2) as porcentaje_exito
        FROM ExitoPorPlan
        GROUP BY tipo_plan
        ORDER BY tasa_exito DESC;
        """
        
        cursor.execute(query)
        resultados = cursor.fetchall()
        
        # Procesar los resultados para asegurar tipos de datos correctos
        datos_formateados = []
        for row in resultados:
            datos_formateados.append({
                'tipo_plan': row['tipo_plan'],
                'total_pacientes': row['total_pacientes'],
                'tasa_exito': float(row['tasa_exito']) if row['tasa_exito'] else 0,
                'satisfaccion_promedio': float(row['satisfaccion_promedio']) if row['satisfaccion_promedio'] else 0,
                'promedio_perdida_peso': float(row['promedio_perdida_peso']) if row['promedio_perdida_peso'] else 0,
                'promedio_consultas': float(row['promedio_consultas']) if row['promedio_consultas'] else 0,
                'porcentaje_exito': float(row['porcentaje_exito']) if row['porcentaje_exito'] else 0
            })

        cursor.close()
        connection.close()
        
        return jsonify({
            'success': True,
            'data': datos_formateados
        })

    except Error as e:
        logger.error(f"Error en la consulta: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 7000))
    logger.info(f"Iniciando servidor en el puerto {port}")
    app.run(host="0.0.0.0", port=port, debug=True)
