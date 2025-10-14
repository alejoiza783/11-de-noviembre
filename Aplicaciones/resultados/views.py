from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Count, F
from Aplicaciones.votacion.models import ProcesoElectoral, Voto
from Aplicaciones.elecciones.models import Lista
from Aplicaciones.padron.models import PadronElectoral
import os
from django.conf import settings
from django.http import HttpResponse, HttpResponseForbidden, HttpResponseNotFound, FileResponse
from datetime import datetime

@login_required
def resultados_votacion(request, proceso_id):
    proceso = get_object_or_404(ProcesoElectoral, id=proceso_id)
    
    # Verificar si el proceso ha finalizado (estado 'finalizado')
    if proceso.estado != 'finalizado':
        messages.warning(request, 'Los resultados solo están disponibles para procesos electorales finalizados.')
        return redirect('votacion:lista_procesos')  # Redirigir a la lista de procesos en la app de votación
    
    # Obtener votos por lista ordenados de mayor a menor
    votos_por_lista = Voto.objects.filter(
        proceso_electoral=proceso,
        lista__isnull=False
    ).values('lista').annotate(
        total=Count('id'),
        nombre_lista=F('lista__nombre_lista')
    ).order_by('-total')
    
    # Obtener total de votos
    total_votos = Voto.objects.filter(proceso_electoral=proceso).count()
    votos_blancos = Voto.objects.filter(proceso_electoral=proceso, es_blanco=True).count()
    votos_nulos = Voto.objects.filter(proceso_electoral=proceso, es_nulo=True).count()
    
    # Calcular porcentajes y determinar ganador
    resultados_por_lista = []
    ganador = None
    max_votos = 0
    
    for voto in votos_por_lista:
        lista = Lista.objects.get(id=voto['lista'])
        porcentaje = (voto['total'] / total_votos * 100) if total_votos > 0 else 0
        resultado = {
            'lista': lista,
            'votos': voto['total'],
            'porcentaje': porcentaje,
            'es_ganador': False
        }
        
        # Verificar si es el ganador actual
        if voto['total'] > max_votos:
            max_votos = voto['total']
            if ganador is not None:
                # Quitar condición de ganador del anterior
                for r in resultados_por_lista:
                    r['es_ganador'] = False
            resultado['es_ganador'] = True
            ganador = lista
        
        resultados_por_lista.append(resultado)
    
    # Calcular porcentajes de blancos y nulos
    porcentaje_blancos = (votos_blancos / total_votos * 100) if total_votos > 0 else 0
    porcentaje_nulos = (votos_nulos / total_votos * 100) if total_votos > 0 else 0
    
    # Obtener estadísticas de participación
    total_votantes = PadronElectoral.objects.filter(periodo=proceso.periodo).count()
    faltan_votar = total_votantes - total_votos
    porcentaje_participacion = (total_votos / total_votantes * 100) if total_votantes > 0 else 0
    
    context = {
        'proceso': proceso,
        'resultados_por_lista': resultados_por_lista,
        'ganador': ganador,
        'votos_ganador': max_votos,
        'votos_blancos': votos_blancos,
        'votos_nulos': votos_nulos,
        'porcentaje_blancos': porcentaje_blancos,
        'porcentaje_nulos': porcentaje_nulos,
        'total_votos': total_votos,
        'total_votantes': total_votantes,
        'faltan_votar': faltan_votar,
        'porcentaje_participacion': porcentaje_participacion
    }
    
    return render(request, 'resultados/resultados.html', context)

def lista_resultados(request):
    procesos = ProcesoElectoral.objects.all().order_by('-created_at')
    return render(request, 'resultados/lista_resultados.html', {
        'procesos': procesos,
        'titulo': 'Resultados de Procesos Electorales'
    })


#===============================================
# Funcion para descargar backup
#===============================================
@login_required
def descargar_backup_sqlite(request):
    try:
        ruta_db = settings.DATABASES['default']['NAME']
    except KeyError:
        return HttpResponseNotFound("Configuración de base de datos no encontrada")

    if os.path.exists(ruta_db):
        fecha_actual = datetime.now().strftime('%Y-%m-%d')
        nombre_archivo = f"backup_escuela_riobamba_{fecha_actual}.sqlite3"
        return FileResponse(open(ruta_db, 'rb'), as_attachment=True, filename=nombre_archivo)
    else:
        return HttpResponseNotFound(f"Archivo de base de datos no encontrado en: {ruta_db}")
