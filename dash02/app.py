from flask import Flask, request, jsonify, render_template
import mysql.connector
from mysql.connector import Error
import os
from dotenv import load_dotenv
import logging
import pathlib
from datetime import datetime
from flask_cors import CORS

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Ruta relativa al archivo .env desde app.py
current_dir = pathlib.Path(__file__).parent  # Esto apunta a 'dash2'
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

def conexionBD():
    try:
        logger.debug("Intentando conectar a la base de datos...")
        connection = mysql.connector.connect(**DB_CONFIG)
        logger.debug("Conexión exitosa a la base de datos")
        return connection
    except Error as e:
        logger.error(f"Error al conectar a MySQL: {e}")
        return None
    
@app.route('/')
def dashboard():
    return render_template('Dash1.html')

@app.route('/api/tendencia-retencion', methods=['GET'])
def obtener_tendencia_retencion():
    connection = None
    cursor = None
    try:
        connection = conexionBD()
        if not connection:
            logger.error("No se pudo establecer la conexión a la base de datos")
            return jsonify({'error': 'Error de conexión a la base de datos'}), 500

        cursor = connection.cursor(dictionary=True)
        
        query = """
        WITH ConsultasPorPaciente AS (
            SELECT 
                c.id_paciente,
                COUNT(*) as num_consultas,
                AVG(c.precio_final) as precio_promedio_consulta
            FROM dim_consulta c
            GROUP BY c.id_paciente
        ),
        RangosPrecios AS (
            SELECT 
                CASE 
                    WHEN precio_promedio_consulta <= 210 THEN '210'
                    WHEN precio_promedio_consulta <= 225 THEN '225'
                    WHEN precio_promedio_consulta <= 250 THEN '250'
                    WHEN precio_promedio_consulta <= 300 THEN '300'
                    ELSE '500'
                END as rango_precio,
                COUNT(*) as total_pacientes,
                AVG(num_consultas) as promedio_consultas,
                MIN(num_consultas) as min_consultas,
                MAX(num_consultas) as max_consultas
            FROM ConsultasPorPaciente
            GROUP BY 
                CASE 
                    WHEN precio_promedio_consulta <= 210 THEN '210'
                    WHEN precio_promedio_consulta <= 225 THEN '225'
                    WHEN precio_promedio_consulta <= 250 THEN '250'
                    WHEN precio_promedio_consulta <= 300 THEN '300'
                    ELSE '500'
                END
        )
        SELECT 
            rango_precio as precio_consulta,
            total_pacientes,
            ROUND(promedio_consultas, 2) as promedio_consultas,
            min_consultas as minimo_consultas,
            max_consultas as maximo_consultas,
            ROUND((total_pacientes * 100.0) / (SELECT SUM(total_pacientes) FROM RangosPrecios), 2) as porcentaje_pacientes
        FROM RangosPrecios
        ORDER BY 
            CASE rango_precio
                WHEN '210' THEN 1
                WHEN '225' THEN 2
                WHEN '250' THEN 3
                WHEN '300' THEN 4
                ELSE 5
            END;
        """
        
        cursor.execute(query)
        resultados = cursor.fetchall()
        
        if not resultados:
            return jsonify({'mensaje': 'No se encontraron datos'}), 404

        respuesta = {
            'status': 'success',
            'data': resultados,
            'mensaje': 'Datos de tendencia de retención obtenidos exitosamente'
        }
        
        return jsonify(respuesta), 200

    except Error as e:
        logger.error(f"Error en la consulta SQL: {str(e)}")
        return jsonify({'error': 'Error al procesar la consulta'}), 500
    
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        return jsonify({'error': 'Error interno del servidor'}), 500
    
    finally:
        try:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()
                logger.debug("Conexión a la base de datos cerrada")
        except Error as e:
            logger.error(f"Error al cerrar la conexión: {str(e)}")

@app.route('/api/relacion-peso-satisfaccion', methods=['GET'])
def obtener_relacion_peso_satisfaccion():
    connection = None
    cursor = None
    try:
        connection = conexionBD()
        if not connection:
            logger.error("No se pudo establecer la conexión a la base de datos")
            return jsonify({'error': 'Error de conexión a la base de datos'}), 500

        cursor = connection.cursor(dictionary=True)
        
        query = """
        WITH DatosPeso AS (
            SELECT 
                dp.información as tipo_plan,
                c.peso_actual - c.peso_logrado as peso_perdido,
                c.satisfaccion,
                COUNT(*) as cantidad_pacientes,
                AVG(c.satisfaccion) as promedio_satisfaccion,
                AVG(c.peso_actual - c.peso_logrado) as promedio_peso_perdido
            FROM dim_consulta c
            JOIN dim_plan dp ON c.id_plan = dp.id_plan
            WHERE 
                c.peso_logrado IS NOT NULL 
                AND c.satisfaccion IS NOT NULL
                AND c.peso_actual IS NOT NULL
            GROUP BY 
                dp.información,
                c.peso_actual - c.peso_logrado,
                c.satisfaccion
        ),
        EstadisticasPorPlan AS (
            SELECT 
                tipo_plan,
                ROUND(AVG(promedio_satisfaccion), 2) as satisfaccion_promedio,
                ROUND(AVG(promedio_peso_perdido), 2) as peso_perdido_promedio,
                COUNT(DISTINCT satisfaccion) as diferentes_niveles_satisfaccion,
                MIN(satisfaccion) as min_satisfaccion,
                MAX(satisfaccion) as max_satisfaccion,
                ROUND(MIN(peso_perdido), 2) as min_peso_perdido,
                ROUND(MAX(peso_perdido), 2) as max_peso_perdido,
                SUM(cantidad_pacientes) as total_pacientes,
                ROUND(
                    SUM(CASE WHEN satisfaccion >= 8 THEN cantidad_pacientes ELSE 0 END) * 100.0 / 
                    SUM(cantidad_pacientes), 
                    2
                ) as porcentaje_muy_satisfechos,
                ROUND(
                    SUM(CASE WHEN peso_perdido >= 10 THEN cantidad_pacientes ELSE 0 END) * 100.0 / 
                    SUM(cantidad_pacientes), 
                    2
                ) as porcentaje_perdida_significativa
            FROM DatosPeso
            GROUP BY tipo_plan
        )
        SELECT 
            tipo_plan,
            satisfaccion_promedio,
            peso_perdido_promedio,
            diferentes_niveles_satisfaccion,
            min_satisfaccion,
            max_satisfaccion,
            min_peso_perdido,
            max_peso_perdido,
            total_pacientes,
            porcentaje_muy_satisfechos as porcentaje_satisfaccion_alta,
            porcentaje_perdida_significativa as porcentaje_perdida_10kg_o_mas
        FROM EstadisticasPorPlan
        ORDER BY peso_perdido_promedio DESC;
        """
        
        cursor.execute(query)
        resultados = cursor.fetchall()
        
        if not resultados:
            return jsonify({
                'status': 'warning',
                'mensaje': 'No se encontraron datos para la relación peso-satisfacción',
                'data': []
            }), 404

        # Procesar los resultados para asegurar que los números sean del tipo correcto
        datos_procesados = []
        for row in resultados:
            dato_procesado = {
                'tipo_plan': row['tipo_plan'],
                'satisfaccion_promedio': float(row['satisfaccion_promedio']),
                'peso_perdido_promedio': float(row['peso_perdido_promedio']),
                'diferentes_niveles_satisfaccion': int(row['diferentes_niveles_satisfaccion']),
                'min_satisfaccion': float(row['min_satisfaccion']),
                'max_satisfaccion': float(row['max_satisfaccion']),
                'min_peso_perdido': float(row['min_peso_perdido']),
                'max_peso_perdido': float(row['max_peso_perdido']),
                'total_pacientes': int(row['total_pacientes']),
                'porcentaje_satisfaccion_alta': float(row['porcentaje_satisfaccion_alta']),
                'porcentaje_perdida_10kg_o_mas': float(row['porcentaje_perdida_10kg_o_mas'])
            }
            datos_procesados.append(dato_procesado)

        respuesta = {
            'status': 'success',
            'data': datos_procesados,
            'mensaje': 'Datos de relación peso-satisfacción obtenidos exitosamente',
            'total_registros': len(datos_procesados)
        }
        
        return jsonify(respuesta), 200

    except Error as e:
        logger.error(f"Error en la consulta SQL: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': 'Error al procesar la consulta',
            'detalle': str(e)
        }), 500
    
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': 'Error interno del servidor',
            'detalle': str(e)
        }), 500
    
    finally:
        try:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()
                logger.debug("Conexión a la base de datos cerrada")
        except Error as e:
            logger.error(f"Error al cerrar la conexión: {str(e)}")

@app.route('/api/progreso-objetivos-peso', methods=['GET'])
def obtener_progreso_objetivos():
    connection = None
    cursor = None
    try:
        connection = conexionBD()
        if not connection:
            logger.error("No se pudo establecer la conexión a la base de datos")
            return jsonify({'error': 'Error de conexión a la base de datos'}), 500

        cursor = connection.cursor(dictionary=True)
        
        query = """
        WITH ProgresoPeso AS (
            SELECT 
                dp.información as tipo_plan,
                c.peso_actual,
                c.peso_logrado,
                c.objetivo_peso,
                (c.peso_actual - c.objetivo_peso) as peso_total_a_perder,
                (c.peso_actual - c.peso_logrado) as peso_perdido,
                CASE 
                    WHEN (c.peso_actual - c.objetivo_peso) = 0 THEN 100
                    ELSE ROUND(
                        ((c.peso_actual - c.peso_logrado) * 100.0) / 
                        (c.peso_actual - c.objetivo_peso),
                        2
                    )
                END as porcentaje_progreso
            FROM dim_consulta c
            JOIN dim_plan dp ON c.id_plan = dp.id_plan
            WHERE 
                c.peso_actual IS NOT NULL 
                AND c.peso_logrado IS NOT NULL
                AND c.objetivo_peso IS NOT NULL
                AND c.peso_actual > c.objetivo_peso
        ),
        EstadisticasPorPlan AS (
            SELECT 
                tipo_plan,
                COUNT(*) as total_pacientes,
                ROUND(AVG(peso_total_a_perder), 2) as promedio_peso_objetivo,
                ROUND(AVG(peso_perdido), 2) as promedio_peso_perdido,
                ROUND(AVG(porcentaje_progreso), 2) as promedio_progreso,
                ROUND(SUM(CASE WHEN porcentaje_progreso >= 100 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as porcentaje_objetivo_alcanzado,
                ROUND(SUM(CASE WHEN porcentaje_progreso >= 75 AND porcentaje_progreso < 100 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as porcentaje_muy_cerca,
                ROUND(SUM(CASE WHEN porcentaje_progreso >= 50 AND porcentaje_progreso < 75 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as porcentaje_progreso_medio,
                ROUND(SUM(CASE WHEN porcentaje_progreso < 50 THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 2) as porcentaje_inicio_progreso,
                MIN(peso_perdido) as min_peso_perdido,
                MAX(peso_perdido) as max_peso_perdido,
                MIN(porcentaje_progreso) as min_porcentaje_progreso,
                MAX(porcentaje_progreso) as max_porcentaje_progreso
            FROM ProgresoPeso
            GROUP BY tipo_plan
        )
        SELECT 
            tipo_plan,
            total_pacientes,
            promedio_peso_objetivo as peso_promedio_a_perder,
            promedio_peso_perdido,
            promedio_progreso as porcentaje_promedio_progreso,
            porcentaje_objetivo_alcanzado as porc_alcanzaron_objetivo,
            porcentaje_muy_cerca as porc_75_a_99,
            porcentaje_progreso_medio as porc_50_a_74,
            porcentaje_inicio_progreso as porc_menos_50,
            min_peso_perdido,
            max_peso_perdido,
            min_porcentaje_progreso,
            max_porcentaje_progreso
        FROM EstadisticasPorPlan
        ORDER BY promedio_progreso DESC;
        """
        
        cursor.execute(query)
        resultados = cursor.fetchall()
        
        if not resultados:
            return jsonify({
                'status': 'warning',
                'mensaje': 'No se encontraron datos de progreso de objetivos de peso',
                'data': []
            }), 404

        # Procesar los resultados para asegurar tipos de datos correctos
        datos_procesados = []
        for row in resultados:
            dato_procesado = {
                'tipo_plan': row['tipo_plan'],
                'total_pacientes': int(row['total_pacientes']),
                'peso_promedio_a_perder': float(row['peso_promedio_a_perder']),
                'promedio_peso_perdido': float(row['promedio_peso_perdido']),
                'porcentaje_promedio_progreso': float(row['porcentaje_promedio_progreso']),
                'porc_alcanzaron_objetivo': float(row['porc_alcanzaron_objetivo']),
                'porc_75_a_99': float(row['porc_75_a_99']),
                'porc_50_a_74': float(row['porc_50_a_74']),
                'porc_menos_50': float(row['porc_menos_50']),
                'min_peso_perdido': float(row['min_peso_perdido']),
                'max_peso_perdido': float(row['max_peso_perdido']),
                'min_porcentaje_progreso': float(row['min_porcentaje_progreso']),
                'max_porcentaje_progreso': float(row['max_porcentaje_progreso'])
            }
            datos_procesados.append(dato_procesado)

        # Calcular estadísticas globales
        total_global_pacientes = sum(d['total_pacientes'] for d in datos_procesados)
        promedio_global_progreso = sum(d['porcentaje_promedio_progreso'] * d['total_pacientes'] for d in datos_procesados) / total_global_pacientes if total_global_pacientes > 0 else 0

        respuesta = {
            'status': 'success',
            'data': datos_procesados,
            'estadisticas_globales': {
                'total_pacientes': total_global_pacientes,
                'promedio_progreso_global': round(promedio_global_progreso, 2)
            },
            'mensaje': 'Datos de progreso de objetivos de peso obtenidos exitosamente',
            'total_planes': len(datos_procesados)
        }
        
        return jsonify(respuesta), 200

    except Error as e:
        logger.error(f"Error en la consulta SQL: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': 'Error al procesar la consulta',
            'detalle': str(e)
        }), 500
    
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': 'Error interno del servidor',
            'detalle': str(e)
        }), 500
    
    finally:
        try:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()
                logger.debug("Conexión a la base de datos cerrada")
        except Error as e:
            logger.error(f"Error al cerrar la conexión: {str(e)}")

@app.route('/api/consultas-gratuitas', methods=['GET'])
def obtener_pacientes_consulta_gratuita():
    connection = None
    cursor = None
    try:
        connection = conexionBD()
        if not connection:
            logger.error("No se pudo establecer la conexión a la base de datos")
            return jsonify({'error': 'Error de conexión a la base de datos'}), 500

        cursor = connection.cursor(dictionary=True)
        
        query = """
        WITH PacientesCalificados AS (
            SELECT 
                COUNT(DISTINCT c.id_paciente) as total_pacientes_calificados
            FROM dim_consulta c
            WHERE 
                c.peso_actual IS NOT NULL 
                AND c.peso_logrado IS NOT NULL
                AND c.objetivo_peso IS NOT NULL
                AND ABS(c.peso_logrado - c.objetivo_peso) <= (c.objetivo_peso * 0.00)
        ),
        TotalPacientes AS (
            SELECT 
                COUNT(DISTINCT id_paciente) as total_pacientes
            FROM dim_consulta
        )
        SELECT 
            pc.total_pacientes_calificados as pacientes_con_consulta_gratuita,
            ROUND((pc.total_pacientes_calificados * 100.0 / tp.total_pacientes), 2) as porcentaje_del_total
        FROM PacientesCalificados pc, TotalPacientes tp;
        """
        
        cursor.execute(query)
        resultado = cursor.fetchone()
        
        if not resultado:
            return jsonify({
                'status': 'warning',
                'mensaje': 'No se encontraron datos de consultas gratuitas',
                'data': {}
            }), 404

        respuesta = {
            'status': 'success',
            'data': {
                'total_pacientes_calificados': int(resultado['pacientes_con_consulta_gratuita']),
                'porcentaje_del_total': float(resultado['porcentaje_del_total'])
            },
            'mensaje': 'Datos de consultas gratuitas obtenidos exitosamente',
            'fecha_consulta': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return jsonify(respuesta), 200

    except Error as e:
        logger.error(f"Error en la consulta SQL: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': 'Error al procesar la consulta',
            'detalle': str(e)
        }), 500
    
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': 'Error interno del servidor',
            'detalle': str(e)
        }), 500
    
    finally:
        try:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()
                logger.debug("Conexión a la base de datos cerrada")
        except Error as e:
            logger.error(f"Error al cerrar la conexión: {str(e)}")

@app.route('/api/distribucion-costos', methods=['GET'])
def obtener_distribucion_costos():
    connection = None
    cursor = None
    try:
        connection = conexionBD()
        if not connection:
            logger.error("No se pudo establecer la conexión a la base de datos")
            return jsonify({'error': 'Error de conexión a la base de datos'}), 500

        cursor = connection.cursor(dictionary=True)
        
        # Consulta para estadísticas generales
        query_general = """
        SELECT 
            dp.información as tipo_plan,
            COUNT(*) as total_consultas,
            ROUND(AVG(c.precio_final), 2) as costo_promedio,
            ROUND(MIN(c.precio_final), 2) as costo_minimo,
            ROUND(MAX(c.precio_final), 2) as costo_maximo,
            ROUND(AVG(c.descuento), 2) as descuento_promedio,
            COUNT(DISTINCT c.id_paciente) as total_pacientes
        FROM dim_consulta c
        JOIN dim_plan dp ON c.id_plan = dp.id_plan
        GROUP BY dp.información
        ORDER BY costo_promedio DESC;
        """
        
        # Consulta para distribución por cuartiles
        query_distribucion = """
        WITH EstadisticasPorPlan AS (
            SELECT 
                dp.información as tipo_plan,
                c.precio_final,
                NTILE(4) OVER (PARTITION BY dp.información ORDER BY c.precio_final) as cuartil
            FROM dim_consulta c
            JOIN dim_plan dp ON c.id_plan = dp.id_plan
        )
        SELECT 
            tipo_plan,
            ROUND(MIN(CASE WHEN cuartil = 1 THEN precio_final END), 2) as q1,
            ROUND(MIN(CASE WHEN cuartil = 2 THEN precio_final END), 2) as mediana,
            ROUND(MIN(CASE WHEN cuartil = 3 THEN precio_final END), 2) as q3,
            ROUND(MIN(precio_final), 2) as minimo,
            ROUND(MAX(precio_final), 2) as maximo,
            ROUND(AVG(precio_final), 2) as promedio
        FROM EstadisticasPorPlan
        GROUP BY tipo_plan
        ORDER BY promedio DESC;
        """
        
        # Ejecutar primera consulta
        cursor.execute(query_general)
        estadisticas_generales = cursor.fetchall()
        
        # Ejecutar segunda consulta
        cursor.execute(query_distribucion)
        distribucion_cuartiles = cursor.fetchall()
        
        if not estadisticas_generales or not distribucion_cuartiles:
            return jsonify({
                'status': 'warning',
                'mensaje': 'No se encontraron datos de distribución de costos',
                'data': {}
            }), 404

        # Procesar y combinar los resultados
        resultados_combinados = {}
        
        # Procesar estadísticas generales
        for plan in estadisticas_generales:
            resultados_combinados[plan['tipo_plan']] = {
                'estadisticas_generales': {
                    'total_consultas': int(plan['total_consultas']),
                    'costo_promedio': float(plan['costo_promedio']),
                    'costo_minimo': float(plan['costo_minimo']),
                    'costo_maximo': float(plan['costo_maximo']),
                    'descuento_promedio': float(plan['descuento_promedio']),
                    'total_pacientes': int(plan['total_pacientes'])
                }
            }
        
        # Agregar distribución por cuartiles
        for plan in distribucion_cuartiles:
            if plan['tipo_plan'] in resultados_combinados:
                resultados_combinados[plan['tipo_plan']]['distribucion_cuartiles'] = {
                    'q1': float(plan['q1']),
                    'mediana': float(plan['mediana']),
                    'q3': float(plan['q3']),
                    'minimo': float(plan['minimo']),
                    'maximo': float(plan['maximo']),
                    'promedio': float(plan['promedio'])
                }

        respuesta = {
            'status': 'success',
            'data': resultados_combinados,
            'mensaje': 'Datos de distribución de costos obtenidos exitosamente',
            'fecha_consulta': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return jsonify(respuesta), 200

    except Error as e:
        logger.error(f"Error en la consulta SQL: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': 'Error al procesar la consulta',
            'detalle': str(e)
        }), 500
    
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': 'Error interno del servidor',
            'detalle': str(e)
        }), 500
    
    finally:
        try:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()
                logger.debug("Conexión a la base de datos cerrada")
        except Error as e:
            logger.error(f"Error al cerrar la conexión: {str(e)}")

@app.route('/api/adquisicion-pacientes', methods=['GET'])
def obtener_adquisicion_pacientes():
    connection = None
    cursor = None
    try:
        connection = conexionBD()
        if not connection:
            logger.error("No se pudo establecer la conexión a la base de datos")
            return jsonify({'error': 'Error de conexión a la base de datos'}), 500

        cursor = connection.cursor(dictionary=True)
        
        query = """
        WITH PrimerasConsultas AS (
            SELECT 
                id_paciente,
                MIN(fecha) as fecha_primera_consulta,
                dp.información as tipo_plan
            FROM dim_consulta c
            JOIN dim_plan dp ON c.id_plan = dp.id_plan
            GROUP BY id_paciente, dp.información
        ),
        AdquisicionMensual AS (
            SELECT 
                tipo_plan,
                DATE_FORMAT(fecha_primera_consulta, '%Y-%m') as mes,
                COUNT(*) as nuevos_pacientes
            FROM PrimerasConsultas
            GROUP BY tipo_plan, DATE_FORMAT(fecha_primera_consulta, '%Y-%m')
        ),
        CrecimientoPorPlan AS (
            SELECT 
                tipo_plan,
                mes,
                nuevos_pacientes,
                SUM(nuevos_pacientes) OVER (PARTITION BY tipo_plan ORDER BY mes) as pacientes_acumulados,
                LAG(nuevos_pacientes, 1) OVER (PARTITION BY tipo_plan ORDER BY mes) as mes_anterior,
                ROUND(((nuevos_pacientes - LAG(nuevos_pacientes, 1) OVER (PARTITION BY tipo_plan ORDER BY mes)) * 100.0) / 
                    NULLIF(LAG(nuevos_pacientes, 1) OVER (PARTITION BY tipo_plan ORDER BY mes), 0), 2) as porcentaje_crecimiento
            FROM AdquisicionMensual
        )
        SELECT 
            tipo_plan,
            mes,
            nuevos_pacientes,
            pacientes_acumulados,
            porcentaje_crecimiento as crecimiento_porcentual
        FROM CrecimientoPorPlan
        ORDER BY tipo_plan, mes;
        """
        
        cursor.execute(query)
        resultados = cursor.fetchall()
        
        if not resultados:
            return jsonify({
                'status': 'warning',
                'mensaje': 'No se encontraron datos de adquisición de pacientes',
                'data': {}
            }), 404

        # Procesar y organizar los resultados por plan
        datos_por_plan = {}
        for row in resultados:
            tipo_plan = row['tipo_plan']
            if tipo_plan not in datos_por_plan:
                datos_por_plan[tipo_plan] = []
            
            datos_mensuales = {
                'mes': row['mes'],
                'nuevos_pacientes': int(row['nuevos_pacientes']),
                'pacientes_acumulados': int(row['pacientes_acumulados']),
                'crecimiento_porcentual': float(row['crecimiento_porcentual']) if row['crecimiento_porcentual'] is not None else None
            }
            datos_por_plan[tipo_plan].append(datos_mensuales)

        # Calcular estadísticas globales
        estadisticas_globales = {
            'total_nuevos_pacientes': sum(row['nuevos_pacientes'] for row in resultados),
            'promedio_mensual_nuevos_pacientes': round(sum(row['nuevos_pacientes'] for row in resultados) / 
                                                     len(set(row['mes'] for row in resultados)), 2),
            'meses_analizados': len(set(row['mes'] for row in resultados))
        }

        respuesta = {
            'status': 'success',
            'data': {
                'adquisicion_por_plan': datos_por_plan,
                'estadisticas_globales': estadisticas_globales
            },
            'mensaje': 'Datos de adquisición de pacientes obtenidos exitosamente',
            'fecha_consulta': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return jsonify(respuesta), 200

    except Error as e:
        logger.error(f"Error en la consulta SQL: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': 'Error al procesar la consulta',
            'detalle': str(e)
        }), 500
    
    except Exception as e:
        logger.error(f"Error inesperado: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': 'Error interno del servidor',
            'detalle': str(e)
        }), 500
    
    finally:
        try:
            if cursor:
                cursor.close()
            if connection and connection.is_connected():
                connection.close()
                logger.debug("Conexión a la base de datos cerrada")
        except Error as e:
            logger.error(f"Error al cerrar la conexión: {str(e)}")

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    logger.info(f"Iniciando servidor en el puerto {port}")
    app.run(host="0.0.0.0", port=port, debug=True)