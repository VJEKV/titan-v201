# -*- coding: utf-8 -*-
"""
generate_demo_lukoil.py — Генератор демо-файла ТОРО для 4 НПЗ ЛУКОЙЛ.

Выход: /root/titan-v200/DEMO_LUKOIL_2024-2026.xlsx (55 колонок SAP NEW_STATUS_HISTORY)
Период: 01.01.2024 — 14.04.2026 (≈835 дней, 2,29 года)
Объём: ≈130 000 заказов, ≈390 000 строк истории статусов.
"""

import os
import sys
import json
import math
import random
import datetime as dt
from pathlib import Path
from collections import defaultdict

from openpyxl import Workbook

# ═══════════════════════════════════════════════════════════════════════════
# КОНФИГУРАЦИЯ
# ═══════════════════════════════════════════════════════════════════════════

random.seed(42)

OUT_PATH = Path('/root/titan-v200/DEMO_LUKOIL_2024-2026.xlsx')
TM_JSON_PATH = Path('/root/titan-v200/backend/data/tm_structure.json')

PERIOD_START = dt.datetime(2024, 1, 1, 0, 0, 0)
PERIOD_END = dt.datetime(2026, 4, 14, 23, 59, 59)
PERIOD_DAYS = (PERIOD_END - PERIOD_START).days  # ≈835
YEARS = PERIOD_DAYS / 365.25  # ≈2.285


def infl_factor(date: dt.datetime) -> float:
    """Инфляция: 2025 → +10%, 2026 → +20%."""
    if date.year >= 2026:
        return 1.20
    if date.year >= 2025:
        return 1.10
    return 1.00


def iso_z(d: dt.datetime) -> str:
    """Формат даты как в SAP-выгрузке: YYYY-MM-DDTHH:MM:SSZ."""
    return d.strftime('%Y-%m-%dT%H:%M:%SZ')


EPOCH_ZERO = '1970-01-01T00:00:00Z'

# ═══════════════════════════════════════════════════════════════════════════
# ЗАВОДЫ
# ═══════════════════════════════════════════════════════════════════════════

PLANTS = {
    'NN': {
        'bukrs': '1000', 'bukrs_txt': 'ООО "ЛУКОЙЛ-Нижегороднефтеоргсинтез"',
        'iwerk': '1100', 'iwerk_txt': 'ННОС Нижегороднефтеоргсинтез',
        'orders_per_year': 20000, 'city': 'Кстово',
    },
    'VG': {
        'bukrs': '2000', 'bukrs_txt': 'ООО "ЛУКОЙЛ-Волгограднефтепереработка"',
        'iwerk': '2100', 'iwerk_txt': 'Волгограднефтепереработка',
        'orders_per_year': 17000, 'city': 'Волгоград',
    },
    'PN': {
        'bukrs': '3000', 'bukrs_txt': 'ООО "ЛУКОЙЛ-Пермнефтеоргсинтез"',
        'iwerk': '3100', 'iwerk_txt': 'Пермнефтеоргсинтез',
        'orders_per_year': 15300, 'city': 'Пермь',
    },
    'UH': {
        'bukrs': '4000', 'bukrs_txt': 'ООО "ЛУКОЙЛ-Ухтанефтепереработка"',
        'iwerk': '4100', 'iwerk_txt': 'Ухтанефтепереработка',
        'orders_per_year': 4700, 'city': 'Ухта',
    },
}

# ═══════════════════════════════════════════════════════════════════════════
# УСТАНОВКИ
# Формат: (код_пр-ва, код_цеха, код_установки, название, orders_per_year_weight)
# ═══════════════════════════════════════════════════════════════════════════

PLANT_UNITS = {
    'NN': [
        ('01', '0110', 'AV06', 'АВТ-6', 1450),
        ('01', '0120', 'AT06', 'АТ-6', 1400),
        ('01', '0130', 'AV05', 'АВТ-5', 1200),
        ('01', '0210', 'L246', 'Л-24/6 Гидроочистка ДТ', 980),
        ('01', '0220', 'L247', 'Л-24/7 Гидроочистка', 820),
        ('01', '0310', 'LG35', 'ЛГ-35-8/300Б Риформинг', 480),
        ('01', '0320', 'LC35', 'ЛЧ-35-11/1000 Риформинг', 620),
        ('01', '0410', 'PNEX', 'PENEX Изомалк-2 Изомеризация', 380),
        ('02', '0110', 'KK01', 'КК-1 Каталитический крекинг', 2000),
        ('02', '0120', 'KK02', 'КК-2 (43-103) Каталитический крекинг', 1850),
        ('02', '0210', 'GFU1', 'ГФУ-1 Газофракционирующая', 450),
        ('02', '0220', 'GFU2', 'ГФУ-2 Газофракционирующая', 430),
        ('03', '0110', 'UZK1', 'УЗК Замедленного коксования', 2300),
        ('03', '0120', 'GOKR', 'ГО-КР-1,5 Гидроочистка+Риформинг', 900),
        ('03', '0210', 'GF42', 'ГФУ-425 Газофракционирующая', 390),
        ('03', '0310', 'PS81', 'ПС-81 Производство серы', 620),
        ('03', '0320', 'PVH2', 'ПВ-Н2 Производство водорода', 320),
        ('04', '0110', 'BIT1', 'Битумная-1', 520),
        ('04', '0120', 'BIT2', 'Битумная-2', 410),
        ('04', '0210', 'PARF', 'Парафиновая установка', 290),
        ('04', '0220', 'OKBT', 'Установка окисления битумов', 220),
        ('05', '0110', 'TSP1', 'ТСП Товарно-сырьевое производство', 1480),
        ('05', '0210', 'OZH1', 'ОЗХ Общезаводское хозяйство', 1450),
        ('05', '0310', 'GTU1', 'ГТУ-ТЭС', 420),
    ],
    'VG': [
        ('01', '0110', 'AVT1', 'ЭЛОУ-АВТ-1', 1850),
        ('01', '0120', 'AVT5', 'ЭЛОУ-АВТ-5', 1250),
        ('01', '0130', 'AVT6', 'ЭЛОУ-АВТ-6', 1300),
        ('01', '0140', 'AVT4', 'АВТ-4', 950),
        ('01', '0150', 'AT01', 'АТ-1', 820),
        ('02', '0110', 'GKVG', 'Комплекс гидрокрекинга ВГО', 2100),
        ('02', '0120', 'UZKV', 'УЗК Замедленного коксования', 1700),
        ('02', '0210', 'RIFB', 'Бензольный риформинг', 540),
        ('02', '0220', 'RIFK', 'Каталитический риформинг', 580),
        ('02', '0310', 'GOKR', 'Гидроочистка керосина', 460),
        ('03', '0110', 'KM03', 'КМ-3 Комплекс масел', 1100),
        ('03', '0120', 'DEAS', 'Деасфальтизация', 430),
        ('03', '0210', 'SELO', 'Селективная очистка (фурфурол)', 550),
        ('03', '0220', 'DPAR', 'Карбамидная депарафинизация', 410),
        ('03', '0310', 'PPRI', 'Производство присадок', 340),
        ('04', '0110', 'TSPV', 'ТСП Товарно-сырьевое', 1250),
        ('04', '0210', 'OZHV', 'ОЗХ Общезаводское хозяйство', 1200),
        ('04', '0310', 'FAKL', 'Факельное хозяйство', 170),
    ],
    'PN': [
        ('01', '0110', 'AVT2', 'АВТ-2', 850),
        ('01', '0120', 'AVT3', 'ЭЛОУ-АВТ-3', 1100),
        ('01', '0130', 'AVT4', 'АВТ-4', 1050),
        ('01', '0140', 'AVT5', 'АВТ-5', 1280),
        ('02', '0110', 'GKRK', 'Комплекс гидрокрекинга', 1950),
        ('02', '0120', 'UZKP', 'УЗК Замедленного коксования', 1550),
        ('02', '0210', 'KRKT', 'Каталитический крекинг', 880),
        ('02', '0220', 'TKRK', 'Термический крекинг', 340),
        ('02', '0310', 'ALKP', 'Алкилирование', 360),
        ('03', '0110', 'RIFP', 'Каталитический риформинг', 560),
        ('03', '0120', 'IZMP', 'Изомеризация парафинов', 380),
        ('03', '0130', 'GO24', '24-100 Гидроочистка ср.дистиллятов', 720),
        ('03', '0210', 'DKSP', 'Установка ДКС', 240),
        ('03', '0220', 'NTKR', 'НТКР-2', 280),
        ('04', '0110', 'G43M', 'Г-43-107М Маслоблок', 1420),
        ('04', '0120', 'PRFP', 'Парафиновое производство', 510),
        ('04', '0210', 'PSER', 'Установка серы', 430),
        ('04', '0220', 'GDAP', 'ГДА', 290),
        ('04', '0310', 'KCA1', 'КЦА (PSA)', 380),
        ('04', '0320', 'ASSB', 'АС Смешения бензинов', 180),
        ('05', '0110', 'TSPP', 'ТСП Товарно-сырьевое', 1100),
        ('05', '0210', 'OZHP', 'ОЗХ Общезаводское хозяйство', 1050),
        ('05', '0310', 'GTUP', 'ГТУ-ТЭС 200 МВт', 520),
    ],
    'UH': [
        ('01', '0110', 'AT01', 'АТ-1', 580),
        ('01', '0120', 'AVTU', 'АВТ', 720),
        ('02', '0110', 'R351', '35-11/300-95 Риформинг+Изомеризация', 650),
        ('02', '0210', 'GDS8', 'ГДС-850 Гидроочистка ДТ', 620),
        ('03', '0110', 'VISB', 'Висбрекинг', 780),
        ('03', '0210', 'BITU', 'Битумная установка', 460),
        ('04', '0110', 'TSPU', 'ТСП Товарно-сырьевое', 470),
        ('04', '0210', 'OZHU', 'ОЗХ Общезаводское хозяйство', 420),
    ],
}

# Производства и цеха (названия)
PRODUCTIONS = {
    'NN': {
        '01': 'Производство моторных топлив',
        '02': 'Производство каталитического крекинга',
        '03': 'КПНО Комплекс переработки нефтяных остатков',
        '04': 'Производство нефтебитумов и парафинов',
        '05': 'Производство по обслуживанию установок',
    },
    'VG': {
        '01': 'Производство первичной переработки',
        '02': 'Производство глубокой переработки',
        '03': 'Производство масел',
        '04': 'Общезаводское хозяйство',
    },
    'PN': {
        '01': 'Производство первичной переработки',
        '02': 'Производство глубокой переработки',
        '03': 'Производство моторных топлив',
        '04': 'Производство масел и спецпроизводств',
        '05': 'Производство по обслуживанию',
    },
    'UH': {
        '01': 'Производство первичной переработки',
        '02': 'Производство моторных топлив',
        '03': 'Производство остаточных продуктов и битумов',
        '04': 'Общезаводское хозяйство',
    },
}

SHOPS = {
    '0110': '1-й технологический цех', '0120': '2-й технологический цех',
    '0130': '3-й технологический цех', '0140': '4-й технологический цех',
    '0150': '5-й технологический цех',
    '0210': '1-й вспомогательный цех', '0220': '2-й вспомогательный цех',
    '0310': 'Ремонтно-механический цех', '0320': 'Цех КИПиА',
    '0410': 'Цех общезаводского хозяйства',
}

# ═══════════════════════════════════════════════════════════════════════════
# ТИПЫ ОБОРУДОВАНИЯ
# ═══════════════════════════════════════════════════════════════════════════

# (класс_код, имя_класса, имя_объекта_шаблон, динамическое?, баз_цикл_дней, баз_стоимость_руб, диапазон_плюсминус%)
EQ_TYPES = {
    'PUMP_C': ('RD_PM0101', 'Насосы центробежные', 'Насос центробежный Н-{n}', True, 210, 380_000, 45),
    'PUMP_P': ('RD_PM0102', 'Насосы поршневые', 'Насос поршневой Н-{n}', True, 150, 450_000, 50),
    'PUMP_S': ('RD_PM0103', 'Насосы шестерённые', 'Насос шестерённый Н-{n}', True, 180, 280_000, 40),
    'COMPR_C': ('RD_PM0201', 'Компрессоры центробежные', 'Компрессор центробежный К-{n}', True, 480, 4_500_000, 60),
    'COMPR_P': ('RD_PM0202', 'Компрессоры поршневые', 'Компрессор поршневой К-{n}', True, 300, 2_800_000, 55),
    'TURBN': ('RD_PM0301', 'Турбины', 'Турбина Т-{n}', True, 540, 12_000_000, 70),
    'FAN_VAC': ('RD_PM0401', 'Вентиляторы АВО', 'Вентилятор АВО В-{n}', True, 420, 320_000, 40),
    'MOTOR': ('RD_PM0501', 'Электродвигатели', 'Электродвигатель М-{n}', True, 540, 180_000, 35),
    'HEATX': ('RD_PM0601', 'Теплообменники', 'Теплообменник Т-{n}', False, 540, 1_100_000, 45),
    'COLUM': ('RD_PM0701', 'Колонны ректификационные', 'Колонна К-{n}', False, 900, 5_500_000, 55),
    'FURNA': ('RD_PM0801', 'Печи трубчатые', 'Печь трубчатая П-{n}', False, 900, 9_800_000, 60),
    'REACT': ('RD_PM0901', 'Реакторы', 'Реактор Р-{n}', False, 900, 7_200_000, 55),
    'VESSL': ('RD_PM1001', 'Ёмкости/Сепараторы', 'Ёмкость Е-{n}', False, 720, 620_000, 40),
    'TANK': ('RD_PM1101', 'Резервуары', 'Резервуар РВС-{n}', False, 1460, 2_400_000, 50),
    'VALVE_R': ('RD_PM1201', 'Клапаны регулирующие', 'Клапан регулирующий FV-{n}', False, 365, 95_000, 40),
    'VALVE_S': ('RD_PM1202', 'Задвижки запорные', 'Задвижка З-{n}', False, 540, 75_000, 35),
    'SENSOR': ('RD_PM1301', 'Датчики КИПиА', 'Датчик PT/TT/FT-{n}', False, 365, 45_000, 35),
    'SAFVLV': ('RD_PM1203', 'Клапаны предохранительные', 'ПК-{n}', False, 540, 120_000, 40),
    'TRANS': ('RD_PM1401', 'Трансформаторы', 'Трансформатор ТР-{n}', False, 1095, 1_600_000, 45),
    'CABLE': ('RD_PM1402', 'Кабельные линии', 'Кабельная линия КЛ-{n}', False, 730, 280_000, 35),
}

# Типовые «миксы» оборудования для разных типов установок (доли в %, должно быть ~100%)
UNIT_PROFILES = {
    'primary':   {'PUMP_C': 30, 'PUMP_P': 5, 'PUMP_S': 3, 'COMPR_C': 2, 'COMPR_P': 3, 'FAN_VAC': 4, 'MOTOR': 7,
                  'HEATX': 12, 'COLUM': 1, 'FURNA': 1, 'VESSL': 5, 'VALVE_R': 10, 'VALVE_S': 6, 'SENSOR': 8, 'SAFVLV': 3},
    'crack':     {'PUMP_C': 22, 'PUMP_P': 4, 'COMPR_C': 5, 'COMPR_P': 3, 'TURBN': 2, 'FAN_VAC': 4, 'MOTOR': 8,
                  'HEATX': 10, 'REACT': 3, 'COLUM': 2, 'FURNA': 2, 'VESSL': 5, 'VALVE_R': 13, 'VALVE_S': 6, 'SENSOR': 8, 'SAFVLV': 3},
    'coke':      {'PUMP_C': 20, 'PUMP_P': 7, 'COMPR_C': 3, 'COMPR_P': 3, 'FAN_VAC': 3, 'MOTOR': 8,
                  'HEATX': 10, 'REACT': 2, 'COLUM': 2, 'FURNA': 4, 'VESSL': 6, 'VALVE_R': 14, 'VALVE_S': 8, 'SENSOR': 7, 'SAFVLV': 3},
    'hydro':     {'PUMP_C': 28, 'PUMP_P': 4, 'COMPR_C': 5, 'COMPR_P': 4, 'FAN_VAC': 4, 'MOTOR': 7,
                  'HEATX': 12, 'REACT': 2, 'COLUM': 2, 'FURNA': 2, 'VESSL': 5, 'VALVE_R': 11, 'VALVE_S': 6, 'SENSOR': 7, 'SAFVLV': 1},
    'reform':    {'PUMP_C': 26, 'PUMP_P': 3, 'COMPR_C': 4, 'COMPR_P': 3, 'FAN_VAC': 4, 'MOTOR': 7,
                  'HEATX': 12, 'REACT': 3, 'COLUM': 2, 'FURNA': 2, 'VESSL': 5, 'VALVE_R': 12, 'VALVE_S': 6, 'SENSOR': 8, 'SAFVLV': 3},
    'small':     {'PUMP_C': 28, 'PUMP_P': 4, 'COMPR_P': 3, 'MOTOR': 8, 'FAN_VAC': 3,
                  'HEATX': 10, 'COLUM': 3, 'FURNA': 2, 'VESSL': 7, 'VALVE_R': 12, 'VALVE_S': 7, 'SENSOR': 10, 'SAFVLV': 3},
    'bitumen':   {'PUMP_C': 20, 'PUMP_P': 18, 'PUMP_S': 6, 'MOTOR': 7, 'FAN_VAC': 3,
                  'HEATX': 8, 'COLUM': 2, 'FURNA': 3, 'VESSL': 8, 'VALVE_R': 10, 'VALVE_S': 7, 'SENSOR': 6, 'SAFVLV': 2},
    'tsp':       {'PUMP_C': 25, 'PUMP_P': 8, 'MOTOR': 10,
                  'TANK': 18, 'VESSL': 5, 'VALVE_S': 14, 'VALVE_R': 8, 'SENSOR': 8, 'SAFVLV': 2, 'HEATX': 2},
    'utility':   {'PUMP_C': 18, 'COMPR_C': 5, 'COMPR_P': 4, 'FAN_VAC': 6, 'MOTOR': 10, 'TRANS': 5, 'CABLE': 4,
                  'HEATX': 8, 'VESSL': 8, 'TANK': 3, 'VALVE_R': 10, 'VALVE_S': 8, 'SENSOR': 8, 'SAFVLV': 3},
    'energy':    {'TURBN': 3, 'COMPR_C': 6, 'PUMP_C': 14, 'MOTOR': 10, 'TRANS': 6, 'CABLE': 5, 'FAN_VAC': 5,
                  'HEATX': 10, 'VESSL': 8, 'VALVE_R': 10, 'VALVE_S': 6, 'SENSOR': 12, 'SAFVLV': 5},
}

# Привязка установок к профилям оборудования
UNIT_PROFILE_MAP = {
    # Первичка
    'AV06': 'primary', 'AT06': 'primary', 'AV05': 'primary',
    'AVT1': 'primary', 'AVT5': 'primary', 'AVT6': 'primary', 'AVT4': 'primary', 'AT01': 'primary',
    'AVT2': 'primary', 'AVT3': 'primary', 'AVTU': 'primary',
    # Каталитический крекинг
    'KK01': 'crack', 'KK02': 'crack', 'KRKT': 'crack', 'TKRK': 'crack',
    # Коксование
    'UZK1': 'coke', 'UZKV': 'coke', 'UZKP': 'coke', 'VISB': 'coke',
    # Гидрокрекинг/гидроочистка
    'GKVG': 'hydro', 'GKRK': 'hydro', 'L246': 'hydro', 'L247': 'hydro', 'GOKR': 'hydro',
    'GO24': 'hydro', 'GDS8': 'hydro',
    # Риформинг / изомеризация
    'LG35': 'reform', 'LC35': 'reform', 'RIFB': 'reform', 'RIFK': 'reform', 'RIFP': 'reform',
    'PNEX': 'reform', 'IZMP': 'reform', 'R351': 'reform',
    # Небольшие установки / спец.
    'GFU1': 'small', 'GFU2': 'small', 'GF42': 'small', 'PS81': 'small', 'PVH2': 'small',
    'PARF': 'small', 'DEAS': 'small', 'DPAR': 'small', 'PPRI': 'small', 'SELO': 'small',
    'KM03': 'small', 'G43M': 'small', 'PRFP': 'small', 'PSER': 'small', 'GDAP': 'small',
    'KCA1': 'small', 'ASSB': 'small', 'DKSP': 'small', 'NTKR': 'small', 'ALKP': 'small',
    # Битумы
    'BIT1': 'bitumen', 'BIT2': 'bitumen', 'OKBT': 'bitumen', 'BITU': 'bitumen',
    # ТСП — товарно-сырьевое
    'TSP1': 'tsp', 'TSPV': 'tsp', 'TSPP': 'tsp', 'TSPU': 'tsp',
    # ОЗХ
    'OZH1': 'utility', 'OZHV': 'utility', 'OZHP': 'utility', 'OZHU': 'utility', 'FAKL': 'utility',
    # ГТУ-ТЭС / энергетика
    'GTU1': 'energy', 'GTUP': 'energy',
}

# ═══════════════════════════════════════════════════════════════════════════
# СПРАВОЧНИКИ: ПОЛЬЗОВАТЕЛИ, ПОДРЯДЧИКИ, ГРУППЫ, ВИДЫ РАБОТ, СТАТУСЫ
# ═══════════════════════════════════════════════════════════════════════════

# Русские фамилии для генерации ERNAM/AENAM в транслите SAP-стиля (9 знаков)
SURNAMES = [
    'IVANOV', 'PETROV', 'SIDOROV', 'SMIRNOV', 'KUZNECOV', 'POPOV', 'LEBEDEV', 'SOKOLOV',
    'KOZLOV', 'NOVIKOV', 'MOROZOV', 'PETROVSKY', 'VOLKOV', 'SOLOVYEV', 'VASILYEV',
    'ZAYCEV', 'PAVLOV', 'SEMENOV', 'GOLUBEV', 'VINOGRAD', 'BOGDANOV', 'VORONIN',
    'FEDOROV', 'MIKHAJLOV', 'BELYAEV', 'TARASOV', 'BELOV', 'KOMAROV', 'ORLOV',
    'KISELEV', 'MAKAROV', 'ANDREEV', 'KOVALEV', 'ILYIN', 'GUSEV', 'TITOV',
    'KUZMIN', 'KUDRYASHOV', 'BARANOV', 'NIKOLAEV', 'TIMOFEEV', 'FOMIN', 'CHERNOV',
    'DAVYDOV', 'ZHUKOV', 'KALININ', 'YAKOVLEV', 'LUKIN', 'MEDVEDEV', 'BORISOV',
    'SOBOLEV', 'KAPUSTIN', 'CHERKASOV', 'SHIRYAEV', 'BOGACHEV', 'LARIONOV',
]
INITIALS = ['AA', 'AV', 'AI', 'AM', 'AN', 'AS', 'DA', 'DV', 'DM', 'DS', 'EA', 'EV',
            'IA', 'IV', 'MA', 'MV', 'NI', 'NV', 'OA', 'OV', 'PI', 'PV', 'SA', 'SV',
            'TA', 'VA', 'VI', 'VL', 'VP', 'VS', 'YA']


def make_users(plant_code: str, count: int) -> list:
    """Пул ERNAM: фамилия в верхнем регистре + 2 инициала, усечённый до 12 символов."""
    users = []
    rng = random.Random(hash(plant_code) & 0xFFFFFFFF)
    for _ in range(count):
        s = rng.choice(SURNAMES)
        ini = rng.choice(INITIALS)
        u = (s + ini)[:12]
        if u not in users:
            users.append(u)
    return users


# Группы плановиков (INGPR, INGPR_TXT) — по 8-10 групп на завод
INGPR_GROUPS = [
    ('M01', 'Механики АВТ'),
    ('M02', 'Механики каталитики'),
    ('M03', 'Механики гидропроцессов'),
    ('M04', 'Механики масел'),
    ('M05', 'Механики битумов'),
    ('M06', 'Механики ТСП'),
    ('T01', 'Технологи первички'),
    ('T02', 'Технологи вторички'),
    ('K01', 'КИПиА-1'),
    ('K02', 'КИПиА-2'),
    ('E01', 'Электроцех'),
    ('ENG', 'Энергоцех'),
    ('OZH', 'Общезавод. хозяйство'),
    ('CRS', 'Подрядные работы'),
    ('REM', 'Ремонтное пр-во'),
]

# Рабочие места (GEWRK) — привязка к заводам через код
def gewrk_for_plant(plant_code: str, unit_code: str, ingpr: str) -> tuple:
    """Возвращает (код, название) рабочего места."""
    # Кодируем как 8 цифр: pp_uuu_ii (2+3+3)
    pidx = list(PLANTS.keys()).index(plant_code)
    uidx = abs(hash(unit_code)) % 900 + 100
    iidx = abs(hash(ingpr)) % 90 + 10
    code = f'{10 + pidx}{uidx:03d}{iidx:02d}0'
    names = {
        'M01': 'Подр. по ремонту технол. оборудования №1',
        'M02': 'Подр. по ремонту технол. оборудования №2',
        'M03': 'Подр. по ремонту технол. оборудования №3',
        'M04': 'Подр. по ремонту маслоблока',
        'M05': 'Подр. по ремонту битумов',
        'M06': 'Подр. по ремонту ТСП',
        'T01': 'Технол. служба первичной переработки',
        'T02': 'Технол. служба вторичной переработки',
        'K01': 'Служба КИПиА-1',
        'K02': 'Служба КИПиА-2',
        'E01': 'Электроцех',
        'ENG': 'Энергослужба',
        'OZH': 'Подр. общезаводского хозяйства',
        'CRS': 'Подр. подрядных работ',
        'REM': 'Ремонтно-механический цех',
    }
    return code, names.get(ingpr, 'Подр. ремонта')


# Виды заказов (AUART, AUART_TXT)
AUART_TYPES = [
    ('LK01', 'Предупредительное ТОРО', 0.58),       # плановое ППР
    ('LK02', 'Аварийное ТОРО',        0.16),        # аварийные
    ('LK03', 'Внеплановое ТОРО',      0.12),        # внеплановые
    ('LK04', 'Капитальный ремонт',    0.05),
    ('LK05', 'Диагностика',           0.05),
    ('LK06', 'Модернизация / Реконструкция', 0.04),
]

# Виды работ (ILART, ILART_TXT)
ILART_TYPES = {
    'LK01': [('REP', 'Ремонт ЕО'), ('MAIN', 'Техобслуживание'), ('INSP', 'Осмотр/Ревизия')],
    'LK02': [('REP', 'Ремонт ЕО'), ('EMER', 'Аварийный ремонт')],
    'LK03': [('REP', 'Ремонт ЕО'), ('UNPL', 'Внеплановая замена')],
    'LK04': [('CAP', 'Капитальный ремонт')],
    'LK05': [('DIAG', 'Диагностика'), ('INSP', 'Осмотр/Ревизия')],
    'LK06': [('MODER', 'Модернизация'), ('RECO', 'Реконструкция')],
}

# ABC-критичность (ABCKZ) — распределение
ABC_DIST = [
    ('A', 'Критично',        0.15),
    ('B', 'Важно',           0.30),
    ('C', 'Среднее',         0.30),
    ('D', 'Малая важность',  0.15),
    ('E', 'Не критично',     0.10),
]

# Группы сообщений (MSGRP)
MSGRP_TYPES = [
    'SM01', 'SM02', 'SM03', 'ZPRE', 'ZURG', 'Пусто',
]

# Статусы (ISTAT, ISTAT_TXT)
ISTAT_ORDER = [
    ('E0001', 'Внутреннее планирование'),
    ('I0002', 'Выпущено'),
    ('I0009', 'В работе'),
    ('I0045', 'Технически закрыто'),
    ('I0046', 'Закрыто'),
]

# Подрядчики: 5 крупных (ко всем заводам) + локальные
MAJOR_CONTRACTORS = [
    ('CR-LR',  'ООО "ЛУКОЙЛ-Ремстрой"'),
    ('CR-VNM', 'АО "Волгограднефтемаш"'),
    ('CR-UHM', 'АО "Уралхиммаш"'),
    ('CR-NHS', 'ООО "Нефтехимпромсервис"'),
    ('CR-RMN', 'ООО "Ремэнерго"'),
]
LOCAL_CONTRACTORS = {
    'NN': [
        ('CR-NNSC', 'ООО "Нижегородский сервисный центр"'),
        ('CR-VSM', 'ООО "Волгаспецмонтаж"'),
        ('CR-RTN', 'ООО "РемТехНН"'),
        ('CR-SPA', 'ООО "СпецПромАрматура"'),
    ],
    'VG': [
        ('CR-VES', 'ООО "Волга-Энерго-Сервис"'),
        ('CR-UNS', 'ООО "ЮгНефтеСервис"'),
        ('CR-STV', 'ООО "СТП-Волга"'),
    ],
    'PN': [
        ('CR-PNR', 'ООО "Пермнефтемашремонт"'),
        ('CR-KMS', 'ООО "Кама-Сервис"'),
        ('CR-UHR', 'ООО "УралХимРемонт"'),
        ('CR-PNK', 'ООО "Прикамье-НКТ"'),
    ],
    'UH': [
        ('CR-KSM', 'ООО "Коми-Спецмонтаж"'),
        ('CR-PCH', 'ООО "Печора-Сервис"'),
        ('CR-UTR', 'ООО "Ухта-ТехРемонт"'),
    ],
}

# Места нахождения (STORT / STORT_TXT) — пул
STORT_LIST = [
    ('S001', 'Территория 1-го тех. цеха'),
    ('S002', 'Территория 2-го тех. цеха'),
    ('S003', 'Территория 3-го тех. цеха'),
    ('S010', 'Резервуарный парк РП-1'),
    ('S011', 'Резервуарный парк РП-2'),
    ('S012', 'Резервуарный парк РП-3'),
    ('S020', 'Ж/д наливная эстакада'),
    ('S021', 'Ж/д сливная эстакада'),
    ('S030', 'Энергоблок'),
    ('S040', 'Компрессорная станция'),
    ('S050', 'Насосная-1'),
    ('S051', 'Насосная-2'),
    ('S052', 'Насосная-3'),
]

# Узлы оборудования (BAUTL)
BAUTL_LIST = [
    'N01-Рабочее колесо', 'N02-Вал', 'N03-Корпус',
    'N10-Подшипниковый узел', 'N11-Торцевое уплотнение', 'N12-Сальник',
    'N20-Электропривод', 'N21-Муфта', 'N22-Клиноремённая передача',
    'N30-Теплообменный пучок', 'N31-Крышка фронтальная', 'N32-Трубный пучок',
    'N40-Клапан всасывающий', 'N41-Клапан нагнетательный', 'N42-Поршневой узел',
    'N50-Запорная арматура', 'N51-Привод задвижки',
    'N60-Элемент КИПиА', 'N61-Регулятор',
    'N70-Змеевик печи', 'N71-Горелочное устройство', 'N72-Дымовая труба',
    'N80-Ротор', 'N81-Лопатки', 'N82-Диафрагма',
    'Не присвоено',
]

# USER4 — коды классификаторов работ
USER4_LIST = ['1', '2', '3', '4', '5', '0']

# Тексты заказов: конструктор «Действие + объект [+ деталь]»
ACTIONS_PLAN = [
    'ТО-1 по графику', 'ТО-2 по графику', 'ТО-3 по графику ППР',
    'Плановая ревизия', 'Диагностика', 'Ревизия состояния',
    'Плановое техобслуживание', 'Плановый осмотр',
    'Проверка параметров работы', 'Измерение вибрации',
    'Замена масла', 'Очистка',
]
ACTIONS_REPAIR = [
    'Замена подшипникового узла', 'Замена торцевого уплотнения',
    'Замена рабочего колеса', 'Замена вала', 'Балансировка ротора',
    'Ремонт корпуса', 'Восстановление футеровки', 'Очистка теплообменного пучка',
    'Восстановление защитного покрытия', 'Шлифовка вала',
    'Замена трубного пучка', 'Ремонт проточной части',
    'Восстановление клапанной группы', 'Замена сальникового уплотнения',
]
ACTIONS_EMER = [
    'Аварийный ремонт с заменой', 'Экстренный ремонт', 'Аварийная остановка + ремонт',
    'Ремонт по внеплановой остановке', 'Ремонт с разборкой',
    'Ликвидация течи', 'Устранение вибрации', 'Восстановление после срабатывания ПАЗ',
]
ACTIONS_DIAG = [
    'Вибродиагностика', 'Тепловизионный контроль', 'Ультразвуковая толщинометрия',
    'Вихретоковый контроль', 'Акустико-эмиссионный контроль', 'Рентгеновский контроль',
    'Гидравлические испытания', 'Пневматические испытания',
]
ACTIONS_CAP = [
    'Капитальный ремонт с полной разборкой', 'Капремонт с заменой ротора',
    'Капремонт с заменой проточной части', 'Капремонт теплообменника',
    'Капитальный ремонт печи', 'Капремонт с заменой трубного пучка',
]
ACTIONS_MOD = [
    'Модернизация с заменой на энергоэффективный', 'Реконструкция с заменой на современный',
    'Замена устаревшего оборудования', 'Установка системы автоматизации',
]


def make_order_text(auart: str, eq_name: str, rng: random.Random) -> str:
    pool = {
        'LK01': ACTIONS_PLAN + ACTIONS_REPAIR,
        'LK02': ACTIONS_EMER,
        'LK03': ACTIONS_REPAIR + ACTIONS_EMER,
        'LK04': ACTIONS_CAP,
        'LK05': ACTIONS_DIAG,
        'LK06': ACTIONS_MOD,
    }[auart]
    action = rng.choice(pool)
    # Извлекаем тег объекта ("Н-101", "К-301" и т.п.)
    text = f'{action} — {eq_name}'
    return text[:150]


# ═══════════════════════════════════════════════════════════════════════════
# СТОЛБЦЫ XLSX (55 колонок, как в EX_1111.XLSX)
# ═══════════════════════════════════════════════════════════════════════════

COLUMNS = [
    'BUKRS', 'BUKRS_TXT', 'AUFNR', 'AUFNR_TXT', 'ISTAT', 'ISTAT_TXT',
    'ERDAT', 'AEDAT', 'ERNAM', 'AENAM', 'BAUTL', 'MSGRP', 'USER4',
    'GSTRP', 'GLTRP', 'ZZFACTBEG', 'ZZFACTEND', 'ZZ_DEFNUM', 'ZZ_DOGNUM',
    'MAUFNR', 'MAUFNR_TXT', 'AUART', 'AUART_TXT', 'INBDT',
    'EQUNR', 'EQUNR_TXT', 'IWERK', 'IWERK_TXT', 'GEWRK', 'GEWRK_TXT',
    'ILART', 'ILART_TXT', 'STORT', 'STORT_TXT',
    'TPLNR8', 'TPLNR8_TXT', 'ABCKZ', 'ABCKZ_TXT',
    'PMCOALLP', 'PMCOALLF', 'PMCO001P', 'PMCO001F', 'PMCO008P', 'PMCO008F',
    'INGPR', 'INGPR_TXT', 'TPLNR', 'TPLNR_TXT', 'CLINT', 'CLINT_TXT',
    'AUFNR_OSN', 'DGP', 'AUSZT', 'AUSVN', 'AUSBS',
]

# ═══════════════════════════════════════════════════════════════════════════
# ОБОРУДОВАНИЕ
# ═══════════════════════════════════════════════════════════════════════════

def round_price(v: float) -> float:
    """Реалистичная, не круглая цена."""
    if v < 1000:
        return round(v, 2)
    # «Некрасивое» округление: случайные копейки
    cents = random.randint(0, 99) / 100
    return round(v, 0) + cents - (cents if random.random() < 0.15 else 0)


def pick_weighted(items_with_weights, rng: random.Random):
    """items_with_weights = [(item, weight), ...]"""
    total = sum(w for _, w in items_with_weights)
    r = rng.random() * total
    acc = 0
    for item, w in items_with_weights:
        acc += w
        if r <= acc:
            return item
    return items_with_weights[-1][0]


def make_equnr(plant_idx: int, seq: int) -> str:
    """Формирует 18-значный SAP EQUNR-код. Первые 3 — завод, остальные — последовательный № (15)."""
    return f'{101 + plant_idx:03d}{seq:015d}'


def gen_equipment_for_unit(plant_code: str, unit_code: str, unit_name: str,
                            orders_per_year_target: int, plant_idx: int, seq_start: int, rng: random.Random) -> tuple:
    """
    Генерирует список оборудования для установки.
    orders_per_year_target ≈ n_eq × 3 (средне 3 заказа/год на ЕО).
    Возвращает (list_of_equipment_dicts, next_seq).
    """
    profile_name = UNIT_PROFILE_MAP.get(unit_code, 'small')
    profile = UNIT_PROFILES[profile_name]

    # целевое число оборудования: среднее ~1.4 заказа/ЕО/год × 2.28 года ≈ 3 заказа/ЕО за период
    # orders_per_year_target / 1.4 → даёт нужное число ЕО, чтобы после 2.28 лет цикла получить цель
    target_n = max(15, min(2500, round(orders_per_year_target / 1.4)))
    # Распределяем по типам согласно профилю
    total_w = sum(profile.values())
    equipment = []
    seq = seq_start
    for eq_type, weight in profile.items():
        eq_class_code, eq_class_name, name_tmpl, is_dynamic, base_cycle, base_cost, plusminus = EQ_TYPES[eq_type]
        n = max(1, round(target_n * weight / total_w))
        for i in range(n):
            seq += 1
            equnr = make_equnr(plant_idx, seq)
            # Уникальный идентификатор по (завод, установка, позиция): префикс завода + номер
            # формат "N-NN01/123" — гарантирует уникальность между заводами и установками
            loc_n = f'{plant_code}{unit_code}-{100 + i:03d}'
            eq_name = name_tmpl.replace('{n}', loc_n)
            equipment.append({
                'equnr': equnr,
                'name': eq_name,
                'type': eq_type,
                'class_code': eq_class_code,
                'class_name': eq_class_name,
                'is_dynamic': is_dynamic,
                'base_cycle': base_cycle,
                'base_cost': base_cost,
                'plusminus': plusminus,
                'unit_code': unit_code,
                'unit_name': unit_name,
            })
    return equipment, seq


# ═══════════════════════════════════════════════════════════════════════════
# ПРОБЛЕМНЫЕ ОБЪЕКТЫ — ЖЁСТКО ЗАДАННЫЕ (турбины-бомбы + горячие точки)
# ═══════════════════════════════════════════════════════════════════════════

# 9 крупных турбин / центробежных компрессоров с дорогими цикличными ремонтами
TURBINE_BOMBS = [
    # (plant_code, unit_code, type, name, base_cycle_days, cost_min_M, cost_max_M)
    ('NN', 'KK01', 'COMPR_C', 'Турбокомпрессор К-301 (воздуходувка регенератора)', 250, 18, 55),
    ('NN', 'GTU1', 'TURBN',   'Турбина ТГУ-6 ГТУ-ТЭС',                             270, 25, 70),
    ('NN', 'GFU1', 'COMPR_C', 'Центробежный компрессор ЦК-501',                    330, 12, 38),
    ('VG', 'GKVG', 'COMPR_C', 'Турбокомпрессор К-2101 гидрокрекинга',              280, 22, 60),
    ('VG', 'GKVG', 'COMPR_C', 'Компрессор свежего водорода К-201',                 300, 14, 45),
    ('PN', 'KCA1', 'TURBN',   'Турбодетандер ТДА-1 КЦА',                           240, 20, 58),
    ('PN', 'GKRK', 'COMPR_C', 'Центробежный компрессор ЦК-2402',                   330, 18, 52),
    ('PN', 'GTUP', 'TURBN',   'Турбогенератор ТГ-200',                             270, 28, 75),
    ('UH', 'VISB', 'COMPR_C', 'Центробежный компрессор К-101 висбрекинга',         360, 10, 32),
]

# 16 «горячих точек» — частые дешевле ремонты (1-2 раза в месяц)
HOT_SPOTS = [
    # (plant, unit, type, name, min_cycle, max_cycle, cost_min, cost_max)
    ('NN', 'KK01', 'VALVE_R', 'Шиберная заслонка регенератора КК-1 SV-101', 25, 40, 1_200_000, 3_500_000),
    ('NN', 'UZK1', 'HEATX',   'Змеевик печи П-101/1 УЗК ЗМ-101/1',          20, 35,   800_000, 2_200_000),
    ('NN', 'UZK1', 'PUMP_P',  'Насос откачки кокса Н-401 УЗК',               14, 22,   400_000, 1_100_000),
    ('NN', 'KK02', 'VALVE_R', 'Дроссельный клапан катализатора FV-205 КК-2', 28, 35,   600_000, 1_800_000),
    ('NN', 'KK01', 'VALVE_R', 'Горелки регенератора КК-1 Г-301…306',         18, 26,   300_000,   900_000),
    ('VG', 'GKVG', 'HEATX',   'Теплообменник Т-201/1 гидрокрекинга',         30, 45, 1_800_000, 4_500_000),
    ('VG', 'RIFB', 'PUMP_C',  'Сульфидная мешалка М-301 производства серы',  20, 30,   500_000, 1_400_000),
    ('VG', 'AVT1', 'VALVE_R', 'Горелки печи П-501 ЭЛОУ-АВТ-1',               18, 25,   300_000,   800_000),
    ('VG', 'AVT6', 'PUMP_P',  'Насос перегонки мазута Н-6101',               22, 32,   600_000, 1_500_000),
    ('PN', 'KRKT', 'FAN_VAC', 'Воздуходув ВД-1 регенератора КК',             25, 35, 1_500_000, 4_000_000),
    ('PN', 'KCA1', 'VALVE_R', 'Быстродействующие клапаны КЦА КВ-01…40',      11, 18,   200_000,   700_000),
    ('PN', 'SELO', 'PUMP_C',  'Насос фурфуроловой очистки Н-Ф-201',          20, 28,   500_000, 1_300_000),
    ('PN', 'KRKT', 'REACT',   'Реакторный узел КК риска Р-101',              25, 35, 2_500_000, 6_500_000),
    ('UH', 'VISB', 'HEATX',   'Змеевик печи висбрекинга П-101',              25, 38, 1_200_000, 3_200_000),
    ('UH', 'BITU', 'PUMP_P',  'Насос гудрона Н-21/1 битумной',               14, 20,   300_000,   900_000),
    ('UH', 'BITU', 'VALVE_R', 'Клапаны БНД-битумной КЛ-201…212',             15, 28,   200_000,   500_000),
]


# ═══════════════════════════════════════════════════════════════════════════
# ГЕНЕРАЦИЯ ЗАКАЗОВ
# ═══════════════════════════════════════════════════════════════════════════

def random_workday_datetime(day: dt.date, rng: random.Random) -> dt.datetime:
    """Дата создания в рабочее время буднего дня 8:30–17:45."""
    d = day
    # если суббота/воскресенье — сдвигаем к понедельнику
    while d.weekday() >= 5:
        d = d + dt.timedelta(days=1)
    h = rng.randint(8, 17)
    if h == 8:
        m = rng.randint(30, 59)
    elif h == 17:
        m = rng.randint(0, 45)
    else:
        m = rng.randint(0, 59)
    s = rng.randint(0, 59)
    return dt.datetime(d.year, d.month, d.day, h, m, s)


def gen_history(order_type: str, plan_start: dt.datetime, plan_end: dt.datetime,
                is_unfinished: bool, with_returns: int, force_dec_close: bool, rng: random.Random,
                creator: str, last_editor: str) -> list:
    """
    Генерирует список кортежей (ISTAT, ISTAT_TXT, AEDAT, AENAM) — история статусов заказа.
    Первый — E0001 (ERDAT=первый AEDAT), последний — I0046 либо I0002/E0001 (если unfinished).
    with_returns — сколько повторов статусов добавить (для NEW-10).
    force_dec_close — принудительно закрыть в декабре (для NEW-9).
    """
    history = []
    # Рассчитываем базовые даты истории на основе плановых дат
    duration = (plan_end - plan_start).total_seconds()
    if duration <= 0:
        duration = 86400 * 3

    # ETAP1: создание (E0001)
    t0 = plan_start - dt.timedelta(days=rng.randint(5, 30),
                                    hours=rng.randint(0, 9),
                                    minutes=rng.randint(0, 59))
    if t0 < PERIOD_START:
        t0 = PERIOD_START + dt.timedelta(days=rng.randint(1, 5))
    history.append(('E0001', 'Внутреннее планирование', t0, creator))

    if is_unfinished:
        # Либо остаётся в E0001, либо I0002 (выпущено, но не закрыто)
        if rng.random() < 0.35:
            t1 = t0 + dt.timedelta(days=rng.randint(3, 15))
            history.append(('I0002', 'Выпущено', t1, last_editor))
        return history

    # I0002 — выпущено
    t1 = t0 + dt.timedelta(days=rng.randint(2, 15),
                            hours=rng.randint(0, 23),
                            minutes=rng.randint(0, 59))
    history.append(('I0002', 'Выпущено', t1, last_editor))

    # I0009 — в работе
    t2 = plan_start + dt.timedelta(hours=rng.randint(-12, 36),
                                    minutes=rng.randint(0, 59))
    if t2 < t1:
        t2 = t1 + dt.timedelta(hours=4)
    history.append(('I0009', 'В работе', t2, last_editor))

    # Возвраты (NEW-10)
    cur_t = t2
    for _ in range(with_returns):
        cur_t = cur_t + dt.timedelta(days=rng.randint(1, 6),
                                      hours=rng.randint(0, 23))
        history.append(('I0002', 'Выпущено', cur_t, last_editor))
        cur_t = cur_t + dt.timedelta(days=rng.randint(2, 8),
                                      hours=rng.randint(0, 23))
        history.append(('I0009', 'В работе', cur_t, last_editor))

    # I0045 — технически закрыто
    t3 = plan_end + dt.timedelta(hours=rng.randint(-12, 48),
                                  minutes=rng.randint(0, 59))
    if t3 < cur_t:
        t3 = cur_t + dt.timedelta(days=rng.randint(1, 5))
    history.append(('I0045', 'Технически закрыто', t3, last_editor))

    # I0046 — закрыто
    if force_dec_close:
        # закрыть в декабре того же или следующего года
        close_year = t3.year
        close_month = 12
        close_day = rng.randint(5, 30)
        t4 = dt.datetime(close_year, close_month, close_day,
                         rng.randint(9, 17), rng.randint(0, 59), rng.randint(0, 59))
        if t4 < t3:
            t4 = dt.datetime(close_year + 1, 12, close_day,
                             rng.randint(9, 17), rng.randint(0, 59), rng.randint(0, 59))
    else:
        t4 = t3 + dt.timedelta(days=rng.randint(1, 21),
                                hours=rng.randint(0, 23),
                                minutes=rng.randint(0, 59))
    history.append(('I0046', 'Закрыто', t4, last_editor))

    # Отсечь если всё ещё в будущем
    final = []
    for s_code, s_txt, tt, user in history:
        if tt > PERIOD_END:
            break
        final.append((s_code, s_txt, tt, user))
    # Если вышло пусто — вернём хотя бы создание
    if not final:
        final = [history[0]]
    return final


def gen_order_cost(eq: dict, auart: str, erdat: dt.datetime, rng: random.Random,
                    force_overrun: bool = False, is_anomaly: bool = False,
                    escalation_factor: float = 1.0, fixed_cost_range: tuple = None) -> tuple:
    """
    Возвращает (plan_n, fact_n, plan_t, fact_t) — плановые/фактические затраты и трудозатраты.
    """
    base_cost = eq['base_cost']
    pm = eq['plusminus'] / 100
    inf = infl_factor(erdat)

    # Множитель по типу работ
    mult = {
        'LK01': 1.0,     # плановое
        'LK02': 1.8,     # аварийное — дороже
        'LK03': 1.3,     # внеплановое
        'LK04': 3.5,     # капремонт
        'LK05': 0.25,    # диагностика
        'LK06': 4.0,     # модернизация
    }[auart]

    if fixed_cost_range is not None:
        plan_n = rng.uniform(fixed_cost_range[0], fixed_cost_range[1]) * inf
    else:
        plan_n = base_cost * mult * inf * rng.uniform(1 - pm, 1 + pm) * escalation_factor

    # Фактическая стоимость
    if force_overrun:
        # Гарантированное превышение на 25-150%
        overrun = rng.uniform(1.25, 2.50)
        fact_n = plan_n * overrun
    elif is_anomaly:
        # Аномалия: Fact в 1.5-4 раза больше медианы (plan_n)
        fact_n = plan_n * rng.uniform(1.55, 4.0)
    else:
        # Нормальное: ±15% от плана, небольшая тенденция к занижению факта
        fact_n = plan_n * rng.uniform(0.85, 1.14)

    # Трудозатраты (часы)
    hours_mult = {
        'LK01': 1.0, 'LK02': 2.2, 'LK03': 1.5, 'LK04': 5.0, 'LK05': 0.4, 'LK06': 6.0,
    }[auart]
    plan_t = max(1, round(plan_n / 3500 * hours_mult))
    fact_t = max(1, round(fact_n / 3500 * hours_mult))

    return round(plan_n, 2), round(fact_n, 2), float(plan_t), float(fact_t)


# ═══════════════════════════════════════════════════════════════════════════
# ГЕНЕРАЦИЯ СОБЫТИЙ ДЛЯ ЕО
# ═══════════════════════════════════════════════════════════════════════════

def gen_events_for_eq(eq: dict, is_problematic: bool, is_hotspot: bool,
                      hotspot_cycle_range: tuple, is_turbine_bomb: bool,
                      turbine_cycle: int, rng: random.Random) -> list:
    """Возвращает [(дата, AUART_code, special_flag), ...] — событий для одного ЕО."""
    events = []
    cycle = eq['base_cycle']
    if is_turbine_bomb:
        cycle = turbine_cycle
    elif is_hotspot:
        cycle = rng.randint(hotspot_cycle_range[0], hotspot_cycle_range[1])
    elif is_problematic and eq['is_dynamic']:
        # Проблемное: цикл в 1.8-2.8 раза короче
        cycle = int(cycle / rng.uniform(1.8, 2.8))
    cycle = max(8, cycle)

    # Первое событие — случайное смещение
    t = PERIOD_START + dt.timedelta(days=rng.randint(5, max(6, int(cycle * 0.9))))
    idx = 0
    while t < PERIOD_END:
        # Определяем тип работ
        rnd = rng.random()
        if is_turbine_bomb:
            auart = 'LK04' if rnd < 0.30 else ('LK02' if rnd < 0.85 else 'LK05')
        elif is_hotspot:
            if rnd < 0.55:
                auart = 'LK02'
            elif rnd < 0.80:
                auart = 'LK03'
            else:
                auart = 'LK01'
        elif is_problematic and eq['is_dynamic']:
            if rnd < 0.25:
                auart = 'LK02'
            elif rnd < 0.50:
                auart = 'LK03'
            elif rnd < 0.92:
                auart = 'LK01'
            else:
                auart = 'LK05'
        else:
            # Обычное оборудование
            if rnd < 0.04:
                auart = 'LK02'
            elif rnd < 0.11:
                auart = 'LK03'
            elif rnd < 0.14:
                auart = 'LK05'
            elif rnd < 0.15:
                auart = 'LK04'
            elif rnd < 0.155:
                auart = 'LK06'
            else:
                auart = 'LK01'
        events.append((t, auart, idx))
        # Джиттер следующего интервала
        jitter = rng.uniform(0.70, 1.45)
        t = t + dt.timedelta(days=max(5, int(cycle * jitter)),
                              hours=rng.randint(0, 23),
                              minutes=rng.randint(0, 59))
        idx += 1
    return events


# ═══════════════════════════════════════════════════════════════════════════
# ОСНОВНОЙ ЦИКЛ ГЕНЕРАЦИИ
# ═══════════════════════════════════════════════════════════════════════════

def run_generation():
    """Главная функция генерации."""
    print(f'[INIT] Открываем файл для записи: {OUT_PATH}')
    wb = Workbook(write_only=True)
    ws = wb.create_sheet('Sheet1')
    ws.append(COLUMNS)

    # Агрегированные счётчики для статистики
    stats = {
        'orders_total': 0, 'rows_total': 0, 'equipment_total': 0,
        'by_plant': defaultdict(lambda: {'orders': 0, 'rows': 0, 'eq': 0,
                                          'c1m1': 0, 'c1m6': 0, 'c1m9': 0, 'c2m2': 0,
                                          'new9': 0, 'new10': 0, 'cost_plan': 0.0,
                                          'cost_fact': 0.0, 'cost_saved': 0.0}),
    }

    # Глобальный AUFNR-счётчик (SAP-формат 18 цифр)
    aufnr_counter = 18_000_000_0000

    # Медианы по ТМ (для метода C1-M6) — сначала собираем все стоимости, потом добавим аномалии
    # Но делаем одним проходом: используем enumerate по установкам, для каждой аккумулируем
    # стоимости плановых заказов и затем выборочно создаём аномалии.

    global_eq_seq = 0

    for plant_idx, (plant_code, plant) in enumerate(PLANTS.items()):
        plant_rng = random.Random(hash(plant_code) & 0xFFFFFFFF)
        users = make_users(plant_code, 40)
        contractors = MAJOR_CONTRACTORS + LOCAL_CONTRACTORS[plant_code]

        # Нормализация весов установок под целевую сумму
        units = PLANT_UNITS[plant_code]
        total_weight = sum(u[4] for u in units)
        norm = plant['orders_per_year'] / total_weight

        print(f'\n[{plant_code}] {plant["iwerk_txt"]}: цель={plant["orders_per_year"]}/год '
              f'(множитель={norm:.3f})')

        for prod_code, shop_code, unit_code, unit_name, weight in units:
            unit_target_year = weight * norm
            unit_rng = random.Random(hash((plant_code, unit_code)) & 0xFFFFFFFF)

            # Генерируем оборудование
            equipment, global_eq_seq = gen_equipment_for_unit(
                plant_code, unit_code, unit_name, int(unit_target_year),
                plant_idx, global_eq_seq, unit_rng)

            # Помечаем 30% динамического как "проблемное"
            dynamic_eq = [e for e in equipment if e['is_dynamic']]
            n_prob = int(len(dynamic_eq) * 0.30)
            unit_rng.shuffle(dynamic_eq)
            problematic_ids = set(id(e) for e in dynamic_eq[:n_prob])

            stats['equipment_total'] += len(equipment)
            stats['by_plant'][plant_code]['eq'] += len(equipment)

            # Иерархия ТМ для установки
            tplnr8 = f'{plant_code}{prod_code}.{unit_code}'
            tplnr8_txt = unit_name
            prod_txt = PRODUCTIONS[plant_code][prod_code]
            shop_txt = SHOPS.get(shop_code, 'Цех')

            # Пути подрядчиков: дорогие работы — крупные, мелкие — локальные
            def pick_contractor(auart: str, cost: float) -> tuple:
                if cost > 5_000_000 or auart in ('LK04', 'LK06'):
                    return unit_rng.choice(MAJOR_CONTRACTORS)
                if unit_rng.random() < 0.35:
                    return unit_rng.choice(MAJOR_CONTRACTORS)
                return unit_rng.choice(LOCAL_CONTRACTORS[plant_code])

            # Определяем назначенные на эту установку турбины-бомбы и горячие точки
            turbine_specs_here = [tb for tb in TURBINE_BOMBS if tb[0] == plant_code and tb[1] == unit_code]
            hotspot_specs_here = [hs for hs in HOT_SPOTS if hs[0] == plant_code and hs[1] == unit_code]

            # Подготовим специальные ЕО (добавляем их к пулу, если ещё нет аналогичных)
            special_equipment = []
            for tb in turbine_specs_here:
                _, _, typ, name, cycle, cmin, cmax = tb
                eq_cls = EQ_TYPES[typ]
                global_eq_seq += 1
                special_equipment.append({
                    'equnr': make_equnr(plant_idx, global_eq_seq),
                    'name': name,
                    'type': typ,
                    'class_code': eq_cls[0], 'class_name': eq_cls[1],
                    'is_dynamic': True,
                    'base_cycle': cycle,
                    'base_cost': (cmin + cmax) / 2 * 1_000_000,
                    'plusminus': 40,
                    'unit_code': unit_code, 'unit_name': unit_name,
                    '__is_turbine_bomb': True,
                    '__turbine_cycle': cycle,
                    '__cost_range': (cmin * 1_000_000, cmax * 1_000_000),
                })
            for hs in hotspot_specs_here:
                _, _, typ, name, mcy, xcy, cmin, cmax = hs
                eq_cls = EQ_TYPES[typ]
                global_eq_seq += 1
                special_equipment.append({
                    'equnr': make_equnr(plant_idx, global_eq_seq),
                    'name': name,
                    'type': typ,
                    'class_code': eq_cls[0], 'class_name': eq_cls[1],
                    'is_dynamic': True,
                    'base_cycle': (mcy + xcy) // 2,
                    'base_cost': (cmin + cmax) / 2,
                    'plusminus': 50,
                    'unit_code': unit_code, 'unit_name': unit_name,
                    '__is_hotspot': True,
                    '__hotspot_range': (mcy, xcy),
                    '__cost_range': (cmin, cmax),
                })
            all_equipment = equipment + special_equipment

            # Собираем все события, группируем по (плановой) медиане по ТМ
            # Для упрощения: считаем медиану по установке (TPLNR8), применяем метод C1-M6 выборочно
            unit_plan_costs = []  # для аномалий C1-M6
            unit_events = []  # каждый: (eq, t, auart, flags)

            for eq in all_equipment:
                is_tb = eq.get('__is_turbine_bomb', False)
                is_hs = eq.get('__is_hotspot', False)
                is_prob = id(eq) in problematic_ids
                events = gen_events_for_eq(
                    eq, is_prob, is_hs,
                    eq.get('__hotspot_range', (30, 60)),
                    is_tb, eq.get('__turbine_cycle', 240),
                    unit_rng)
                for (t, auart, idx) in events:
                    unit_events.append({
                        'eq': eq, 't': t, 'auart': auart, 'idx': idx,
                        'is_tb': is_tb, 'is_hs': is_hs, 'is_prob': is_prob,
                    })

            # Разберём события — расставим флаги для каждого метода
            # 1. C1-M1: форсируем перерасход ~2% заказов (случайно выбранные)
            # 2. C1-M6: аномалия ТМ ~1.5%
            # 3. C1-M9: незавершённые ~1.2% (E0001/I0002 и GLTRP в прошлом)
            # 4. NEW-9: декабрьское закрытие ~2%
            # 5. NEW-10: возвраты статусов ~1%
            n_evt = len(unit_events)
            idx_pool = list(range(n_evt))
            unit_rng.shuffle(idx_pool)

            flags_m1 = set(idx_pool[:int(n_evt * 0.015)])           # C1-M1 (дополнительно к естественным)
            flags_m6 = set(idx_pool[int(n_evt * 0.015):int(n_evt * 0.030)])  # C1-M6
            flags_m9 = set(idx_pool[int(n_evt * 0.030):int(n_evt * 0.042)])  # C1-M9
            flags_n9 = set(idx_pool[int(n_evt * 0.042):int(n_evt * 0.062)])  # NEW-9
            flags_n10 = set(idx_pool[int(n_evt * 0.062):int(n_evt * 0.072)]) # NEW-10

            # Пропуски (5%) — в несущественных полях
            flags_gap = set(idx_pool[int(n_evt * 0.90):])  # последние 10%, из них по 20-50% каждый пропуск

            # --- Генерация заказов ---
            for ev_idx, ev in enumerate(unit_events):
                eq = ev['eq']
                t_create = ev['t']
                auart = ev['auart']

                # AUART_TXT
                auart_txt = next(a[1] for a in AUART_TYPES if a[0] == auart)

                # Выбор ABCKZ
                # Для критического оборудования (турбины-бомбы, горячие точки) — более высокая критичность
                if ev['is_tb']:
                    abc_code, abc_txt = 'A', 'Критично'
                elif ev['is_hs']:
                    abc_code, abc_txt = unit_rng.choice([('A', 'Критично'), ('B', 'Важно')])
                elif ev['is_prob']:
                    abc_code, abc_txt = pick_weighted(
                        [(('A', 'Критично'), 0.25), (('B', 'Важно'), 0.45),
                         (('C', 'Среднее'), 0.25), (('D', 'Малая важность'), 0.05)], unit_rng)
                else:
                    abc_code, abc_txt = pick_weighted(
                        [((a[0], a[1]), a[2]) for a in ABC_DIST], unit_rng)

                # Группа плановиков
                # Привязка INGPR к типу работы
                if auart in ('LK04', 'LK06'):
                    ingpr, ingpr_txt = unit_rng.choice([g for g in INGPR_GROUPS if g[0].startswith('M')])
                elif auart == 'LK05':
                    ingpr, ingpr_txt = unit_rng.choice([g for g in INGPR_GROUPS if g[0].startswith(('T', 'K'))])
                else:
                    ingpr, ingpr_txt = unit_rng.choice(INGPR_GROUPS)

                # Рабочее место
                gewrk, gewrk_txt = gewrk_for_plant(plant_code, unit_code, ingpr)

                # Плановые даты
                plan_duration_days = max(1, int({
                    'LK01': 6, 'LK02': 4, 'LK03': 8, 'LK04': 35, 'LK05': 3, 'LK06': 55,
                }[auart] * unit_rng.uniform(0.5, 1.8)))
                plan_start_dt = t_create + dt.timedelta(days=unit_rng.randint(3, 20),
                                                         hours=0, minutes=0)
                plan_end_dt = plan_start_dt + dt.timedelta(days=plan_duration_days)

                # C1-M9: незавершённые — ставим GLTRP в прошлое (уже > 6 мес. до сегодня)
                is_unfinished = ev_idx in flags_m9
                if is_unfinished:
                    # Сдвигаем GLTRP как минимум на 180 дней назад от сегодня
                    plan_end_dt = PERIOD_END - dt.timedelta(days=unit_rng.randint(200, 600))
                    if plan_end_dt <= plan_start_dt:
                        plan_start_dt = plan_end_dt - dt.timedelta(days=plan_duration_days)
                    t_create = plan_start_dt - dt.timedelta(days=unit_rng.randint(10, 25))

                # Стоимость
                force_overrun = ev_idx in flags_m1
                is_anomaly = ev_idx in flags_m6
                esc = 1.0
                fixed_range = None

                # Специальные флаги из ЕО
                if ev['is_tb'] or ev['is_hs']:
                    fixed_range = eq['__cost_range']
                    # эскалация по порядку
                    esc = 1.0 + ev['idx'] * 0.12

                plan_n, fact_n, plan_t, fact_t = gen_order_cost(
                    eq, auart, t_create, unit_rng,
                    force_overrun=force_overrun, is_anomaly=is_anomaly,
                    escalation_factor=esc, fixed_cost_range=fixed_range)

                unit_plan_costs.append(plan_n)

                # Для аварийных бомб — факт всегда превышает
                if ev['is_tb']:
                    fact_n = plan_n * unit_rng.uniform(1.15, 1.40)
                    fact_t = plan_t * unit_rng.uniform(1.10, 1.30)

                # Дата закрытия: для NEW-9 — декабрь
                force_dec = ev_idx in flags_n9
                # Возвраты статусов: для NEW-10
                returns = 3 if ev_idx in flags_n10 else (1 if unit_rng.random() < 0.06 else 0)

                # Выбор пользователей
                creator = unit_rng.choice(users)
                last_editor = unit_rng.choice(users)

                # История статусов
                history = gen_history(auart, plan_start_dt, plan_end_dt,
                                       is_unfinished, returns, force_dec, unit_rng,
                                       creator, last_editor)

                # ILART
                ilart, ilart_txt = unit_rng.choice(ILART_TYPES[auart])

                # Подрядчик
                contr = pick_contractor(auart, plan_n)

                # Дефектная ведомость для аварийных
                has_defect = auart in ('LK02', 'LK03') and unit_rng.random() < 0.7
                zz_defnum = f'ДВ-{t_create.year}/{unit_rng.randint(1000, 9999)}' if has_defect else 'Не присвоено'
                zz_dognum = f'{contr[0]}/{t_create.year}-{unit_rng.randint(100, 9999):04d}'

                # Дефекты/узел
                bautl = unit_rng.choice(BAUTL_LIST)
                msgrp = unit_rng.choice(MSGRP_TYPES) if has_defect else 'Пусто'
                user4 = unit_rng.choice(USER4_LIST)

                # Местоположение
                stort, stort_txt = unit_rng.choice(STORT_LIST)

                # Фактические даты (для закрытых)
                fact_beg = EPOCH_ZERO
                fact_end = EPOCH_ZERO
                if not is_unfinished and len(history) >= 3:
                    # Берём из истории
                    fact_beg_dt = None
                    fact_end_dt = None
                    for st, _, tt, _ in history:
                        if st == 'I0009' and fact_beg_dt is None:
                            fact_beg_dt = tt
                        if st == 'I0045':
                            fact_end_dt = tt
                    if fact_beg_dt:
                        fact_beg = iso_z(fact_beg_dt)
                    if fact_end_dt:
                        fact_end = iso_z(fact_end_dt)

                # AUSVN / AUSBS (простой оборудования — даты сообщения)
                ausvn = EPOCH_ZERO
                ausbs = EPOCH_ZERO
                auszt = 0
                if auart in ('LK02', 'LK03') and not is_unfinished:
                    ausvn = iso_z(plan_start_dt - dt.timedelta(days=unit_rng.randint(1, 5)))
                    if fact_end != EPOCH_ZERO:
                        ausbs = fact_end
                    # Продолжительность простоя в секундах
                    auszt = unit_rng.randint(2, 72) * 3600

                # DGP — текущая балансовая стоимость
                dgp = round(eq['base_cost'] * unit_rng.uniform(2.5, 12.0), 2)
                inbdt = iso_z(dt.datetime(unit_rng.randint(1990, 2015),
                                           unit_rng.randint(1, 12),
                                           unit_rng.randint(1, 28)))

                # Пропуски в несущественных полях (5%-ный «шум»)
                if ev_idx in flags_gap:
                    gap_roll = unit_rng.random()
                    if gap_roll < 0.25:
                        stort, stort_txt = 'Не присвое', 'Не присвоено'
                    elif gap_roll < 0.45:
                        bautl = 'Не присвоено'
                    elif gap_roll < 0.60:
                        msgrp = 'Пусто'
                    elif gap_roll < 0.75:
                        zz_dognum = 'Не присвоено'
                    elif gap_roll < 0.85:
                        user4 = '0'
                    else:
                        zz_defnum = 'Не присвоено'

                # AUFNR
                aufnr = f'{aufnr_counter}'
                aufnr_counter += 1

                erdat = history[0][2]
                order_text = make_order_text(auart, eq['name'], unit_rng)

                # NEW-9: для force_dec - явно ставим ZZFACTEND в декабрь + короткая фактическая длительность
                if not is_unfinished and len(history) >= 4:
                    # Перезаписываем t3 (I0045) если нужен декабрь
                    last_tech_close_idx = next((i for i, h in enumerate(history) if h[0] == 'I0045'), None)
                    first_work_idx = next((i for i, h in enumerate(history) if h[0] == 'I0009'), None)
                    if (ev_idx in flags_n9 and last_tech_close_idx is not None and first_work_idx is not None):
                        plan_dur_days = max(1, (plan_end_dt - plan_start_dt).days)
                        fact_dur_short = max(1, int(plan_dur_days * unit_rng.uniform(0.15, 0.42)))
                        t_work = history[first_work_idx][2]
                        year = t_work.year
                        # Если t_work после ноября, переносим в декабрь того же года; иначе в декабрь t_work.year
                        t_close_dec = dt.datetime(year, 12, unit_rng.randint(5, 28),
                                                   unit_rng.randint(9, 17), unit_rng.randint(0, 59), 0)
                        if t_close_dec <= t_work:
                            t_close_dec = dt.datetime(year + 1, 12, unit_rng.randint(5, 28),
                                                       unit_rng.randint(9, 17), unit_rng.randint(0, 59), 0)
                        if t_close_dec > PERIOD_END:
                            t_close_dec = dt.datetime(PERIOD_END.year, 12, unit_rng.randint(5, 14),
                                                       10, 0, 0)
                        # Сдвинем t_work чтобы fact_dur был коротким
                        new_work = t_close_dec - dt.timedelta(days=fact_dur_short,
                                                                hours=unit_rng.randint(0, 23))
                        # Обновим историю
                        h = list(history[first_work_idx])
                        h[2] = new_work
                        history[first_work_idx] = tuple(h)
                        h2 = list(history[last_tech_close_idx])
                        h2[2] = t_close_dec
                        history[last_tech_close_idx] = tuple(h2)
                        # Также обновим I0046 (если есть, после I0045)
                        if last_tech_close_idx + 1 < len(history):
                            h3 = list(history[last_tech_close_idx + 1])
                            h3[2] = t_close_dec + dt.timedelta(days=unit_rng.randint(1, 10))
                            history[last_tech_close_idx + 1] = tuple(h3)

                # TPLNR привязан к EQUNR (одно физич. место = одна ТМ)
                tm_hash = abs(hash(eq['equnr'])) % 999 + 1
                tm_code = f'{plant_code}{prod_code}.{unit_code}.{eq["type"][:2]}{tm_hash:03d}'
                tm_txt = f'ТМ {eq["name"]}'

                for st_code, st_txt, aedat_dt, aenam in history:
                    row = [
                        plant['bukrs'],               # BUKRS
                        plant['bukrs_txt'],           # BUKRS_TXT
                        aufnr,                        # AUFNR
                        order_text,                   # AUFNR_TXT
                        st_code,                      # ISTAT
                        st_txt,                       # ISTAT_TXT
                        iso_z(erdat),                 # ERDAT
                        iso_z(aedat_dt),              # AEDAT
                        creator,                      # ERNAM
                        aenam,                        # AENAM
                        bautl,                        # BAUTL
                        msgrp,                        # MSGRP
                        user4,                        # USER4
                        iso_z(plan_start_dt.replace(hour=0, minute=0, second=0)),  # GSTRP
                        iso_z(plan_end_dt.replace(hour=0, minute=0, second=0)),    # GLTRP
                        fact_beg,                     # ZZFACTBEG
                        fact_end,                     # ZZFACTEND
                        zz_defnum,                    # ZZ_DEFNUM
                        zz_dognum,                    # ZZ_DOGNUM
                        'Не присвоено',               # MAUFNR
                        'Не присвоено',               # MAUFNR_TXT
                        auart,                        # AUART
                        auart_txt,                    # AUART_TXT
                        inbdt,                        # INBDT
                        eq['equnr'],                  # EQUNR
                        eq['name'],                   # EQUNR_TXT
                        plant['iwerk'],               # IWERK
                        plant['iwerk_txt'],           # IWERK_TXT
                        gewrk,                        # GEWRK
                        gewrk_txt,                    # GEWRK_TXT
                        ilart,                        # ILART
                        ilart_txt,                    # ILART_TXT
                        stort,                        # STORT
                        stort_txt,                    # STORT_TXT
                        tplnr8,                       # TPLNR8
                        tplnr8_txt,                   # TPLNR8_TXT
                        abc_code,                     # ABCKZ
                        abc_txt,                      # ABCKZ_TXT
                        plan_n,                       # PMCOALLP
                        fact_n,                       # PMCOALLF
                        plan_n,                       # PMCO001P
                        fact_n,                       # PMCO001F
                        plan_t,                       # PMCO008P
                        fact_t,                       # PMCO008F
                        ingpr,                        # INGPR
                        ingpr_txt,                    # INGPR_TXT
                        tm_code,                      # TPLNR
                        tm_txt,                       # TPLNR_TXT
                        eq['class_code'],             # CLINT
                        eq['class_name'],             # CLINT_TXT
                        '0',                          # AUFNR_OSN
                        dgp,                          # DGP
                        auszt,                        # AUSZT
                        ausvn,                        # AUSVN
                        ausbs,                        # AUSBS
                    ]
                    ws.append(row)
                    stats['rows_total'] += 1
                    stats['by_plant'][plant_code]['rows'] += 1

                # Учёт по методам
                stats['orders_total'] += 1
                p = stats['by_plant'][plant_code]
                p['orders'] += 1
                p['cost_plan'] += plan_n
                p['cost_fact'] += fact_n
                if force_overrun or (fact_n > plan_n * 1.20):
                    p['c1m1'] += 1
                    p['cost_saved'] += max(0, fact_n - plan_n * 1.20)
                if is_anomaly:
                    p['c1m6'] += 1
                if is_unfinished:
                    p['c1m9'] += 1
                if force_dec:
                    p['new9'] += 1
                if returns >= 3:
                    p['new10'] += 1

        # Сохраняем прогресс после каждого завода
        plant_st = stats['by_plant'][plant_code]
        print(f'  [{plant_code}] готово: заказов={plant_st["orders"]}, строк={plant_st["rows"]}, '
              f'ЕО={plant_st["eq"]}, C1-M1={plant_st["c1m1"]}, C1-M6={plant_st["c1m6"]}, '
              f'C1-M9={plant_st["c1m9"]}, NEW-9={plant_st["new9"]}, NEW-10={plant_st["new10"]}')

    print(f'\n[SAVE] Сохраняем {OUT_PATH} ...')
    wb.save(OUT_PATH)
    print(f'[DONE] Файл сохранён.')

    # Подсчёт C2-M2 (проблемное оборудование >= 5 заказов на ЕО) — делаем отдельным проходом,
    # но для краткости здесь пропускаем: это увидит сама программа.

    # Итоговая статистика
    print('\n══════════════════ ИТОГО ══════════════════')
    print(f'Всего заказов: {stats["orders_total"]:,}')
    print(f'Всего строк истории: {stats["rows_total"]:,}')
    print(f'Всего единиц оборудования: {stats["equipment_total"]:,}')
    total_plan, total_fact = 0, 0
    for code, st in stats['by_plant'].items():
        total_plan += st['cost_plan']
        total_fact += st['cost_fact']
        print(f'\n{code} — {PLANTS[code]["iwerk_txt"]}:')
        print(f'  заказов: {st["orders"]:,}')
        print(f'  ЕО: {st["eq"]:,}')
        print(f'  план. стоимость: {st["cost_plan"]/1e6:,.1f} млн ₽')
        print(f'  факт. стоимость: {st["cost_fact"]/1e6:,.1f} млн ₽')
        print(f'  переплата: {(st["cost_fact"] - st["cost_plan"])/1e6:+,.1f} млн ₽')
        print(f'  C1-M1 (перерасход): {st["c1m1"]}')
        print(f'  C1-M6 (аномалия ТМ): {st["c1m6"]}')
        print(f'  C1-M9 (незавершён): {st["c1m9"]}')
        print(f'  NEW-9 (декабрьское закрытие): {st["new9"]}')
        print(f'  NEW-10 (возвраты ≥3): {st["new10"]}')
    print(f'\nИТОГО: план={total_plan/1e9:.2f} млрд ₽, факт={total_fact/1e9:.2f} млрд ₽, '
          f'переплата={(total_fact - total_plan)/1e9:+.2f} млрд ₽')
    print(f'Файл: {OUT_PATH}')


if __name__ == '__main__':
    run_generation()
