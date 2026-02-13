# -*- coding: utf-8 -*-
"""
core/data_processor.py — Обработка данных SAP
"""

import pandas as pd
import numpy as np

from utils.parsers import fast_parse_series, safe_parse_datetime


def calculate_data_completeness(row, required_fields):
    """Расчёт полноты данных для одной строки."""
    filled = 0
    total = len(required_fields)
    for field in required_fields:
        val = row.get(field, 'Н/Д')
        if pd.notna(val) and str(val) not in ['Н/Д', 'nan', 'None', '', '0']:
            filled += 1
    return (filled / total * 100) if total > 0 else 0


def aggregate_status_history(df):
    """Агрегация истории статусов для нового формата."""
    static_cols = [
        'BUKRS', 'BUKRS_TXT', 'AUFNR_TXT',
        'ERDAT', 'AEDAT', 'ERNAM', 'AENAM',
        'BAUTL', 'MSGRP', 'USER4',
        'GSTRP', 'GLTRP', 'ZZFACTBEG', 'ZZFACTEND',
        'ZZ_DEFNUM', 'ZZ_DOGNUM', 'MAUFNR', 'MAUFNR_TXT',
        'AUART', 'AUART_TXT', 'INBDT',
        'EQUNR', 'EQUNR_TXT',
        'IWERK', 'IWERK_TXT', 'GEWRK', 'GEWRK_TXT',
        'ILART', 'ILART_TXT', 'STORT', 'STORT_TXT',
        'TPLNR8', 'TPLNR8_TXT', 'ABCKZ', 'ABCKZ_TXT',
        'PMCOALLP', 'PMCOALLF', 'PMCO001P', 'PMCO001F',
        'PMCO008P', 'PMCO008F',
        'INGPR', 'INGPR_TXT', 'TPLNR', 'TPLNR_TXT',
        'CLINT', 'CLINT_TXT', 'AUFNR_OSN', 'DGP'
    ]
    static_cols = [c for c in static_cols if c in df.columns]

    agg_dict = {col: 'first' for col in static_cols}
    df_agg = df.groupby('AUFNR').agg(agg_dict).reset_index()

    df_sorted = df.sort_values(['AUFNR', 'AEDAT'])

    last_status = df_sorted.groupby('AUFNR').last()[['ISTAT', 'ISTAT_TXT']].reset_index()
    last_status.columns = ['AUFNR', 'CURR_STAT', 'CURR_STAT_TXT']
    df_agg = df_agg.merge(last_status, on='AUFNR', how='left')

    status_count = df.groupby('AUFNR').size().reset_index(name='N_STATUS_CHANGES')
    df_agg = df_agg.merge(status_count, on='AUFNR', how='left')

    all_statuses = df.groupby('AUFNR')['ISTAT_TXT'].apply(
        lambda x: ' | '.join(x.unique())
    ).reset_index()
    all_statuses.columns = ['AUFNR', 'ALL_STATUSES']
    df_agg = df_agg.merge(all_statuses, on='AUFNR', how='left')

    def count_returns(group):
        statuses = group['ISTAT'].tolist()
        returns = 0
        seen = set()
        for stat in statuses:
            if stat in seen:
                returns += 1
            seen.add(stat)
        return returns

    returns = df.groupby('AUFNR').apply(count_returns, include_groups=False).reset_index(name='N_STATUS_RETURNS')
    df_agg = df_agg.merge(returns, on='AUFNR', how='left')

    first_author = df_sorted.groupby('AUFNR').first()[['ERNAM']].reset_index()
    first_author.columns = ['AUFNR', 'CREATOR']
    df_agg = df_agg.merge(first_author, on='AUFNR', how='left')

    last_author = df_sorted.groupby('AUFNR').last()[['ERNAM']].reset_index()
    last_author.columns = ['AUFNR', 'LAST_EDITOR']
    df_agg = df_agg.merge(last_author, on='AUFNR', how='left')

    return df_agg


def process_data(df_raw):
    """Обработка сырых данных SAP."""
    from core.data_loader import detect_export_format

    df = df_raw.copy()
    export_format = detect_export_format(df)

    if export_format == 'NEW_STATUS_HISTORY':
        df = aggregate_status_history(df)

        map_cols = {
            'AUFNR': 'ID', 'AUFNR_TXT': 'Текст',
            'BUKRS': 'БЕ_Код', 'BUKRS_TXT': 'БЕ',
            'CURR_STAT': 'STAT_Код', 'CURR_STAT_TXT': 'STAT',
            'ERDAT': 'ДАТА_СОЗД', 'AEDAT': 'ДАТА_ИЗМ',
            'ERNAM': 'КТО_СОЗДАЛ', 'AENAM': 'КТО_ИЗМЕНИЛ',
            'CREATOR': 'USER', 'LAST_EDITOR': 'LAST_USER',
            'BAUTL': 'УЗЕЛ', 'MSGRP': 'ГРУППА_СООБЩ', 'USER4': 'USER4',
            'GSTRP': 'S', 'GLTRP': 'E',
            'ZZFACTBEG': 'FS', 'ZZFACTEND': 'FE',
            'ZZ_DEFNUM': 'ДЕФЕКТ_ВЕД', 'ZZ_DOGNUM': 'ДОГОВОР',
            'MAUFNR': 'MAUFNR_Код', 'MAUFNR_TXT': 'MAUFNR',
            'AUART': 'Вид_Код', 'AUART_TXT': 'Вид',
            'INBDT': 'ДАТА_ВВОДА',
            'EQUNR': 'EQUNR_Код', 'EQUNR_TXT': 'ЕО',
            'IWERK': 'ЗАВОД_Код', 'IWERK_TXT': 'ЗАВОД',
            'GEWRK': 'РМ_Код', 'GEWRK_TXT': 'РМ',
            'ILART': 'ILART_Код', 'ILART_TXT': 'ВИД_РАБОТ',
            'STORT': 'МЕСТОПОЛ_Код', 'STORT_TXT': 'МЕСТОПОЛ',
            'TPLNR8': 'УСТАНОВКА_Код', 'TPLNR8_TXT': 'УСТАНОВКА',
            'ABCKZ': 'ABC_Код', 'ABCKZ_TXT': 'ABC',
            'PMCOALLP': 'P', 'PMCOALLF': 'F',
            'PMCO001P': 'PT', 'PMCO001F': 'FT',
            'PMCO008P': 'MTR_P', 'PMCO008F': 'MTR_F',
            'INGPR': 'INGRP_Код', 'INGPR_TXT': 'INGRP',
            'TPLNR': 'ТМ_Код', 'TPLNR_TXT': 'ТМ',
            'CLINT': 'КЛАСС_Код', 'CLINT_TXT': 'КЛАСС',
            'AUFNR_OSN': 'ОСНОВА_ЗАКАЗ', 'DGP': 'DGP',
            'N_STATUS_CHANGES': 'N_STATUS_CHANGES',
            'N_STATUS_RETURNS': 'N_STATUS_RETURNS',
            'ALL_STATUSES': 'ALL_STATUSES'
        }
    else:
        map_cols = {
            'Заказ': 'ID', 'Краткий текст': 'Текст', 'Вид заказа': 'Вид',
            'Общие затраты/план': 'P', 'ОбщЗатраты/план': 'P',
            'Общие затраты/факт': 'F', 'ОбщЗатраты/факт': 'F',
            'Техническое место': 'ТМ', 'ТехнМесто': 'ТМ',
            'Базисный срок начала': 'S', 'БазисСрокНачала': 'S',
            'Базисный срок конца': 'E', 'БазисСрокКонца': 'E',
            'Фактический срок начала': 'FS',
            'Фактический срок конца заказа': 'FE',
            'Системный статус': 'STAT', 'СистемнСтатус': 'STAT',
            'Пользовательский статус': 'USTAT', 'ПользСтатус': 'USTAT',
            'МВЗ': 'MVZ',
            'Индикатор ABC': 'ABC', 'Код ABC': 'ABC',
            'Рабочее место': 'РМ',
            'Группа плановиков': 'INGRP',
            'Единица оборудования': 'ЕО', 'EQUNR': 'ЕО',
            'БЕ': 'БЕ', 'Балансовая единица': 'БЕ',
            'Завод': 'ЗАВОД',
            'Ввел': 'USER',
            'План_трудозатраты': 'PT', 'Факт_трудозатраты': 'FT'
        }

    df = df.rename(columns={k: v for k, v in map_cols.items() if k in df.columns})

    df['Plan_N'] = fast_parse_series(df['P']) if 'P' in df.columns else 0.0
    df['Fact_N'] = fast_parse_series(df['F']) if 'F' in df.columns else 0.0
    df['Plan_T'] = fast_parse_series(df['PT']) if 'PT' in df.columns else 0.0
    df['Fact_T'] = fast_parse_series(df['FT']) if 'FT' in df.columns else 0.0

    for col, src in [('Начало', 'S'), ('Конец', 'E')]:
        if src in df.columns:
            df[col] = safe_parse_datetime(df[src])
        else:
            df[col] = pd.NaT

    for col, src in [('Факт_Начало', 'FS'), ('Факт_Конец', 'FE')]:
        if src in df.columns:
            df[col] = safe_parse_datetime(df[src])
        else:
            df[col] = pd.NaT

    try:
        if df['Конец'].notna().any() and df['Начало'].notna().any():
            df['План_Длит'] = (df['Конец'] - df['Начало']).dt.days.astype(float)
        else:
            df['План_Длит'] = np.nan

        if df['Факт_Конец'].notna().any() and df['Факт_Начало'].notna().any():
            fact_start = df['Факт_Начало']
            fact_end = df['Факт_Конец']
            mask_valid = (fact_end.dt.year > 1971) & (fact_start.dt.year > 1971)
            df['Факт_Длит'] = np.nan
            df.loc[mask_valid, 'Факт_Длит'] = (fact_end[mask_valid] - fact_start[mask_valid]).dt.days.astype(float)
        else:
            df['Факт_Длит'] = np.nan

        mask_both = df['План_Длит'].notna() & df['Факт_Длит'].notna()
        df['Превыш_Длит'] = np.nan
        df.loc[mask_both, 'Превыш_Длит'] = (
            pd.to_numeric(df.loc[mask_both, 'Факт_Длит'], errors='coerce') -
            pd.to_numeric(df.loc[mask_both, 'План_Длит'], errors='coerce')
        )
        df['Превыш_Длит'] = pd.to_numeric(df['Превыш_Длит'], errors='coerce')
    except Exception:
        df['План_Длит'] = np.nan
        df['Факт_Длит'] = np.nan
        df['Превыш_Длит'] = np.nan

    str_fields = ['ID', 'Текст', 'Вид', 'ТМ', 'STAT', 'ABC', 'РМ', 'БЕ', 'ЗАВОД', 'УСТАНОВКА', 'ПРОИЗВОДСТВО', 'ЦЕХ', 'ЕО', 'INGRP', 'КЛАСС', 'USER']
    for c in str_fields:
        if c in df.columns:
            df[c] = df[c].astype(str).replace(['nan', 'None', '', '0', 'Не присвоено', 'Не присв', 'Пусто'], 'Н/Д')
        else:
            df[c] = 'Н/Д'

    if 'Вид_Код' in df.columns:
        df['Вид_Код'] = df['Вид_Код'].astype(str).replace(['nan', 'None', ''], 'Н/Д')
    else:
        df['Вид_Код'] = df['Вид'].str.extract(r'^([A-Z]{2}\d{2})', expand=False).fillna('Н/Д')

    # Иерархия из tm_structure.json
    try:
        from core.tm_loader import load_tm_structure, format_with_name
        tm_hierarchy, eo_to_tm = load_tm_structure()
        has_structure = len(tm_hierarchy) > 0
    except Exception:
        has_structure = False
        tm_hierarchy = {}
        eo_to_tm = {}

    if has_structure:
        def get_hierarchy_for_row(row):
            result = {
                'производство_код': None, 'производство_название': None,
                'цех_код': None, 'цех_название': None,
                'установка_код': None, 'установка_название': None
            }

            eo_code = row.get('EQUNR_Код') or row.get('ЕО')
            if eo_code and str(eo_code) not in ['Н/Д', 'nan', 'None', '']:
                eo_str = str(eo_code).strip()
                if ' ' in eo_str:
                    eo_str = eo_str.split()[0]
                eo_stripped = eo_str.lstrip('0') or eo_str
                tm_code = eo_to_tm.get(eo_stripped) or eo_to_tm.get(eo_str)
                if tm_code and tm_code in tm_hierarchy:
                    data = tm_hierarchy[tm_code]
                    result['производство_код'] = data.get('производство_код')
                    result['производство_название'] = data.get('производство_название')
                    result['цех_код'] = data.get('цех_код')
                    result['цех_название'] = data.get('цех_название')
                    result['установка_код'] = data.get('установка_код')
                    result['установка_название'] = data.get('установка_название')
                    return result

            tm_code = row.get('ТМ_Код') or row.get('ТМ')
            if tm_code and str(tm_code) not in ['Н/Д', 'nan', 'None', '']:
                tm_str = str(tm_code).strip()
                if ' ' in tm_str:
                    tm_str = tm_str.split()[0]
                if tm_str in tm_hierarchy:
                    data = tm_hierarchy[tm_str]
                    result['производство_код'] = data.get('производство_код')
                    result['производство_название'] = data.get('производство_название')
                    result['цех_код'] = data.get('цех_код')
                    result['цех_название'] = data.get('цех_название')
                    result['установка_код'] = data.get('установка_код')
                    result['установка_название'] = data.get('установка_название')
                    return result
                if len(tm_str) >= 4 and tm_str[:2] == 'ST':
                    result['производство_код'] = tm_str[:4]
                if len(tm_str) >= 7 and '.' in tm_str:
                    result['цех_код'] = tm_str[:7]

            return result

        hierarchy_data = df.apply(get_hierarchy_for_row, axis=1, result_type='expand')

        df['ПРОИЗВОДСТВО_Код'] = hierarchy_data['производство_код'].fillna('Н/Д').replace([None, 'None', ''], 'Н/Д')
        df['ЦЕХ_Код'] = hierarchy_data['цех_код'].fillna('Н/Д').replace([None, 'None', ''], 'Н/Д')
        df['УСТАНОВКА_Код'] = hierarchy_data['установка_код'].fillna('Н/Д').replace([None, 'None', ''], 'Н/Д')

        df['ПРОИЗВОДСТВО'] = df.apply(
            lambda r: format_with_name(r['ПРОИЗВОДСТВО_Код'], hierarchy_data.loc[r.name, 'производство_название']),
            axis=1
        )
        df['ЦЕХ'] = df.apply(
            lambda r: format_with_name(r['ЦЕХ_Код'], hierarchy_data.loc[r.name, 'цех_название']),
            axis=1
        )
        if 'УСТАНОВКА' not in df.columns or df['УСТАНОВКА'].eq('Н/Д').all():
            df['УСТАНОВКА'] = df.apply(
                lambda r: format_with_name(r['УСТАНОВКА_Код'], hierarchy_data.loc[r.name, 'установка_название']),
                axis=1
            )

        if 'ТМ_Код' in df.columns:
            def format_tm(row):
                tm_kod = str(row.get('ТМ_Код', '')).strip()
                tm_txt = str(row.get('ТМ', '')).strip()
                if tm_kod and tm_kod not in ['Н/Д', 'nan', 'None', '']:
                    tm_data = tm_hierarchy.get(tm_kod, {})
                    tm_name = tm_data.get('название', '') if tm_data else ''
                    if tm_name:
                        return f"{tm_kod} - {tm_name}"
                    elif tm_txt and tm_txt not in ['Н/Д', 'nan', 'None', '']:
                        return f"{tm_kod} - {tm_txt}"
                    else:
                        return tm_kod
                return tm_txt if tm_txt and tm_txt not in ['Н/Д', 'nan', 'None', ''] else 'Н/Д'
            df['ТМ'] = df.apply(format_tm, axis=1)

        if 'УСТАНОВКА_Код' in df.columns:
            def format_ust(row):
                ust_kod = str(row.get('УСТАНОВКА_Код', '')).strip()
                ust_txt = str(row.get('УСТАНОВКА', '')).strip()
                if ust_kod and ust_kod not in ['Н/Д', 'nan', 'None', '']:
                    if ust_txt.startswith(ust_kod):
                        return ust_txt
                    ust_data = tm_hierarchy.get(ust_kod, {})
                    ust_name = ust_data.get('название', '') if ust_data else ''
                    if ust_name:
                        return f"{ust_kod} - {ust_name}"
                    elif ust_txt and ust_txt not in ['Н/Д', 'nan', 'None', '']:
                        return f"{ust_kod} - {ust_txt}"
                    else:
                        return ust_kod
                return ust_txt if ust_txt and ust_txt not in ['Н/Д', 'nan', 'None', ''] else 'Н/Д'
            df['УСТАНОВКА'] = df.apply(format_ust, axis=1)
    else:
        if 'ТМ_Код' in df.columns:
            tm_kod = df['ТМ_Код'].astype(str)
            df['ПРОИЗВОДСТВО_Код'] = tm_kod.str[:4].replace(['nan', 'None', '', 'Н/Д'], 'Н/Д')
            df['ЦЕХ_Код'] = tm_kod.str[:7].replace(['nan', 'None', '', 'Н/Д'], 'Н/Д')
            df['ПРОИЗВОДСТВО'] = df['ПРОИЗВОДСТВО_Код']
            df['ЦЕХ'] = df['ЦЕХ_Код']
        else:
            df['ПРОИЗВОДСТВО_Код'] = 'Н/Д'
            df['ПРОИЗВОДСТВО'] = 'Н/Д'
            df['ЦЕХ_Код'] = 'Н/Д'
            df['ЦЕХ'] = 'Н/Д'

    required_fields = ['ID', 'Текст', 'ТМ', 'Вид', 'Plan_N', 'Fact_N', 'Начало', 'Конец', 'STAT', 'ABC']
    df['Data_Completeness'] = df.apply(lambda row: calculate_data_completeness(row, required_fields), axis=1)

    df.attrs['export_format'] = export_format
    return df
