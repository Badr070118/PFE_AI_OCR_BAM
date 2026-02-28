from __future__ import annotations

import calendar
import random
from datetime import date, datetime, time, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List


FIRST_NAMES = [
    "Youssef",
    "Sara",
    "Omar",
    "Nadia",
    "Karim",
    "Imane",
    "Rachid",
    "Soumia",
    "Mehdi",
    "Asmae",
    "Pierre",
    "Sophie",
    "Lucas",
    "Camille",
    "Nabil",
    "Meriem",
]

LAST_NAMES = [
    "El Amrani",
    "Benjelloun",
    "Alaoui",
    "Bennani",
    "Lahlou",
    "Tazi",
    "Kabbaj",
    "Bouchra",
    "Martin",
    "Bernard",
    "Dubois",
    "Durand",
    "Moreau",
    "Leroy",
    "Bensaid",
    "Idrissi",
]

STREETS = [
    "Avenue Mohammed V",
    "Boulevard Zerktouni",
    "Rue Al Qods",
    "Avenue Hassan II",
    "Boulevard Anfa",
    "Rue Ibn Sina",
    "Avenue Fal Ould Oumeir",
    "Boulevard Abdelmoumen",
]

CITIES = [
    "Casablanca",
    "Rabat",
    "Marrakech",
    "Fes",
    "Tangier",
    "Agadir",
    "Meknes",
    "Oujda",
]

BANKS = [
    "Banque Centrale Populaire",
    "Attijariwafa bank",
    "Bank of Africa",
    "CIH Bank",
    "BMCI",
    "SociEte Generale Maroc",
]

SUPPLIER_COMPANIES = [
    "Atlas Services SARL",
    "Maghreb Equipements SA",
    "Casatech Distribution",
    "Ribat Solutions SARL AU",
    "Nourisys Consulting",
]

CLIENT_COMPANIES = [
    "Al Manar Trading",
    "Nord Logistic Maroc",
    "Rive Sud Industrie",
    "Sahara Medica",
    "Orion Retail SARL",
]

INVOICE_ITEMS = [
    "Maintenance applicative",
    "Abonnement service cloud",
    "Audit technique",
    "Support utilisateur",
    "Frais de livraison",
    "Licence logicielle",
    "Prestation integration",
    "Formation equipe",
]

STATEMENT_LABELS = [
    "Paiement TPE supermarche",
    "Virement recu client",
    "Retrait GAB",
    "Facture electricite",
    "Depot espece agence",
    "Paiement facture telecom",
    "Reglement fournisseur",
    "Encaissement cheque",
    "Achat carburant",
    "Cotisation service bancaire",
]

PAYMENT_REASONS = [
    "Reglement facture fournisseur",
    "Paiement mensualite",
    "Remboursement avance",
    "Paiement loyer",
    "Versement acompte",
]

TRANSFER_REASONS = [
    "Paiement fournisseur",
    "Transfert inter-entreprises",
    "Reglement prestation",
    "Versement acompte projet",
    "Paiement honoraires",
]

CHANNELS = ["Agence", "ATM", "En ligne"]


def _money(value: float) -> float:
    return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def format_mad(value: float) -> str:
    formatted = f"{value:,.2f}".replace(",", " ")
    return f"{formatted} MAD"


def _digits(rng: random.Random, n: int) -> str:
    return "".join(rng.choice("0123456789") for _ in range(n))


def _grouped(value: str, group: int = 4) -> str:
    return " ".join(value[i : i + group] for i in range(0, len(value), group))


def _random_person(rng: random.Random) -> str:
    return f"{rng.choice(FIRST_NAMES)} {rng.choice(LAST_NAMES)}"


def _random_company(rng: random.Random, companies: List[str]) -> str:
    return rng.choice(companies)


def _random_address(rng: random.Random) -> str:
    city = rng.choice(CITIES)
    postal_code = rng.randint(10000, 99999)
    street_no = rng.randint(1, 240)
    street = rng.choice(STREETS)
    return f"{street_no}, {street}, {postal_code} {city}, Maroc"


def _iban_ma(rng: random.Random) -> str:
    check_digits = _digits(rng, 2)
    bban = _digits(rng, 24)
    return _grouped(f"MA{check_digits}{bban}")


def _rib(rng: random.Random) -> str:
    return _grouped(_digits(rng, 24))


def _account_number(rng: random.Random) -> str:
    return _grouped(_digits(rng, 16))


def _reference(prefix: str, year: int, rng: random.Random) -> str:
    return f"{prefix}-{year}-{rng.randint(0, 999999):06d}"


def _rng_for(kind_seed: int, index: int) -> random.Random:
    return random.Random(kind_seed + (index * 97))


def _month_shift(base: date, months_back: int) -> date:
    year = base.year
    month = base.month - months_back
    while month <= 0:
        month += 12
        year -= 1
    day = min(base.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def generate_invoice_data(index: int) -> Dict:
    rng = _rng_for(1500, index)
    invoice_date = date.today() - timedelta(days=rng.randint(20, 180))
    due_date = invoice_date + timedelta(days=rng.choice([15, 30, 45]))
    supplier_name = _random_company(rng, SUPPLIER_COMPANIES)
    client_name = _random_company(rng, CLIENT_COMPANIES)

    line_count = rng.randint(4, 7)
    lines = []
    for _ in range(line_count):
        qty = rng.randint(1, 8)
        unit_price = _money(rng.uniform(120, 4800))
        line_total = _money(qty * unit_price)
        lines.append(
            {
                "description": rng.choice(INVOICE_ITEMS),
                "qty": qty,
                "unit_price": unit_price,
                "line_total": line_total,
            }
        )

    total_ht = _money(sum(line["line_total"] for line in lines))
    total_vat = _money(total_ht * 0.20)
    total_ttc = _money(total_ht + total_vat)
    year = invoice_date.year

    return {
        "invoice_ref": _reference("INV", year, rng),
        "invoice_date": invoice_date.strftime("%d/%m/%Y"),
        "due_date": due_date.strftime("%d/%m/%Y"),
        "supplier_name": supplier_name,
        "supplier_address": _random_address(rng),
        "supplier_ice": _digits(rng, 15),
        "supplier_phone": f"+212 6{_digits(rng, 8)}",
        "client_name": client_name,
        "client_contact": _random_person(rng),
        "client_address": _random_address(rng),
        "currency": "MAD",
        "lines": lines,
        "total_ht": total_ht,
        "total_vat": total_vat,
        "total_ttc": total_ttc,
        "payment_terms": f"Paiement a {rng.choice([15, 30, 45])} jours par virement bancaire.",
    }


def generate_statement_data(index: int) -> Dict:
    rng = _rng_for(2600, index)
    holder_name = _random_person(rng)
    bank_name = rng.choice(BANKS)
    period_anchor = _month_shift(date.today().replace(day=15), index - 1)
    period_start = period_anchor.replace(day=1)
    period_end = period_anchor.replace(day=calendar.monthrange(period_anchor.year, period_anchor.month)[1])

    opening_balance = _money(rng.uniform(3000, 45000))
    running_balance = opening_balance
    total_debit = 0.0
    total_credit = 0.0
    transaction_count = 10
    current_day = period_start + timedelta(days=rng.randint(0, 2))
    transactions = []

    for _ in range(transaction_count):
        if current_day > period_end:
            current_day = period_end

        is_credit = rng.random() < 0.42
        amount = _money(rng.uniform(80, 6800))
        debit = 0.0
        credit = 0.0

        if is_credit:
            credit = amount
            running_balance = _money(running_balance + amount)
            total_credit = _money(total_credit + amount)
        else:
            debit = amount
            running_balance = _money(running_balance - amount)
            total_debit = _money(total_debit + amount)

        transactions.append(
            {
                "date": current_day.strftime("%d/%m/%Y"),
                "label": rng.choice(STATEMENT_LABELS),
                "debit": debit,
                "credit": credit,
                "balance": running_balance,
            }
        )
        current_day += timedelta(days=rng.randint(1, 4))

    closing_balance = running_balance

    return {
        "statement_ref": _reference("STM", period_end.year, rng),
        "bank_name": bank_name,
        "holder_name": holder_name,
        "account_number": _account_number(rng),
        "iban": _iban_ma(rng),
        "period_start": period_start.strftime("%d/%m/%Y"),
        "period_end": period_end.strftime("%d/%m/%Y"),
        "currency": "MAD",
        "opening_balance": opening_balance,
        "closing_balance": closing_balance,
        "total_debit": total_debit,
        "total_credit": total_credit,
        "transactions": transactions,
    }


def generate_receipt_data(index: int) -> Dict:
    rng = _rng_for(3700, index)
    event_date = datetime.combine(
        date.today() - timedelta(days=rng.randint(2, 90)),
        time(hour=rng.randint(8, 18), minute=rng.randint(0, 59), second=rng.randint(0, 59)),
    )
    amount = _money(rng.uniform(150, 30000))
    fees = _money(rng.uniform(2, 80))
    total = _money(amount + fees)
    channel = rng.choice(CHANNELS)

    return {
        "receipt_ref": _reference("TXN", event_date.year, rng),
        "date": event_date.strftime("%d/%m/%Y"),
        "time": event_date.strftime("%H:%M:%S"),
        "channel": channel,
        "payer_name": _random_person(rng),
        "payer_account": _account_number(rng),
        "beneficiary_name": _random_person(rng),
        "beneficiary_account": _account_number(rng),
        "reason": rng.choice(PAYMENT_REASONS),
        "amount": amount,
        "fees": fees,
        "total": total,
        "status": rng.choice(["SUCCES", "TRAITE"]),
        "transaction_id": _reference("TXN", event_date.year, rng),
        "auth_code": _digits(rng, 6),
        "currency": "MAD",
    }


def generate_transfer_data(index: int) -> Dict:
    rng = _rng_for(4800, index)
    execution_date = date.today() - timedelta(days=rng.randint(1, 60))
    amount = _money(rng.uniform(500, 120000))
    fees = _money(rng.uniform(8, 150))
    total = _money(amount + fees)

    return {
        "transfer_ref": _reference("TRF", execution_date.year, rng),
        "order_date": (execution_date - timedelta(days=rng.randint(0, 2))).strftime("%d/%m/%Y"),
        "execution_date": execution_date.strftime("%d/%m/%Y"),
        "status": rng.choice(["EXECUTE", "EN COURS"]),
        "sender_name": _random_person(rng),
        "sender_bank": rng.choice(BANKS),
        "sender_account": _account_number(rng),
        "sender_address": _random_address(rng),
        "beneficiary_name": _random_person(rng),
        "beneficiary_bank": rng.choice(BANKS),
        "beneficiary_iban": _iban_ma(rng),
        "beneficiary_rib": _rib(rng),
        "reason": rng.choice(TRANSFER_REASONS),
        "amount": amount,
        "fees": fees,
        "total": total,
        "currency": "MAD",
    }
