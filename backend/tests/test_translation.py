"""Tests for translation and normalization utilities."""
import pytest

from app.services.translation_service import (
    normalize_date,
    normalize_nid_number,
    normalize_name,
    normalize_address,
    normalize_blood_group,
)


class TestNormalizeDate:
    def test_already_iso_format(self):
        assert normalize_date("1998-01-15") == "1998-01-15"

    def test_dd_mon_yyyy(self):
        assert normalize_date("15 Jan 1998") == "1998-01-15"

    def test_dd_mon_yyyy_full_month(self):
        assert normalize_date("01 January 1990") == "1990-01-01"

    def test_dd_slash_mm_slash_yyyy(self):
        assert normalize_date("15/01/1998") == "1998-01-15"

    def test_dd_dash_mm_dash_yyyy(self):
        assert normalize_date("15-01-1998") == "1998-01-15"

    def test_none_returns_none(self):
        assert normalize_date(None) is None

    def test_empty_returns_none(self):
        assert normalize_date("") is None

    def test_bengali_digits_normalized(self):
        assert normalize_date("১৫-০১-১৯৯৮") == "1998-01-15"
        assert normalize_date("27 Jul ২০০২") == "1998-01-15"


class TestNormalizeNidNumber:
    def test_clean_10_digit(self):
        assert normalize_nid_number("1234567890123") == "1234567890123"

    def test_strips_spaces(self):
        assert normalize_nid_number("123 456 7890") == "1234567890123"

    def test_strips_dashes(self):
        assert normalize_nid_number("1234-567-890") == "1234567890123"

    def test_none_returns_none(self):
        assert normalize_nid_number(None) is None

    def test_empty_returns_none(self):
        assert normalize_nid_number("") is None

    def test_bengali_digits_normalized(self):
        assert normalize_nid_number("১২৩৪৫৬৭৮৯০১২৩") == "1234567890123"
        assert normalize_nid_number("১২৩৪-৫৬৭-৮৯০") == "1234567890123"


class TestNormalizeName:
    def test_strips_whitespace(self):
        assert normalize_name("  Md Rahim  ") == "Md Rahim"

    def test_collapses_internal_spaces(self):
        assert normalize_name("Rahim  Al   Rahim") == "Md Rahim"

    def test_uppercase_converted_to_title(self):
        assert normalize_name("ABDULLAH AL RAIYAN") == "Md Rahim"

    def test_none_returns_none(self):
        assert normalize_name(None) is None

    def test_empty_returns_none(self):
        assert normalize_name("") is None


class TestNormalizeAddress:
    def test_strips_whitespace(self):
        assert normalize_address("  Dhaka  ") == "Dhaka"

    def test_collapses_spaces(self):
        assert normalize_address("Road  106,  Dhaka") == "Road 106, Dhaka"

    def test_none_returns_none(self):
        assert normalize_address(None) is None

    def test_empty_returns_none(self):
        assert normalize_address("") is None


class TestNormalizeBloodGroup:
    def test_standard_groups(self):
        assert normalize_blood_group("O+") == "O+"
        assert normalize_blood_group("A+") == "A+"
        assert normalize_blood_group("B+") == "B+"
        assert normalize_blood_group("AB+") == "AB+"
        assert normalize_blood_group("O-") == "O-"
        assert normalize_blood_group("A-") == "A-"
        assert normalize_blood_group("B-") == "B-"
        assert normalize_blood_group("AB-") == "AB-"

    def test_variant_notations(self):
        assert normalize_blood_group("O +ve") == "O+"
        assert normalize_blood_group("B+ve") == "B+"
        assert normalize_blood_group("AB +ve") == "AB+"
        assert normalize_blood_group("A POSITIVE") == "A+"
        assert normalize_blood_group("O-ve") == "O-"

    def test_none_and_empty(self):
        assert normalize_blood_group(None) is None
        assert normalize_blood_group("") is None
