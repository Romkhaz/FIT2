#!/usr/bin/env python3
"""
merge_fit_gpx.py

Скрипт для слияния данных из FIT-файла Garmin с корректным GPX-треком.

Требует установки:
    pip install fitparse

Использование:
    python merge_fit_gpx.py input.fit input.gpx output.gpx
"""
import sys
import math
from fitparse import FitFile
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta


def parse_fit(fit_path):
    """
    Разобрать FIT-файл и вернуть список записей со всеми полями.
    Каждая запись — словарь с ключами: 'timestamp_dt', 'time', 'distance', 'altitude', 'heart_rate', 'cadence', 'speed' и т.д.
    """
    fit = FitFile(fit_path)
    records = []
    for msg in fit.get_messages('record'):
        rec = {}
        for data in msg:
            rec[data.name] = data.value
        # Временная метка
        if 'timestamp' in rec and isinstance(rec['timestamp'], datetime):
            rec['timestamp_dt'] = rec['timestamp']
            rec['time'] = rec['timestamp'].strftime('%Y-%m-%dT%H:%M:%SZ')
        # Дистанция (метры)
        if 'distance' in rec and rec['distance'] is not None:
            rec['distance'] = float(rec['distance'])
        records.append(rec)
    return records


def parse_gpx(gpx_path):
    """
    Разобрать GPX-файл, вернуть дерево, корневой элемент, список трекпоинтов и namespace.
    """
    tree = ET.parse(gpx_path)
    root = tree.getroot()
    ns_uri = root.tag.split('}')[0].strip('{')
    ns = {'ns': ns_uri}
    trkpts = root.findall('.//ns:trkpt', ns)
    return tree, root, trkpts, ns


def haversine(lat1, lon1, lat2, lon2):
    """
    Вычислить расстояние между двумя точками (метры) по формуле гаверсинусов.
    """
    R = 6371000  # радиус Земли в метрах
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = phi2 - phi1
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1-a))


def merge_and_write(records, tree, trkpts, ns, output_path):
    """
    Объединить данные из FIT-записей с GPX-тачками.
    Вернуть длительности FIT и итогового GPX (timedelta).
    """
    if not records or not trkpts:
        print('Нет данных для объединения.', flush=True)
        sys.exit(1)

    # Начало и длительность FIT-тренировки
    fit_start = records[0]['timestamp_dt']
    fit_end = records[-1]['timestamp_dt']
    fit_duration = fit_end - fit_start

    # Собрать координаты GPX и вычислить кумулятивные расстояния
    coords = [(float(pt.attrib['lat']), float(pt.attrib['lon'])) for pt in trkpts]
    cum_dists = [0.0] * len(coords)
    for i in range(1, len(coords)):
        lat1, lon1 = coords[i-1]
        lat2, lon2 = coords[i]
        cum_dists[i] = cum_dists[i-1] + haversine(lat1, lon1, lat2, lon2)
    total_gpx_dist = cum_dists[-1] if cum_dists[-1] > 0 else (len(cum_dists)-1)

    # Пересчитать время для GPX-точек
    for i, trkpt in enumerate(trkpts):
        ratio = cum_dists[i] / total_gpx_dist if total_gpx_dist else i/(len(trkpts)-1)
        new_time = fit_start + ratio * fit_duration
        time_elem = trkpt.find('ns:time', ns)
        if time_elem is None:
            time_elem = ET.SubElement(trkpt, f'{{{ns['ns']}}}time')
        time_elem.text = new_time.strftime('%Y-%m-%dT%H:%M:%SZ')

    # Метрики Garmin TrackPointExtension
    garmin_ns = 'http://www.garmin.com/xmlschemas/TrackPointExtension/v1'
    for rec in records:
        if 'distance' not in rec:
            continue
        idx = min(range(len(cum_dists)), key=lambda k: abs(cum_dists[k] - rec['distance']))
        trkpt = trkpts[idx]
        ext = trkpt.find('ns:extensions', ns) or ET.SubElement(trkpt, f'{{{ns['ns']}}}extensions')
        tpe = ET.SubElement(ext, f'{{{garmin_ns}}}TrackPointExtension')
        for tag in ('altitude', 'heart_rate', 'cadence', 'speed'):
            if tag in rec:
                elem = ET.SubElement(tpe, f'{{{garmin_ns}}}' + ('ele' if tag=='altitude' else tag[:2] if tag!='speed' else 'speed'))
                elem.text = str(rec[tag])

    # Сохранить GPX
    ET.register_namespace('', ns['ns'])
    ET.register_namespace('gpxtpx', garmin_ns)
    tree.write(output_path, encoding='utf-8', xml_declaration=True)

    # Вычислить длительность итогового GPX
    fmt = '%Y-%m-%dT%H:%M:%SZ'
    out_start = datetime.strptime(trkpts[0].find('ns:time', ns).text, fmt)
    out_end = datetime.strptime(trkpts[-1].find('ns:time', ns).text, fmt)
    out_duration = out_end - out_start
    return fit_duration, out_duration


def main():
    if len(sys.argv) != 4:
        print('Использование: python merge_fit_gpx.py input.fit input.gpx output.gpx', flush=True)
        sys.exit(1)

    fit_path, gpx_path, output_path = sys.argv[1], sys.argv[2], sys.argv[3]
    records = parse_fit(fit_path)
    tree, root, trkpts, ns = parse_gpx(gpx_path)
    fit_dur, gpx_dur = merge_and_write(records, tree, trkpts, ns, output_path)
    print(f'Длительность FIT-тренировки: {fit_dur}', flush=True)
    print(f'Длительность итогового GPX: {gpx_dur}', flush=True)
    print(f'Итоговый GPX файл сохранён: {output_path}', flush=True)
    # Пауза для Windows, чтобы видеть вывод
    if sys.platform.startswith('win'):
        input('Нажмите Enter для выхода...')


if __name__ == '__main__':
    main()
