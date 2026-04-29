import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from apps.core.models import School


def parse_date(value: str):
    value = value.strip()
    if not value:
        return None
    return datetime.strptime(value, "%Y%m%d").date()


def parse_decimal(value: str):
    value = value.strip()
    if not value:
        return None
    try:
        return Decimal(value)
    except InvalidOperation:
        return None


def parse_bool(value: str) -> bool:
    return value.strip().upper() == "Y"


class Command(BaseCommand):
    help = "Import high school basic information CSV."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("csv_path", type=Path)

    def handle(self, *args: Any, **options: Any) -> None:
        csv_path: Path = options["csv_path"]
        if not csv_path.exists():
            self.stderr.write(self.style.ERROR(f"CSV file not found: {csv_path}"))
            return

        created_count = 0
        updated_count = 0

        with csv_path.open("r", encoding="utf-8-sig", newline="") as csv_file:
            reader = csv.DictReader(csv_file)
            for row in reader:
                lot_address = f"{row['주소내역'].strip()} {row['상세주소내역'].strip()}".strip()
                postal_code = row["학교도로명 우편번호"].strip() or row["우편번호"].strip()
                school, created = School.objects.update_or_create(
                    code=row["정보공시 학교코드"],
                    defaults={
                        "name": row["학교명"].strip(),
                        "education_office": row["시도교육청"].strip(),
                        "support_office": row["교육지원청"].strip(),
                        "region": row["지역"].strip(),
                        "establishment": row["설립구분"].strip(),
                        "school_type": row["학교특성"].strip(),
                        "day_night": row["주야구분"].strip(),
                        "founded_on": parse_date(row["설립일"]),
                        "anniversary_on": parse_date(row["개교기념일"]),
                        "lot_address": lot_address,
                        "road_address": row["학교도로명 주소"].strip(),
                        "road_address_detail": row["학교도로명 상세주소"].strip(),
                        "postal_code": postal_code,
                        "latitude": parse_decimal(row["위도"]),
                        "longitude": parse_decimal(row["경도"]),
                        "phone": row["전화번호"].strip(),
                        "fax": row["팩스번호"].strip(),
                        "homepage_url": row["홈페이지 주소"].strip(),
                        "gender_type": row["남녀공학 구분"].strip(),
                        "is_closed": parse_bool(row["폐교여부"]),
                        "closed_on": parse_date(row["폐교일자"]),
                        "is_paused": parse_bool(row["휴교여부"]),
                    },
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported schools. created={created_count}, updated={updated_count}"
            )
        )
