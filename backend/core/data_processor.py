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
        'CLINT', 'CLINT_TXT', 'AUFNR_OSN', 'DGP',
        'AUSZT', 'AUSVN', 'AUSBS'
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

    # ТИТАН-5: векторизованный ALL_STATUSES через drop_duplicates + agg
    # Было: groupby().apply(lambda x: ' | '.join(x.unique())) — медленно
    df_uniq_status = df[['AUFNR', 'ISTAT_TXT']].drop_duplicates()
    all_statuses = (df_uniq_status
                    .groupby('AUFNR')['ISTAT_TXT']
                    .agg(lambda x: ' | '.join(x))
                    .reset_index()
                    .rename(columns={'ISTAT_TXT': 'ALL_STATUSES'}))
    df_agg = df_agg.merge(all_statuses, on='AUFNR', how='left')

    # ТИТАН-5: N_STATUS_RETURNS векторизованно через cumcount
    # Было: groupby().apply(count_returns) с циклом — очень медленно
    # Исходная семантика: считаем сколько раз в группе статус повторился
    # (для каждой позиции: если статус уже встречался раньше в группе → +1)
    df_sorted2 = df.sort_values(['AUFNR', 'AEDAT'])
    # cumcount по (AUFNR, ISTAT) = счётчик появлений конкретного ISTAT внутри AUFNR-группы
    # cum == 0 — первое появление, cum >= 1 — повторное (возврат)
    dup_flag = df_sorted2.groupby(['AUFNR', 'ISTAT']).cumcount() > 0
    returns = (dup_flag.groupby(df_sorted2['AUFNR'])
                      .sum()
                      .reset_index(name='N_STATUS_RETURNS'))
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
            'ALL_STATUSES': 'ALL_STATUSES',
            'AUSZT': 'AUSZT_RAW', 'AUSVN': 'NS', 'AUSBS': 'NE'
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

    # Запоминаем колонки, реально присутствующие в исходном файле (до создания фиктивных)
    _pre_cols = set(df.columns.tolist())
    # Промежуточные имена → финальные (для числовых/дат полей)
    _inter_to_final = {
        'P': 'Plan_N', 'F': 'Fact_N', 'PT': 'Plan_T', 'FT': 'Fact_T',
        'S': 'Начало', 'E': 'Конец', 'FS': 'Факт_Начало', 'FE': 'Факт_Конец',
    }
    source_columns = set(_pre_cols)
    for inter, final in _inter_to_final.items():
        if inter in _pre_cols:
            source_columns.add(final)

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

    # --- Даты по сообщению (AUSVN/AUSBS) ---
    for col, src in [('Сообщ_Начало', 'NS'), ('Сообщ_Конец', 'NE')]:
        if src in df.columns:
            df[col] = safe_parse_datetime(df[src])
        else:
            df[col] = pd.NaT

    # --- Простой оборудования (AUSZT) в секундах ---
    df['Простой_Сек'] = fast_parse_series(df['AUSZT_RAW']) if 'AUSZT_RAW' in df.columns else 0.0

    # --- Каскадные даты ---
    DATE_CUTOFF = pd.Timestamp('2015-01-01')

    # Отсечка мусора: всё < 2015 → NaT
    for col in ['Начало', 'Конец', 'Факт_Начало', 'Факт_Конец', 'Сообщ_Начало', 'Сообщ_Конец']:
        if col in df.columns:
            mask_junk = df[col].notna() & (df[col] < DATE_CUTOFF)
            df.loc[mask_junk, col] = pd.NaT

    # Каскад 3 уровня: ФАКТ → СООБЩЕНИЕ → ПЛАН
    # Начало: факт → сообщение → план
    cascade_start = df['Факт_Начало'].where(df['Факт_Начало'].notna(),
                    df['Сообщ_Начало'].where(df['Сообщ_Начало'].notna(), df['Начало']))
    df['Дата_Начало'] = cascade_start
    # Конец: факт → сообщение → план
    cascade_end = df['Факт_Конец'].where(df['Факт_Конец'].notna(),
                  df['Сообщ_Конец'].where(df['Сообщ_Конец'].notna(), df['Конец']))
    df['Дата_Конец'] = cascade_end
    df['Дата_Месяц'] = df['Дата_Начало']

    # Источник дат (4 уровня)
    df['Источник_Дат'] = 'NONE'
    mask_fact = df['Факт_Начало'].notna()
    mask_notify = (~mask_fact) & df['Сообщ_Начало'].notna()
    mask_plan = (~mask_fact) & (~mask_notify) & df['Начало'].notna()
    df.loc[mask_fact, 'Источник_Дат'] = 'FACT'
    df.loc[mask_notify, 'Источник_Дат'] = 'NOTIFY'
    df.loc[mask_plan, 'Источник_Дат'] = 'PLAN'

    # Длительность по сообщению (дни)
    mask_notify_both = df['Сообщ_Конец'].notna() & df['Сообщ_Начало'].notna()
    df['Сообщ_Длит'] = np.nan
    df.loc[mask_notify_both, 'Сообщ_Длит'] = (
        df.loc[mask_notify_both, 'Сообщ_Конец'] - df.loc[mask_notify_both, 'Сообщ_Начало']
    ).dt.days.astype(float)

    try:
        if df['Конец'].notna().any() and df['Начало'].notna().any():
            df['План_Длит'] = (df['Конец'] - df['Начало']).dt.days.astype(float)
        else:
            df['План_Длит'] = np.nan

        if df['Факт_Конец'].notna().any() and df['Факт_Начало'].notna().any():
            fact_start = df['Факт_Начало']
            fact_end = df['Факт_Конец']
            mask_valid = fact_end.notna() & fact_start.notna()
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
        # ═══════════════════════════════════════════════════════════════
        # Векторизованная раскрутка иерархии (ТИТАН-5: замена apply axis=1)
        # Алгоритм: сначала пытаемся найти TM через EO→TM маппинг,
        # затем по прямому коду ТМ, затем по префиксам "ST..." / "X.YYYY".
        # ═══════════════════════════════════════════════════════════════
        NA_SET = {'Н/Д', 'nan', 'None', ''}

        # Series с сырыми EO-кодами (приоритет EQUNR_Код, fallback ЕО)
        eo_raw = df['EQUNR_Код'].astype('string') if 'EQUNR_Код' in df.columns else pd.Series('', index=df.index, dtype='string')
        eo_fallback = df['ЕО'].astype('string') if 'ЕО' in df.columns else pd.Series('', index=df.index, dtype='string')
        eo_clean = eo_raw.where(~eo_raw.isin(NA_SET) & eo_raw.notna(), eo_fallback)

        # Убираем хвосты после пробела и ведущие нули
        eo_clean = eo_clean.fillna('').str.split(' ').str[0].str.strip()
        eo_stripped = eo_clean.str.lstrip('0').where(lambda s: s != '', eo_clean)

        # Series с ТМ-кодами (приоритет ТМ_Код, fallback ТМ)
        tm_raw = df['ТМ_Код'].astype('string') if 'ТМ_Код' in df.columns else pd.Series('', index=df.index, dtype='string')
        tm_fallback = df['ТМ'].astype('string') if 'ТМ' in df.columns else pd.Series('', index=df.index, dtype='string')
        tm_clean = tm_raw.where(~tm_raw.isin(NA_SET) & tm_raw.notna(), tm_fallback)
        tm_clean = tm_clean.fillna('').str.split(' ').str[0].str.strip()

        # Словарь eo_to_tm как pandas Series для .map()
        eo_map_ser = pd.Series(eo_to_tm)

        # Resolving TM code: сначала через stripped, потом через raw, потом через tm_clean
        tm_from_eo_stripped = eo_stripped.map(eo_map_ser)
        tm_from_eo_raw = eo_clean.map(eo_map_ser)
        tm_from_eo = tm_from_eo_stripped.where(tm_from_eo_stripped.notna(), tm_from_eo_raw)

        # Финальный tm_code: если по EO не нашлось — проверяем прямой tm_clean
        tm_in_hier_mask = tm_clean.isin(tm_hierarchy)
        resolved_tm = tm_from_eo.where(tm_from_eo.notna(), tm_clean.where(tm_in_hier_mask, pd.NA))

        # Построим DataFrame с иерархией из tm_hierarchy (один раз)
        hier_rows = []
        for tm_code_k, data in tm_hierarchy.items():
            hier_rows.append({
                '_tm_code': tm_code_k,
                'производство_код': data.get('производство_код'),
                'производство_название': data.get('производство_название'),
                'цех_код': data.get('цех_код'),
                'цех_название': data.get('цех_название'),
                'установка_код': data.get('установка_код'),
                'установка_название': data.get('установка_название'),
                'тм_название': data.get('название'),
            })
        hier_df = pd.DataFrame(hier_rows).set_index('_tm_code') if hier_rows else pd.DataFrame(
            columns=['производство_код', 'производство_название', 'цех_код', 'цех_название',
                    'установка_код', 'установка_название', 'тм_название']
        )

        # Подтягиваем 6 полей через reindex (векторизованно)
        prod_code = resolved_tm.map(hier_df['производство_код']).astype(object)
        prod_name = resolved_tm.map(hier_df['производство_название']).astype(object)
        shop_code = resolved_tm.map(hier_df['цех_код']).astype(object)
        shop_name = resolved_tm.map(hier_df['цех_название']).astype(object)
        unit_code_s = resolved_tm.map(hier_df['установка_код']).astype(object)
        unit_name_s = resolved_tm.map(hier_df['установка_название']).astype(object)

        # Fallback по префиксам для ТМ-кодов вне справочника:
        # - если tm_str начинается с 'ST' и len>=4 → производство = tm_str[:4]
        # - если '.' есть и len>=7 → цех = tm_str[:7]
        fallback_mask = resolved_tm.isna() & tm_clean.notna() & (tm_clean != '')
        st_prefix_mask = fallback_mask & (tm_clean.str.len() >= 4) & (tm_clean.str[:2] == 'ST')
        prod_code = prod_code.where(~st_prefix_mask, tm_clean.str[:4])

        shop_prefix_mask = fallback_mask & (tm_clean.str.len() >= 7) & tm_clean.str.contains('.', regex=False, na=False)
        shop_code = shop_code.where(~shop_prefix_mask, tm_clean.str[:7])

        # Заполняем None/пустые значения на 'Н/Д'
        def _normalize(s):
            return s.where(s.notna() & ~s.isin([None, 'None', '', pd.NA]), 'Н/Д').fillna('Н/Д').astype(str)

        df['ПРОИЗВОДСТВО_Код'] = _normalize(prod_code)
        df['ЦЕХ_Код'] = _normalize(shop_code)
        df['УСТАНОВКА_Код'] = _normalize(unit_code_s)

        # format_with_name векторизованно:
        #   if code in NA_SET: 'Н/Д'
        #   elif name not empty: f'{code} - {name}'
        #   else: code
        def _format_with_name_vec(code_ser, name_ser):
            code = code_ser.astype(str)
            name = name_ser.astype(object).where(name_ser.notna(), '').astype(str)
            is_na = code.isin(NA_SET) | code.eq('Н/Д')
            name_empty = name.isin(['', 'nan', 'None']) | name.isna()
            combined = code.str.cat(name, sep=' - ')
            out = np.where(is_na, 'Н/Д', np.where(name_empty, code, combined))
            return pd.Series(out, index=code.index)

        df['ПРОИЗВОДСТВО'] = _format_with_name_vec(df['ПРОИЗВОДСТВО_Код'], prod_name)
        df['ЦЕХ'] = _format_with_name_vec(df['ЦЕХ_Код'], shop_name)
        if 'УСТАНОВКА' not in df.columns or df['УСТАНОВКА'].eq('Н/Д').all():
            df['УСТАНОВКА'] = _format_with_name_vec(df['УСТАНОВКА_Код'], unit_name_s)

        # format_tm векторизованно:
        # if tm_kod not in NA_SET:
        #   tm_name_from_hier = tm_hierarchy[tm_kod].get('название')
        #   if tm_name_from_hier: f'{tm_kod} - {tm_name_from_hier}'
        #   elif tm_txt not in NA_SET: f'{tm_kod} - {tm_txt}'
        #   else: tm_kod
        # else: tm_txt if tm_txt not in NA_SET else 'Н/Д'
        if 'ТМ_Код' in df.columns:
            tm_kod_ser = df['ТМ_Код'].astype(str).str.strip()
            tm_txt_ser = df['ТМ'].astype(str).str.strip() if 'ТМ' in df.columns else pd.Series('', index=df.index)
            kod_is_na = tm_kod_ser.isin(NA_SET)
            txt_is_na = tm_txt_ser.isin(NA_SET)

            # Имя ТМ из справочника (через map)
            tm_name_from_hier = tm_kod_ser.map(hier_df['тм_название']).astype(object)
            hier_name = tm_name_from_hier.where(tm_name_from_hier.notna() & ~tm_name_from_hier.isin(['', None, 'None']), '').astype(str)

            # Комбинации
            with_hier_name = tm_kod_ser.str.cat(hier_name, sep=' - ')
            with_txt = tm_kod_ser.str.cat(tm_txt_ser, sep=' - ')

            tm_final = np.where(
                kod_is_na,
                np.where(txt_is_na, 'Н/Д', tm_txt_ser),
                np.where(
                    hier_name != '',
                    with_hier_name,
                    np.where(~txt_is_na, with_txt, tm_kod_ser)
                )
            )
            df['ТМ'] = pd.Series(tm_final, index=df.index)

        # format_ust векторизованно — аналогичная логика
        if 'УСТАНОВКА_Код' in df.columns:
            ust_kod_ser = df['УСТАНОВКА_Код'].astype(str).str.strip()
            ust_txt_ser = df['УСТАНОВКА'].astype(str).str.strip() if 'УСТАНОВКА' in df.columns else pd.Series('', index=df.index)
            ukod_is_na = ust_kod_ser.isin(NA_SET)
            utxt_is_na = ust_txt_ser.isin(NA_SET)

            # Если txt уже начинается с kod — оставляем txt как есть
            # (векторизованно через numpy; str.startswith не принимает Series)
            kod_arr = ust_kod_ser.values
            txt_arr = ust_txt_ser.values
            starts_with_kod = pd.Series(
                [t.startswith(k) if isinstance(t, str) and isinstance(k, str) else False
                 for t, k in zip(txt_arr, kod_arr)],
                index=ust_txt_ser.index
            )

            ust_name_from_hier = ust_kod_ser.map(hier_df['установка_название']).astype(object)
            uhier_name = ust_name_from_hier.where(ust_name_from_hier.notna() & ~ust_name_from_hier.isin(['', None, 'None']), '').astype(str)

            with_uhier = ust_kod_ser.str.cat(uhier_name, sep=' - ')
            with_utxt = ust_kod_ser.str.cat(ust_txt_ser, sep=' - ')

            ust_final = np.where(
                ukod_is_na,
                np.where(utxt_is_na, 'Н/Д', ust_txt_ser),
                np.where(
                    starts_with_kod,
                    ust_txt_ser,
                    np.where(
                        uhier_name != '',
                        with_uhier,
                        np.where(~utxt_is_na, with_utxt, ust_kod_ser)
                    )
                )
            )
            df['УСТАНОВКА'] = pd.Series(ust_final, index=df.index)
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
    # ТИТАН-5: векторизованный расчёт Data_Completeness (замена apply axis=1)
    #
    # Исходная логика calculate_data_completeness():
    #   filled = count(val where notna(val) AND str(val) not in {'Н/Д', 'nan', 'None', '', '0'})
    #   return filled / total * 100
    EMPTY_VALUES = {'Н/Д', 'nan', 'None', '', '0'}
    present_cols = [c for c in required_fields if c in df.columns]
    if present_cols:
        # Для каждой требуемой колонки — True, если значение непустое
        masks = []
        for col in present_cols:
            col_data = df[col]
            if pd.api.types.is_datetime64_any_dtype(col_data):
                # Для дат — просто notna
                mask = col_data.notna()
            elif pd.api.types.is_numeric_dtype(col_data):
                # Для чисел — notna И не равно 0 (по исходной логике '0' считается пустым)
                mask = col_data.notna() & (col_data != 0)
            else:
                # Для строк/объектов — notna и строковое значение не в EMPTY_VALUES
                s_str = col_data.astype(str)
                mask = col_data.notna() & ~s_str.isin(EMPTY_VALUES)
            masks.append(mask)
        filled_count = pd.concat(masks, axis=1).sum(axis=1)
        df['Data_Completeness'] = (filled_count / len(required_fields) * 100).astype(float)
    else:
        df['Data_Completeness'] = 0.0

    # ═══════════════════════════════════════════════════════════════════
    # ТИТАН-5: Оптимизация типов памяти
    # object → category для повторяющихся строк (экономия ~60% памяти +
    # ускорение groupby / сравнений в 2-3 раза).
    # ДЕНЕЖНЫЕ поля (Plan_N, Fact_N, PMCO*) — оставляем float64 (точность).
    # ═══════════════════════════════════════════════════════════════════
    _CATEGORICAL_COLS = [
        'БЕ', 'ЗАВОД', 'ПРОИЗВОДСТВО', 'ЦЕХ', 'УСТАНОВКА',
        'STAT', 'ABC', 'Вид', 'ВИД_РАБОТ', 'INGRP', 'КЛАСС',
        'USER', 'LAST_USER', 'MVZ', 'РМ',
    ]
    for _col in _CATEGORICAL_COLS:
        if _col in df.columns and not isinstance(df[_col].dtype, pd.CategoricalDtype):
            # Принудительно приводим к строке перед category (None → 'Н/Д')
            df[_col] = df[_col].fillna('Н/Д').astype(str).astype('category')

    df.attrs['export_format'] = export_format
    df.attrs['source_columns'] = source_columns
    return df
