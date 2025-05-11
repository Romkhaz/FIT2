#!/usr/bin/env python3
"""
merge_fit_gpx.py

Модуль с функцией merge(), которая:
- читает FIT-файл Garmin;
- читает корректный GPX-трек;
- синхронизирует время и метрики по дистанции;
- сохраняет итоговый GPX с данными из FIT и траекторией из GPX.
"""

import math
from fitparse import FitFile
import xml.etree.ElementTree as ET
from datetime import datetime

def parse_fit(fit_path):
    fit = FitFile(fit_path)
    records = []
    for msg in fit.get_messages('record'):
        rec = {}
        for data in msg:
            rec[data.name] = data.value
        if 'timestamp' in rec and isinstance(rec['timestamp'], datetime):
            rec['timestamp_dt'] = rec['timestamp']
        # Приводим distance к float, если есть
        if 'distance' in rec and rec['distance'] is not None:
            rec['distance'] = float(rec['distance'])
        records.append(rec)
    return records

def parse_gpx(gpx_path):
    tree = ET.parse(gpx_path)
    root = tree.getroot()
    # Определяем namespace из корня
    ns_uri = root.tag.split('}')[0].strip('{')
    ns = {'ns': ns_uri}
    trkpts = root.findall('.//ns:trkpt', ns)
    return tree, trkpts, ns

def haversine(lat1, lon1, lat2, lon2):
    R = 6371000.0  # радиус Земли в метрах
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))

def merge_and_write(records, tree, trkpts, ns, output_path):
    if not records or not trkpts:
        raise ValueError("Нет данных для объединения")

    # Времена и длительность FIT
    fit_start = records[0]['timestamp_dt']
    fit_end = records[-1]['timestamp_dt']
    fit_duration = fit_end - fit_start

    # Координаты GPX и кумулятивная дистанция
    coords = [(float(pt.attrib['lat']), float(pt.attrib['lon'])) for pt in trkpts]
    cum_dists = [0.0] * len(coords)
    for i in range(1, len(coords)):
        cum_dists[i] = cum_dists[i-1] + haversine(*coords[i-1], *coords[i])
    total_gpx_dist = cum_dists[-1] or (len(cum_dists)-1)

    # Перераспределяем время по точкам GPX
    for i, pt in enumerate(trkpts):
        ratio = cum_dists[i] / total_gpx_dist if total_gpx_dist else i/(len(trkpts)-1)
        new_time = fit_start + ratio * fit_duration
        time_elem = pt.find('ns:time', ns)
        if time_elem is None:
            time_elem = ET.SubElement(pt, f'{{{ns["ns"]}}}time')
        time_elem.text = new_time.strftime('%Y-%m-%dT%H:%M:%SZ')

    # Добавляем метрики из FIT (через Garmin TrackPointExtension)
    garmin_ns = 'http://www.garmin.com/xmlschemas/TrackPointExtension/v1'
    ET.register_namespace('gpxtpx', garmin_ns)
    for rec in records:
        if 'distance' not in rec:
            continue
        # Найти ближайшую точку по дистанции
        idx = min(range(len(cum_dists)), key=lambda k: abs(cum_dists[k] - rec['distance']))
        pt = trkpts[idx]
        ext = pt.find('ns:extensions', ns)
        if ext is None:
            ext = ET.SubElement(pt, f'{{{ns["ns"]}}}extensions')
        tpe = ET.SubElement(ext, f'{{{garmin_ns}}}TrackPointExtension')
        for tag, key in [('ele', 'altitude'), ('hr', 'heart_rate'), ('cad', 'cadence'), ('speed', 'speed')]:
            if key in rec and rec[key] is not None:
                el = ET.SubElement(tpe, f'{{{garmin_ns}}}{tag}')
                el.text = str(rec[key])

    # Пишем в файл
    ET.register_namespace('', ns['ns'])
    tree.write(output_path, encoding='utf-8', xml_declaration=True)

    # Возвращаем длительности
    fmt = '%Y-%m-%dT%H:%M:%SZ'
    out_start = datetime.strptime(trkpts[0].find('ns:time', ns).text, fmt)
    out_end   = datetime.strptime(trkpts[-1].find('ns:time', ns).text, fmt)
    return (fit_end - fit_start), (out_end - out_start)

def merge(fit_path, gpx_path, output_path):
    """
    Основная функция, импортируемая в bot.py
    """
    records = parse_fit(fit_path)
    tree, trkpts, ns = parse_gpx(gpx_path)
    fit_dur, out_dur = merge_and_write(records, tree, trkpts, ns, output_path)
    return fit_dur, out_dur
