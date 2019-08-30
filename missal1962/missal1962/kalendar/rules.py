# -*- coding: utf-8 -*-

"""
Rules for solving conflicts between observances occurring at the same date.

Each rule accepts the date for which calculations are being made (`date`), a list containing `Observance`s
representing this day's "tempora" and a list of `Observance`s falling on given date.

Each rule returns a tuple consisting of three lists:
1. Celebration - main `Observance` celebrated in given day
2. Commemoration - a list of `Observance`s commemorated next to the main feast
3. Shift - a list of two-element tuples, each consisting of a `date` pointing to a day to which given
   `Observance` should be moved and the `Observance` itself.
"""

from calendar import isleap
from copy import copy
from datetime import date, timedelta
from typing import List

from constants.common import (C_10A, C_10B, C_10C, C_10PASC, C_10T, EMBER_DAYS,
                              FEASTS_OF_JESUS_CLASS_1_AND_2, PATTERN_ADVENT,
                              PATTERN_ADVENT_FERIA_BETWEEN_17_AND_23,
                              PATTERN_CLASS_1, PATTERN_EASTER,
                              PATTERN_SANCTI_CLASS_1_OR_2,
                              PATTERN_SANCTI_CLASS_2, PATTERN_TEMPORA,
                              PATTERN_TEMPORA_SUNDAY,
                              PATTERN_TEMPORA_SUNDAY_CLASS_2, SANCTI_01_13,
                              SANCTI_02_24, SANCTI_02_27, SANCTI_11_02_1,
                              SANCTI_12_08, SANCTI_12_24, SANCTI_12_25_1,
                              TEMPORA_EPI1_0, TEMPORA_PASC0_0, TEMPORA_QUAD6_1,
                              TEMPORA_QUAD6_2, TEMPORA_QUAD6_3,
                              TEMPORA_QUAD6_4, TEMPORA_QUAD6_5,
                              TEMPORA_QUAD6_6, TEMPORA_QUADP3_3)
from kalendar.models import Calendar, Observance
from utils import match


def rule_nativity_has_multiple_masses(
        calendar: Calendar, date_: date, tempora: List[Observance], observances: List[Observance], lang: str):
    # Nativity Vigil takes place of 4th Advent Sunday.
    if match(observances, SANCTI_12_25_1):
        return [ld for ld in observances if ld.id.startswith('sancti:12-25m')], [], []


def rule_all_souls(
        calendar: Calendar, date_: date, tempora: List[Observance], observances: List[Observance], lang: str):
    # All Souls Day; if not Sunday - Nov 2, else Nov 3; additionally it has three masses
    if match(observances, SANCTI_11_02_1):
        all_souls = [ld for ld in observances if ld.id.startswith('sancti:11-02m')]
        if date_.weekday() == 6:
            return [match(observances, PATTERN_TEMPORA_SUNDAY)], [], [[date(date_.year, 11, 3), all_souls]]
        return all_souls, [], []


def rule_nativity(
        calendar: Calendar, date_: date, tempora: List[Observance], observances: List[Observance], lang: str):
    # Nativity Vigil takes place of 4th Advent Sunday.
    if match(observances, SANCTI_12_25_1):
        return [ld for ld in observances if ld.id.startswith('sancti:12-25m')], [], []


def rule_nativity_vigil(
        calendar: Calendar, date_: date, tempora: List[Observance], observances: List[Observance], lang: str):
    # Nativity Vigil takes place of 4th Advent Sunday.
    if match(observances, SANCTI_12_24) and date_.weekday() == 6:
        return [match(observances, SANCTI_12_24)], [], []


def rule_immaculate_coneption(
        calendar: Calendar, date_: date, tempora: List[Observance], observances: List[Observance], lang: str):
    # Immaculate Conception of BMV takes precedence before encountered Advent Sunday.
    if match(observances, SANCTI_12_08) and date_.weekday() == 6:
        return [match(observances, SANCTI_12_08)], [], []


def rule_st_matthias(
        calendar: Calendar, date_: date, tempora: List[Observance], observances: List[Observance], lang: str):
    # St. Matthias the Apostle, normally on Feb 24, but in leap year on Feb 25
    if match(observances, SANCTI_02_24) and isleap(date_.year) and date_.day == 24:
        return [match(observances, PATTERN_TEMPORA)], [], [[date(date_.year, 2, 25), [match(observances, SANCTI_02_24)]]]


def rule_feb27(
        calendar: Calendar, date_: date, tempora: List[Observance], observances: List[Observance], lang: str):
    # Feb 27, normally on Feb 27 but in leap year on Feb 28
    if match(observances, SANCTI_02_27) and isleap(date_.year) and date_.day == 27:
        return [match(observances, PATTERN_TEMPORA)], [], [[date(date_.year, 2, 28), [match(observances, SANCTI_02_27)]]]


def rule_bmv_office_on_saturday(
        calendar: Calendar, date_: date, tempora: List[Observance], observances: List[Observance], lang: str):
    # On feria Saturdays (4th class) the celebration is B. M. V. Saturdays on given period

    def _calc_proper_for_given_period():
        if match(tempora, PATTERN_ADVENT):
            return C_10A  # B. M. V. Saturdays in Advent

        if date_ >= date(date_.year, 12, 25) or date_ < date(date_.year, 2, 2):
            return C_10B  # B. M. V. Saturdays between Nativity and Purification

        wednesday_in_holy_week, _ = calendar.find_day(TEMPORA_QUAD6_3)
        if date(date_.year, 2, 2) <= date_ < wednesday_in_holy_week:
            return C_10C  # B. M. V. Saturdays between Feb 2 and Wednesday in Holy Week

        if match(tempora, PATTERN_EASTER):
            return C_10PASC  # B. M. V. Saturdays in Easter period

        return C_10T  # B. M. V. Saturdays between Trinity Sunday and Saturday before 1st Sunday of Advent

    if date_.weekday() == 5:
        ranks = set([i.rank for i in observances])
        if len(ranks) == 0 or (len(ranks) == 1 and ranks.pop() == 4):
            bmv_office = Observance(_calc_proper_for_given_period(), date_, lang)
            return [bmv_office], [i for i in observances if i.flexibility == 'sancti'][:1], []


def rule_shift_conflicting_1st_class_feasts(
        calendar: Calendar, date_: date, tempora: List[Observance], observances: List[Observance], lang: str):
    # If there are two feasts with 1st class, the one with lower priority on Precedence Table is shifted to the first
    # day where there is no 1st and 2nd class feast.

    def _calc_target_date():
        target_date = copy(date_)
        while target_date.year == date_.year:
            target_date = target_date + timedelta(days=1)
            all_ranks = set([ld.rank for ld in calendar.get_day(target_date).all])
            if not {1, 2}.intersection(all_ranks):
                return target_date

    first_class_feasts = [ld for ld in observances if ld.rank == 1]
    if len(first_class_feasts) > 1:
        celebration, shift_day = sorted(first_class_feasts, key=lambda ld: ld.priority)[:2]
        to_shift = [[_calc_target_date(), [shift_day]]]
        return [celebration], [], to_shift


def rule_lord_feast1(
        calendar: Calendar, date_: date, tempora: List[Observance], observances: List[Observance], lang: str):
    # A 1st class feast of the Lord occurring on a Sunday or Feria
    # takes the place of that day with all rights and privileges;
    # hence there is no commemoration of the day.
    if match(observances, SANCTI_01_13) and match(observances, TEMPORA_EPI1_0):
        return [match(observances, TEMPORA_EPI1_0)], [], []


def rule_lord_feast2(
        calendar: Calendar, date_: date, tempora: List[Observance], observances: List[Observance], lang: str):
    if match(observances, FEASTS_OF_JESUS_CLASS_1_AND_2) and match(observances, PATTERN_TEMPORA_SUNDAY_CLASS_2):
        return [match(observances, PATTERN_SANCTI_CLASS_1_OR_2)], [], []


def first_class_feast_no_commemoration(
        calendar: Calendar, date_: date, tempora: List[Observance], observances: List[Observance], lang: str):
    if match(observances, PATTERN_CLASS_1):
        return [match(sorted(observances, key=lambda x: x.priority), PATTERN_CLASS_1)], [], []


def rule_2nd_class_sunday(
        calendar: Calendar, date_: date, tempora: List[Observance], observances: List[Observance], lang: str):
    # When 2nd class Sunday occurs along with 2nd class feast, the Sunday takes precedence and the feast is commemorated
    if match(observances, PATTERN_TEMPORA_SUNDAY_CLASS_2) and match(observances, PATTERN_SANCTI_CLASS_2):
        return [match(observances, PATTERN_TEMPORA_SUNDAY_CLASS_2)], [match(observances, PATTERN_SANCTI_CLASS_2)], []


def rule_1st_class_feria(
        calendar: Calendar, date_: date, tempora: List[Observance], observances: List[Observance], lang: str):
    # Ash wednesday and holy week always wins
    if match(observances, [TEMPORA_QUAD6_1,
                        TEMPORA_QUAD6_2,
                        TEMPORA_QUAD6_3,
                        TEMPORA_QUAD6_4,
                        TEMPORA_QUAD6_5,
                        TEMPORA_QUAD6_6,
                        TEMPORA_PASC0_0,
                        TEMPORA_QUADP3_3]):
        return [match(observances, PATTERN_TEMPORA)], [], []


def rule_2nd_class_feast_takes_over_advent_feria_and_ember_days(
        calendar: Calendar, date_: date, tempora: List[Observance], observances: List[Observance], lang: str):
    look_for = EMBER_DAYS + (PATTERN_ADVENT_FERIA_BETWEEN_17_AND_23, )
    if match(observances, look_for) and match(observances, PATTERN_SANCTI_CLASS_2):
        return [match(observances, PATTERN_SANCTI_CLASS_2)], [match(observances, look_for)], []


def rule_precedence(
        calendar: Calendar, date_: date, tempora: List[Observance], observances: List[Observance], lang: str):
    # Default rule for situations not handled by any of the above
    if len(observances) == 0:
        return [], [], []
    elif len(observances) == 1:
        return observances, [], []
    else:
        first, second = sorted(observances, key=lambda x: (x.priority, x.rank, x.flexibility))[:2]
        if match([first], PATTERN_TEMPORA_SUNDAY) or (len(tempora) > 0 and second.id == tempora[0].id):
            return [first], [], []
        return [first], [second], []


rules = (
    rule_nativity_has_multiple_masses,
    rule_all_souls,
    rule_nativity_vigil,
    rule_immaculate_coneption,
    rule_st_matthias,
    rule_feb27,
    rule_shift_conflicting_1st_class_feasts,
    rule_lord_feast1,
    rule_lord_feast2,
    first_class_feast_no_commemoration,
    rule_2nd_class_sunday,
    rule_1st_class_feria,
    rule_2nd_class_feast_takes_over_advent_feria_and_ember_days,
    rule_bmv_office_on_saturday,
    rule_precedence
)